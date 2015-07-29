#!/usr/bin/env python
'''Test sphinxserve.

Tox is recommented for running this pytest.
'''
import gevent.monkey
gevent.monkey.patch_all()

# Add project directory into sys.path and cd into it
from loadconfig.lib import addpath
from os import chdir
PROJECT_PATH = addpath(__file__, parent=True)
chdir(PROJECT_PATH)

from loadconfig import Config
from loadconfig.lib import tempdir
from pytest import fixture, yield_fixture
from multiprocessing import Process
from os import getpid, kill
from psutil import Process as ps
from requests import get
from signal import SIGTERM
from sphinxserve import uninstall, main  # noqa
from sphinxserve.lib import check_host, retry
from gevent import sleep


@fixture(scope='module')
def c(request):
    '''Config fixture. Return a config object for easy attribute access'''

    c = Config('''\
        app: sphinxserve
        host: localhost
        port: 8888
        socket: $host:$port
        ''')
    return c


@yield_fixture
def serve_ctx(c):
    '''Functional serve context for testing core sphinxserve functionality'''

    d = Config('''\
        index_rst: |
            ================
            Test sphinxserve
            ================

            Simple sphinxserve test
        conf_py: |
            source_suffix = '.rst'
            master_doc = 'index'
        ''')
    with tempdir() as tmpdir:
        d.tmpdir = tmpdir
        with open(tmpdir + '/conf.py', 'w') as fh:
            fh.write(d.conf_py)
        with open(tmpdir + '/index.rst', 'w') as fh:
            fh.write(d.index_rst)
        proc = Process(target=main, args=(['sphinxserve', 'serve', tmpdir],))
        proc.start()
        check_host(c.host, c.port, timeout=3)
        d.update({'proc': proc})
        yield d
        proc.terminate()
        proc.join()


def test_functional(c, serve_ctx):
    # Test main header in rendered page
    r = get('http://' + c.socket)
    assert 'Test sphinxserve' in r.text
    timestamp = r.headers['last-modified']

    # Test doc change detection and change reflected in new rendering
    filename = serve_ctx.tmpdir + '/index.rst'
    line = 'Detect doc change test'
    with open(filename, 'a') as fh:
        fh.write(line + '\n')
    for x in range(10):  # give up to 3 sec to do the test
        r = get('http://' + c.socket)
        if timestamp != r.headers['last-modified']:
            break
        sleep(0.3)
    assert line in r.text


def test_clean_subproc(c, serve_ctx):
    def active():
        '''Return True if inotify is active'''
        procs = ps(getpid()).children(recursive=True)
        return [n for n in procs if n.name() == 'inotifywait']

    # Ensure inotify is active within 3 seconds
    assert retry(active, count=10, sleep=0.3, success=bool)

    # Ensure terminating sphinxserve also terminates inotify
    kill(serve_ctx.proc.pid, SIGTERM)
    assert not retry(active, count=10, sleep=0.3, success=lambda x: not(x))
