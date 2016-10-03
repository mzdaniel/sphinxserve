'''sphinxserve library'''

# Make watchdog non-blocking monkeypatching os.read
from gevent.os import tp_read
import os
os.read = tp_read

from bottle import get, install, response, request, run, static_file
from coloredlogs import ColoredFormatter
from contextlib import contextmanager
from decorator import decorator
from distutils.dir_util import mkpath
import gevent
from gevent.queue import Queue
from gevent import sleep
from loadconfig.lib import Ret, write_file
from loadconfig.py6 import cStringIO
import logging
import re
import socket
import sys
from textwrap import dedent
from time import time
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

if sys.platform.startswith('win') or sys.platform.startswith('darwin'):
    from watchdog.observers.polling import PollingObserver as Observer  # noqa

log = logging.getLogger(__name__)


class Webserver(object):
    '''Serve static content from path, featuring asynchronous reload.
       Page reload is triggered by sphinx rst updates using gevent on the
       server and executed after ajax long polling on the browser.'''
    def __init__(self, path, host, port, reload_ev):
        self.path, self.host, self.port = path, host, port
        self.reload_ev = reload_ev

    def run(self):
        reload_js = dedent('''\
        <script type="text/javascript">
            $.ajaxSetup({cache: false})  // drop browser cache for refresh
            $(document).ready(function() {
                $.ajax({ type: "GET", async: true, cache: false,
                    url: location.protocol + "//" + location.host + "/_svwait",
                    success: function() {window.location.reload(true)} }) })
        </script>''')

        def after_request(response):
            '''Add reload javascript and remove googleapis fonts'''
            r = response
            if not r.content_type.startswith('text/'):
                return r
            body = b''.join(r).decode('utf-8')
            r.close()
            if r.content_type.startswith('text/html'):
                body = re.sub(r'(</head>)', r'{}\1'.format(reload_js),
                    body, flags=re.IGNORECASE)
            if r.content_type.startswith('text/css'):
                body = re.sub(r'@import url\(.+fonts.googleapis.com.+\);', '',
                    body, flags=re.IGNORECASE)
            r.headers['Content-Length'] = len(body)
            r.body = body
            return r

        @get('<path:path>')
        def serve_static(path):
            path = path + '/index.html' if path.endswith('/') else path
            response = static_file(path, root=self.path)
            return after_request(response)

        @get('/_svwait')
        def wait_server_event():
            '''Block long polling javascript until reload event'''
            self.reload_ev.wait()
            self.reload_ev.clear()

        install(log_to_logger)
        run(host=self.host, port=int(self.port), quiet=True, server='gevent')


@contextmanager
def fs_event_ctx(path, extensions):
    '''watchdog context manager wrapper. Return filesystem event iterator'''
    class EventHandler(PatternMatchingEventHandler):
        '''Add fs event iterator property to PatternMatchingEventHandler'''
        def __init__(self, *args, **kwargs):
            super(EventHandler, self).__init__(*args, **kwargs)
            self.fs_queue = Queue()

        def on_any_event(self, event):
            self.fs_queue.put(Ret(event.src_path, ev_name=event.event_type))

        @property
        def fs_event(self):
            while True:
                yield self.fs_queue.get()

    patterns = ['*.{}'.format(p) for p in extensions]
    evh = EventHandler(patterns=patterns, ignore_directories=True)
    observer = Observer()
    observer.schedule(evh, path, recursive=True)
    observer.start()
    try:
        yield evh.fs_event
    except StopIteration:
        pass
    observer.stop()
    del observer
    del evh


@contextmanager
def capture_streams():
    r'''Capture streams (stdout & stderr) in a string
    >>> with capture_streams() as streams:
    ...     print('Hi there')
    >>> streams.getvalue()
    'Hi there\n'
    '''
    stdout = sys.stdout
    stderr = sys.stderr
    data = cStringIO()
    sys.stdout = data
    sys.stderr = data
    yield data
    sys.stdout = stdout
    sys.stderr = stderr
    data.flush()


class Timeout(gevent.Timeout):
    '''Add expired attribute to Timeout context manager'''
    def __init__(self, *args, **kwargs):
        super(Timeout, self).__init__(*args, **kwargs)
        self.expired = False

    def __exit__(self, typ, value, tb):
        self.cancel()
        if value is self and self.exception is False:
            self.expired = True
            return True


def exit_msg(msg, exitcode=1):
    log.error(msg)
    exit(exitcode)


@decorator
def log_to_logger(func, *args, **kwargs):
    log.debug('%s %s %s', request.method, request.url, response.status)
    return func(*args, **kwargs)


@decorator
def elapsed(func, *args, **kwargs):
    '''Elapsed time logger decorator'''
    log.info('Building...')
    started = time()
    retcode = func(*args, **kwargs)
    log.info('Build completed in %fs', time() - started)
    return retcode


def check_host(host, port=22, timeout=1, recv=False):
    '''Return True if socket is active. timeout in seconds.
       Use recv=False if socket is silent after connection'''
    with Timeout(timeout) as ctx:
        while True:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            try:
                sock.connect((host, int(port)))
                if not recv or sock.recv(1024):
                    break
                sleep(0.01)
            except socket.error:
                sleep(1)
            except (socket.timeout, OSError):
                pass
            finally:
                sock.close()
    return not ctx.expired


def check_dependencies(c):
    '''Ensure sphinx conf.py and index.rst are on c.sphinx_path
       c is the configuration object.'''
    path = c.sphinx_path
    if not os.path.exists(path):
        exit_msg("\nSphinx config dir %s doesn't exist" % path)
    if not os.path.exists(path + '/index.rst'):
        exit_msg("\nindex.rst doesn't exist on %s\n"
             "Look on '%s --help' to create a default file" % (path, c.app))
    if not os.path.exists(path + '/conf.py'):
        exit_msg("\nconf.py sphinx config file doesn't exist on %s\n"
             "Look on '%s --help' to create a default file" % (path, c.app))


def setlog(c):
    '''Set logging. Call setlog *before* using logging.
       c is the configuration object.'''
    c.loglevel = 50 - 10 * c.debug
    c.quiet = []  # Switch for limiting sphinx logs.
    if c.debug in [0, 1, 2]:
        c.quiet = ['-Q']
    elif c.debug == 3:
        c.quiet = ['-q']
    formatter_cls = logging.Formatter if c.nocolor else ColoredFormatter
    logging_stream = logging.StreamHandler()
    logging_stream.setFormatter(formatter_cls(
        '%(asctime)s %(name)s %(levelname)s %(message)s', '%Y-%m-%d %H:%M:%S'))
    log = logging.getLogger()
    log.setLevel(c.loglevel)
    log.addHandler(logging_stream)
    return log


def setup(c):
    '''Set logger and process switches. c is the configuration object.'''
    setlog(c)

    path = c.sphinx_path
    c.path_dest = os.path.join(path, c.path_dest)
    log.debug('\n' + str(c))
    if c.make_conf:
        mkpath(path)
        write_file(path + '/conf.py', "master_doc = 'index'\n")
    if c.make_index:
        mkpath(path)
        data = dedent('''\
            Index rst file
            ==============

            This is the main reStructuredText page. It is meant as a
            temporary example, ready to override.''')
        write_file(path + '/index.rst', data)
    check_dependencies(c)
    return c
