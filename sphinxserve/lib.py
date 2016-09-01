'''sphinxserve library'''

# Make watchdog non-blocking monkeypatching os.read
from gevent.os import tp_read
import os
os.read = tp_read

from bottle import get, run, static_file
from contextlib import contextmanager
import gevent
from gevent.queue import Queue
from gevent import sleep
from loadconfig.lib import Ret
from loadconfig.py6 import cStringIO
import re
import socket
import sys
from textwrap import dedent
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

if sys.platform.startswith('win') or sys.platform.startswith('darwin'):
    from watchdog.observers.polling import PollingObserver as Observer  # noqa


class Webserver(object):
    '''Serve static content from path, featuring asynchronous reload.
    Page reload is triggered by sphinx rst updates using gevent on the server
    and executed after ajax long polling on the browser.
    '''
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

        run(host=self.host, port=int(self.port), server='gevent')


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


def check_host(host, port=22, timeout=1, recv=False):
    '''Return True if socket is active. timeout in seconds.
    Use recv=False if socket is silent after connection
    '''
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
