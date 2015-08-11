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

from gevent import joinall, sleep, spawn
from loadconfig import Config
from loadconfig.lib import tempdir, capture_stream
from multiprocessing import Process
from os import getpid, kill
from psutil import Process as ps
from pytest import yield_fixture
from requests import get
from signal import SIGTERM
from sphinxserve import main
from sphinxserve.lib import check_host, retry, Timeout


@yield_fixture
def serve_ctx():
    '''Functional serve context for testing core sphinxserve functionality'''

    c = Config('''\
        app: sphinxserve
        host: localhost
        port: 8888
        socket: $host:$port
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
        c.tmpdir = tmpdir
        with open(tmpdir + '/conf.py', 'w') as fh:
            fh.write(c.conf_py)
        with open(tmpdir + '/index.rst', 'w') as fh:
            fh.write(c.index_rst)

        c.proc = Process(target=main, args=(['sphinxserve', tmpdir],))
        c.proc.start()
        check_host(c.host, c.port, timeout=3)
        yield c
        c.proc.terminate()
        c.proc.join()


def test_gevent():
    '''simple gevent test'''
    def first():
        print('1')
        sleep(0)
        print('3')

    def second():
        print('2')
        sleep(0)
        print('4')

    with capture_stream() as stdout:
        joinall([spawn(first), spawn(second)])
    assert ('1\n2\n3\n4\n' == stdout.getvalue())


def test_sphinxserve_Timeout():
    '''Test Timeout subclass context manager'''
    with Timeout(0.2) as timeout:
        pass
    assert timeout.expired is False

    with Timeout(0.2, False) as timeout:
        sleep(1)
    assert timeout.expired is True


def test_functional(serve_ctx):
    # Test main header in rendered page
    r = get('http://' + serve_ctx.socket)
    assert 'Test sphinxserve' in r.text
    timestamp = r.headers['last-modified']

    # Test doc change detection and change reflected in new rendering
    filename = serve_ctx.tmpdir + '/index.rst'
    line = 'Detect doc change test'
    with open(filename, 'a') as fh:
        fh.write(line + '\n')

    for x in range(10):  # give up to 3 sec to do the test
        r = get('http://' + serve_ctx.socket)
        if timestamp != r.headers['last-modified']:
            break
        sleep(0.3)
    assert line in r.text


def test_clean_subproc(serve_ctx):
    def active():
        '''Return True if inotify is active'''
        procs = ps(getpid()).children(recursive=True)
        return bool([n for n in procs if 'watchmedo' in ' '.join(n.cmdline())])

    # Ensure inotify is active within 3 seconds
    assert retry(active, count=10, sleep=0.3, success=bool)

    # Ensure terminating sphinxserve also terminates inotify
    kill(serve_ctx.proc.pid, SIGTERM)
    assert not retry(active, count=10, sleep=0.3, success=lambda x: not(x))
