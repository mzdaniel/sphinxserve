'''sphinxserve library'''

import atexit
import gevent
from gevent import signal, sleep, Timeout
from loadconfig.lib import exc, run
import os
from signal import SIGINT, SIGTERM
import socket


def clean_subproc():
    '''Terminate process group children on exit or SIGTERM'''
    def _term_children():
        pids = run('ps -o pid --no-headers --ppid {}'.format(
            os.getpid())).split()
        for pid in pids:
            with exc(OSError):
                os.kill(int(pid), SIGTERM)

    def sigterm_hdl(*args):
        _term_children()
        exit(SIGTERM)

    with exc(OSError):
        os.setpgrp()
    signal(SIGTERM, sigterm_hdl)
    signal(SIGINT, sigterm_hdl)
    atexit.register(_term_children)


def check_host(host, port=22, timeout=1, recv=False):
    '''Return True if socket is active. timeout in seconds.
    Use recv=False if socket is silent after connection
    '''
    with Timeout(timeout), exc(Timeout) as e:
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
    return not bool(e())


def last(l):
    '''Get last element of a list or generator. Return None if empty.

    >>> last([1,2,3])
    3
    '''
    return next(reversed(list(l)), None)


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
