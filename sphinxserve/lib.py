'''sphinxserve library'''

# Make watchdog non-blocking monkeypatching os.read
from gevent.os import tp_read
import os
os.read = tp_read

from contextlib import contextmanager
from flask import Flask
from flask_sockets import Sockets
import gevent
from gevent.pywsgi import WSGIServer
from gevent.queue import Queue
from gevent import sleep
from geventwebsocket.handler import WebSocketHandler
from loadconfig.py6 import text_type
import re
import socket
from textwrap import dedent
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


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
