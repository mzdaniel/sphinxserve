'''sphinxserve render sphinx docs when detecting file changes.

usage: sphinxserve [-h] ... [sphinx_path]'''

__version__ = '0.8b2'
__author__ = 'Daniel Mizyrycki'

import gevent.monkey
gevent.monkey.patch_all()

from gevent import spawn, joinall, killall, signal
from gevent.event import Event
from loadconfig import Config
from loadconfig.py6 import shlex_quote
import logging
from multiprocessing import Process
from signal import SIGTERM
import sphinx
from sphinxserve.lib import elapsed, exit_msg, fs_event_ctx, setup, Webserver
import sys

log = logging.getLogger(__name__)


conf = '''\
    app:            sphinxserve
    app_socket:     localhost:8888
    extensions:     [rst, rst~, txt, txt~]

    clg:
        prog: $app
        description: |
            $app $version render sphinx docs when detecting file changes and
            serve them by default on localhost:8888. It uses gevent and flask
            for serving the website and watchdog for recursively monitor
            changes on rst and txt files.
        help: 'serve sphinx docs. (For extra help, use: sphinxserve --help)'
        options: &options
            debug:
                short: d
                choices: [0,1,2,3,4]
                help: 'Debug level [0-4] (4: full debug. def: __DEFAULT__)'
                default: 3
                type: int
            nocolor:
                short: N
                action: store_true
                default: False
            socket:
                short: s
                help: 'Launch web server if defined  (def: __DEFAULT__)'
                default: $app_socket
            path_dest:
                short: p
                help: 'output directory (def: __DEFAULT__)'
                default: html
            make_conf:
                short: C
                help: 'Create configuration file conf.py'
                action: store_true
                default: False
            make_index:
                short: I
                help: 'Create index file index.rst'
                action: store_true
                default: False
        args: &args
            sphinx_path:
                help: 'path containing sphinx conf.py (def: $PWD)'
                nargs: '?'
                default: __SUPPRESS__

    checkconfig: |
        import os
        if not self.sphinx_path:
           self.sphinx_path = os.getcwd()
        self.sphinx_path = os.path.abspath(self.sphinx_path)
    '''


class SphinxServer(object):
    '''Coordinate sphinx greenlets.
       manage method render sphinx pages, initialize and give control to serve,
       watch and render greenlets.'''
    def __init__(self, c):
        self.c = c
        self.watch_ev = Event()
        self.render_ev = Event()

    def serve(self):
        '''Serve web requests from path as soon docs are ready.
           Reload remote browser when updates are rendered using websockets'''
        host, port = self.c.socket.split(':')
        server = Webserver(self.c.path_dest, host, port, self.render_ev)
        log.warning('Listening on http://%s:%s', host, port)
        server.run()

    def watch(self):
        '''Watch sphinx_path signalling render when rst files change'''
        with fs_event_ctx(self.c.sphinx_path, self.c.extensions) as fs_ev_iter:
            for event in fs_ev_iter:
                log.info('%s %s', event, event.ev_name)
                self.watch_ev.set()

    @elapsed
    def build(self):
        '''Render reStructuredText files with sphinx'''
        proc = Process(target=sphinx.main,
            args=[['sphinx-build'] + self.c.quiet +
            [shlex_quote(self.c.sphinx_path), shlex_quote(self.c.path_dest)]])
        proc.start()
        proc.join()
        return proc.exitcode

    def render(self):
        '''Render and listen for doc changes (watcher events)'''
        while True:
            self.watch_ev.wait()  # Wait for docs changes
            self.watch_ev.clear()
            if self.build() != 0:
                exit_msg('rendering %s. Aborting.' % self.c.sphinx_path)
            self.render_ev.set()

    def manage(self):
        '''Manage web server, watcher and sphinx docs renderer.'''
        def shutdown_handler():
            log.info('Received SIGTERM signal to shut down!')
            killall(workers)

        if self.build() != 0:
            exit_msg('rendering %s. Aborting.' % self.c.sphinx_path)
        workers = [spawn(self.serve), spawn(self.watch), spawn(self.render)]
        signal(SIGTERM, shutdown_handler)
        joinall(workers)
        exit(0)


def main(args):
    c = setup(Config(conf, args=args, version=__version__))
    SphinxServer(c).manage()


if __name__ == '__main__':
    main(sys.argv)
