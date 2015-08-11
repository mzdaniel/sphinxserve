'''sphinxserve library'''

from flask import Flask
from flask_sockets import Sockets
import gevent
from gevent.pywsgi import WSGIServer
from gevent import sleep
from geventwebsocket.handler import WebSocketHandler
from loadconfig.lib import exc, Run
from loadconfig.py6 import text_type
import logging as log
from os.path import dirname
import re
from signal import SIGINT, SIGTERM
import socket
import sys
from textwrap import dedent
import watchdog


class Webserver(object):
    '''Serve static content from path, featuring asynchronous reload.
    reload uses flask-sockets for async gevent communication on the server
    and websockets on the browser.
    '''
    def __init__(self, path, host, port, sig_reload):
        self.path = path
        self.host = host
        self.port = port
        self.signal = sig_reload

    def run(self):
        reload_js = dedent('''\
        <script type="text/javascript">
            $.ajaxSetup({cache: false})  // drop browser cache for refresh
            var ws = new WebSocket("ws://" + location.host + "/ws")
            ws.onclose = function() {    // reload server signal
                window.location.reload(true)}
        </script>''')
        app = Flask(__name__, static_url_path='',
            static_folder=self.path + '/html')
        sockets = Sockets(app)

        @app.route('/')
        def root():
            return app.send_static_file('index.html')

        @app.after_request
        def after_request(response):  # Add reload javascript
            response.direct_passthrough = False
            if response.content_type.startswith('text/html'):
                response.data = re.sub('(</head>)', r'{}\1'.format(reload_js),
                    response.data, flags=re.IGNORECASE)
            return response

        @sockets.route('/ws')
        def ws_socket(ws):
            '''Reload browser'''
            self.signal.wait()
            self.signal.clear()
            ws.close()

        WSGIServer((self.host, int(self.port)), app,
            handler_class=WebSocketHandler).serve_forever()


def read_event(path, extensions):
    '''Return iterator with filename and filesysytem event tuple.
    '''
    def wd_cmd(path, extensions):
        '''Return watchmedo command line for pex compatibility
        '''
        patterns = ';'.join(['*.' + e for e in extensions])
        watchmedo_path = dirname(watchdog.__file__) + '/watchmedo.py'
        PYTHONPATH = dirname(dirname(watchdog.__file__))
        for dep in ['argh', 'pathtools', 'watchdog', 'yaml']:
            PYTHONPATH += ':{}'.format(
                dirname(dirname(__import__(dep).__file__)))
        return ("PYTHONPATH={} PYTHONUNBUFFERED=1 python2 {} "
            "log {} -p '{}'".format(
                PYTHONPATH, watchmedo_path, path, patterns))

    CMD = wd_cmd(path, extensions)
    log.debug(CMD)
    with Run(CMD, async=True) as proc:
        cleanup_on_signals(proc.terminate)
        while True:
            line = proc.stdout.readline()
            if not line:  # exit program if stdout was closed
                log.debug(proc.stderr.read())
                log.debug('filesystem watchdog empty. Stopping now.')
                sys.exit(0)
            ev_path, ev_name = re.sub("^(.+)\(.+src_path='(.+)'.+",
                r'\2|\1', line).split('|')
            yield (Ret(ev_path, ev_name=ev_name))


class Ret(text_type):
    r'''Return class.
    arg[0] is the string value for the Ret object.
    kwargs are feed as attributes.

    >>> ret = Ret('OK', code=0)
    >>> ret == 'OK'
    True
    >>> ret.code
    0
    '''
    def __new__(cls, string, **kwargs):
        ret = super(Ret, cls).__new__(cls, text_type(string))
        for k in kwargs:
            setattr(ret, k, kwargs[k])
        return ret

    _r = property(lambda self: self.__dict__)


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


def cleanup_on_signals(func):
    '''Call func on signals and exit'''
    def exit():
        func()
        sys.exit(0)
    gevent.signal(SIGINT, exit)
    gevent.signal(SIGTERM, exit)


def retry(func, args=[], kwargs={}, sleep=0, count=5, hide_exc=False,
 success=lambda x: True):
    '''Retry and return func(args) up to count times'''
    for i in range(count):
        if i:
            gevent.sleep(sleep)
        with exc(Exception) as e:
            retval = func(*args, **kwargs)
            if success(retval):
                return retval
    if e() and not hide_exc:
        raise e()
