#!/usr/bin/env python

'''sphinxserve renders sphinx docs when detecting file changes.

usage: sphinxserve [-h] {serve,install,uninstall} ...'''

__version__ = '0.6'
__author__ = 'Daniel Mizyrycki'

import gevent.monkey
gevent.monkey.patch_all()  # noqa

from gevent import sleep, spawn, killall
from gevent.event import Event
from gevent.pywsgi import WSGIServer
from loadconfig import Config
from loadconfig.lib import first, Run, run
import os
from sphinxserve.lib import clean_subproc
from static import Cling
import sys
from textwrap import dedent
from time import time

conf = '''\
    app:            sphinxserve
    app_socket:     localhost:8888
    app_browser:    firefox|iceweasel|chromium|chrome|opera
    app_user:       1000
    docker_image:   mzdaniel/sphinxserve
    extensions:     [rst, rst~, txt, txt~]

    clg:
        prog: $app
        description: |
            $app $version renders sphinx docs when detecting file changes.
            It automatically opens a new tab on the browser when launched.
            It uses gevent and static for serving the website and inotifywait
            for recursively monitor changes on rst and txt files.
            Dependencies can be satisfied intalling inotify and xdotool system
            packages, or with docker using sphinxserve install command.
        default_cmd: serve
        subparsers:
            serve:
                help: serve sphinx docs
                options: &options
                    debug:
                        short: d
                        action: store_true
                        default: __SUPPRESS__
                    browser_name:
                        short: b
                        help: browser name where to open sphinx pages
                        default: $app_browser
                    uid:
                        short: u
                        type: int
                        help: |
                            numeric system user id for rendered pages.
                              (use "id" to retrieve it.  def: $app_user)
                        default: $app_user
                    socket:
                        short: s
                        help: |
                            Launch web server if defined  (def: $app_socket)
                        default: $app_socket
                args: &args
                    sphinx_path:
                        help: |
                            path containing sphinx conf.py
                              (def: $PWD)
                        nargs: '?'
                        default: __SUPPRESS__
            install:
                help: |
                    print commands for docker installation on ~/bin/$app
                      Use as:  docker run $docker_image install | bash
                options: *options
                args: *args
            uninstall:
                help: print commands for uninstalling $app
    checkconfig: |
        import os
        if not self.sphinx_path:
           self.sphinx_path = os.getcwd()
    '''


os.environ['PATH'] = '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'


class SphinxServer(object):
    '''Coordinate sphinx greenlets.
    start method render sphinx pages, initialize and give control to the
    greenlets. The greenlets serve the pages, launch and refresh the browser
    when changes on sphinx data is detected until browser_manage detect the
    browser was closed.
    '''
    def __init__(self, c):
        self.c = c
        self.watch_ev = Event()
        self.render_ev = Event()
        self.browse_ev = Event()
        self.watchproc = None

    def serve(self):
        '''Serve web requests from path as soon docs are ready'''
        app = Cling('{}/html'.format(self.c.sphinx_path))
        host, port = self.c.socket.split(':')
        log = 'default' if self.c.debug else None
        try:
            WSGIServer(('0.0.0.0', int(port)), app, log=log).serve_forever()
        except Exception as e:
            raise SystemExit(e)

    def watch(self):
        '''Watch path signalling render when rst files change'''
        t_prev = 0
        CMD = ('inotifywait -rq -e modify,close_write,moved_from,delete {}'.
            format(self.c.sphinx_path))
        while True:
            with Run(CMD, async=True) as proc:
                filename = proc.get_output()[:-1]
            # Ignore changes in paths that dont have any of the extensions
            if filename.split('.')[-1] not in self.c.extensions:
                continue
            t = time()
            if t - t_prev < 1:  # Ignore events within 1 second
                continue
            t_prev = t
            self.watch_ev.set()

    def render(self):
        '''Render and listen for doc changes (watcher events)'''
        while True:
            self.watch_ev.wait()  # Wait for docs changes
            self.watch_ev.clear()
            run('sphinx-build {0} {0}/html'.format(self.c.sphinx_path))
            self.render_ev.set()

    def browse(self):
        '''Wait and reload browser. Signal teardown when browser closes.'''

        def find_browser_window(browser_name):
            '''Block until a browser is found'''
            while True:
                # xdotool return a list of posible windows. Get the last one.
                browser_wid = first(run(
                    'xdotool search --desktop 0 --class "{}"'.format(
                        browser_name)).split()[-1:])
                if not browser_wid:
                    sleep(1)
                    continue
                code = run('xdotool windowactivate {} 2>&1'.format(
                    browser_wid)).code
                if code == 0:  # browser window activated
                    return browser_wid
                sleep(1)

        browser_wid = find_browser_window(self.c.browser_name)
        # Open a new tab with docs
        CMD = dedent('''\
            xdotool key "ctrl+t"
            xdotool type {}
            xdotool key Return
            ''').format(self.c.socket)
        run(CMD)
        while True:
            self.render_ev.clear()
            event = self.render_ev.wait(2)
            if run('xdotool getwindowname {}'.format(browser_wid)).code:
                self.browse_ev.set()  # Browser was closed. signal teardown
            if not event:
                continue
            # Reload browser page
            cur_window = run('xdotool getactivewindow').stdout
            CMD = dedent('''\
                xdotool windowactivate {}
                xdotool key "ctrl+r"
                xdotool windowactivate {}
                ''').format(browser_wid, cur_window)
            run(CMD)

    def manage(self):
        '''Manage browser and sphinx docs renderer and server'''
        ret = run('sphinx-build {0} {0}/html'.format(self.c.sphinx_path))
        if ret.code != 0:
            raise Exception(ret.stderr)
        workers = [spawn(self.serve), spawn(self.watch),
            spawn(self.render), spawn(self.browse)]
        self.browse_ev.wait()  # Wait until docs cannot be displayed
        # Cleanup
        killall(workers)


def check_dependencies(c):
    if not os.path.exists('{}/conf.py'.format(c.sphinx_path)):
        raise SystemExit('conf.py not found on {}'.format(c.sphinx_path))
    if not os.path.exists('/usr/bin/inotifywait'):
        raise SystemExit('inotify package not installed.')
    if not os.path.exists('/usr/bin/xdotool'):
        raise SystemExit('xdotool package not installed.')


def install(c):
    print(c.render(dedent('''\
        mkdir -p ~/bin
        cat > ~/bin/$app << EOF
        #!/bin/bash

        SPHINX_PATH=\${1:-\$PWD}
        USERID="$uid"
        DESKTOP_ARGS='-v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=:0.0'
        SOCKET="$socket"
        APP_PORT=\${SOCKET#*:}

        usage () {
            echo "Usage: $app [-h] [SPHINX_PATH]    (default: \$PWD)"
            exit 1; }

        [ "\$1" == "-h" ] || [ "\$1" == "--help" ] && usage

        docker run -it -u \$USERID -v \$SPHINX_PATH:/host \$DESKTOP_ARGS \
            -p \$APP_PORT:\$APP_PORT $docker_image \
            -s \$SOCKET -b "$browser_name" /host
        EOF
        chmod 755 ~/bin/$app
        ''')))


def uninstall(c):
    print(c.render('rm -f ~/bin/$app'))


def serve(c):
    check_dependencies(c)
    clean_subproc()
    SphinxServer(c).manage()


def main(args):
    c = Config(conf, args=args, version=__version__)
    c.run(module='sphinxserve')

if __name__ == "__main__":
    main(sys.argv)
