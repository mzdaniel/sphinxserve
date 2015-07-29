===========
sphinxserve
===========

sphinxserve is a tool to effectively document projects
======================================================

`Sphinx`_ is a document processor tool that makes it easy to create intelligent
and beautiful documentation. The goal of sphinxserve is to make sphinx more
accessible, interactive, and convenient to use.


Design considerations
=====================

sphinxserve was originally conceived as a Python and Linux project that can
visualize sphinx document modifications in real time while working on them. At
its core, sphinxserve uses the awesome `gevent`_ project to provide concurrency
and event coordination.


Installation
============

sphinxserve can be installed either as a python package, or as a docker
application.

Python package
~~~~~~~~~~~~~~

System dependencies: python pip xdotool inotify-tools and a browser
(firefox, chromium, etc).

gevent dependency: An easier way to install gevent (and its greenlet
dependency) is using wheel packages::

    GITHUB="https://github.com/mzdaniel/wheel/raw/master"
    pip install $GITHUB/greenlet-0.4.7-cp27-none-linux_x86_64.whl
    pip install $GITHUB/gevent-1.1b1-cp27-none-linux_x86_64.whl

Alternatively, the C development toolchain is needed and used by pip.

sphinxserve (and python dependencies) installation using a wheel from pypi::

    pip install sphinxserve


Docker application
~~~~~~~~~~~~~~~~~~

`Docker`_ is an extraordinary tool that simplifies the entire dependency tree
by including it in a system image. This makes the installation experience
much more pleasant.

System dependencies: docker and a browser

This installation command automatically downloads sphinxserve image and
creates a small shell script ~/bin/sphinxserve that simplifies the running
interface::

    $ docker run mzdaniel/sphinx install | bash


Launching
=========
::

    # Assumming your sphinx project is in ~/docproj (containing conf.py),
    # and ~/bin is in your shell $PATH

    $ sphinxserve ~/docproj


Workflow
========

After launching sphinxserve, it looks for a browser, while rebuilds the sphinx
pages. When it is done, it opens a new tab on the browser pointing to the new
rendered page. As soon as there is a document change, it automatically
re-renders the docs and reloads the browser.


.. _Sphinx: http://sphinx-doc.org/tutorial.html
.. _gevent: http://gevent.org
.. _greenlet: https://github.com/python-greenlet/greenlet
.. _docker: https://www.docker.com
