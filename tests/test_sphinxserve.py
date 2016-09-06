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
from pytest import yield_fixture
from requests import get
from sphinxserve import main
from sphinxserve.lib import check_host, fs_event_ctx, Ret, Timeout


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
        try:
            check_host(c.host, c.port, timeout=5)
            yield c
        finally:
            c.proc.terminate()
            while c.proc.is_alive():
                sleep(0.1)
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


def test_fs_event_ctx():
    with tempdir() as tmpdir, fs_event_ctx(tmpdir, ['rst']) as fs_event:
        filename = tmpdir + '/test.rst'
        open(filename, 'w')
        assert filename == next(fs_event)

        filename = tmpdir + '/test2.rst'
        open(filename, 'w')
        assert filename == next(fs_event)


def test_functional(serve_ctx):
    def append(line, filename):
        '''append line to filename'''
        with open(filename, 'a') as fh:
            fh.write(line + '\n')

    def get_page(url, timestamp):
        with Timeout(5, False):
            while True:
                r = get(url)
                if timestamp != r.headers['last-modified']:
                    break
                sleep(0.3)
        return Ret(r.text, timestamp=r.headers['last-modified'])

    # Test main header in rendered page
    r = get('http://' + serve_ctx.socket)
    assert 'Test sphinxserve' in r.text
    timestamp = r.headers['last-modified']
    # Ensure sphinx detect rst timestamp changes
    sleep(1)

    # Test doc change detection and change reflected in new rendering
    filename = serve_ctx.tmpdir + '/index.rst'
    line = 'Detect doc change test'
    append(line, filename)
    ret = get_page('http://' + serve_ctx.socket, timestamp)
    assert line in ret
    sleep(1)

    line = 'New doc change test'
    append(line, filename)
    ret = get_page('http://' + serve_ctx.socket, ret.timestamp)
    assert line in ret
