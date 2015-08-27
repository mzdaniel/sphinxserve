===========
sphinxserve
===========

.. image:: https://travis-ci.org/mzdanieltest/sphinxserve.svg?branch=master
    :target: https://travis-ci.org/mzdanieltest/sphinxserve
    :alt: [Build tests]
.. image:: https://img.shields.io/badge/github-repo-yellowgreen.jpg
    :target: https://github.com/mzdaniel/sphinxserve
    :alt: [Code repo]
.. image:: https://img.shields.io/pypi/v/sphinxserve.jpg
    :target: https://pypi.python.org/pypi/sphinxserve
    :alt: [Pypi package]


sphinxserve is a tool to effectively document projects
======================================================

Since the internet adopted HTML, many communities are trying to find ways to
write web pages in ways that can be pleasantly readable and writable. In our
python community, `reStructuredText`_ and `Sphinx`_ have been created to author
beautiful documentation. The goal of sphinxserve is to make them more
accessible, interactive, and convenient to use.


Examples of projects using sphinx
=================================

========================   ================================================
Sphinx                     http://sphinx-doc.org
Read The Docs              https://read-the-docs.readthedocs.org
Projects using sphinx      http://sphinx-doc.org/examples.html
sphinxjp.themes.revealjs   http://pythonhosted.org/sphinxjp.themes.revealjs
loadconfig                 http://loadconfig.glidelink.net/docs
========================   ================================================


Design considerations
=====================

sphinxserve was originally conceived as a Python and Linux project that can
visualize sphinx document modifications in real time while working on them. At
its core, sphinxserve uses the awesome projects `gevent`_  to provide
concurrency and event coordination, `flask`_ for web communication, Sphinx
for reStructucturedText rendering and of course `Python`_. sphinxserve used to
control browser reloading with xdotool, introducing a complex system tool
dependency. On release 0.7, sphinxserve decouples from this system dependency
using instead flask-sockets python package. The tradeoff here was to
temporarily drop python3 support until the gevent ecosystem officially
supports python3 which should be soon. Also, the filesystem notification tool
was upgraded to watchdog, removing another system dependency and making
the code more generic and cleaner. With these changes, as of release 0.7.2,
sphinxserve is able to run in other platforms as Windows for example.


Installation
============

sphinxserve can be installed either as a `python package`_, or as a `docker`_
application. On linux, it can also be installed as a pex `python executable`_

.. _python package: https://pypi.python.org/pypi/sphinxserve
.. _docker app: https://hub.docker.com/r/mzdaniel/sphinxserve
.. _Python executable: https://github.com/mzdaniel/sphinxserve/releases


Python executable (PEX)
~~~~~~~~~~~~~~~~~~~~~~~

This is the easiest (no compilation or fancy tooling needed) and smallest
(~9 MB) way to install sphinxserve using the excellent `PEX`_ tool. In itself,
it is a zipfile containing all python package dependencies and only requires
the python interpreter. This pex is verified to work at least on Debian>=7,
Ubuntu>=14, Centos>=7 and Arch distros.

System dependencies: glibc linux>=3, python>=2.7,<3 and a web browser
supporting websockets (Firefox, Chrome, etc)::

    $ wget -O ~/bin/sphinxserve https://github.com/mzdaniel/sphinxserve/releases/download/0.7.1/sphinxserve
    $ chmod 755 ~/bin/sphinxserve


Python package
~~~~~~~~~~~~~~

Linux system dependencies: glibc linux>=3, python>=2.7,<3, the C toolchain
(package names dependent on linux distro) to compile gevent and a web browser
supporting websockets. pip automatically downloads sphinxserve and its python
dependencies, compiles and builds wheel binary packages as needed and finally
install sphinxserve.

Windows system dependencies: Verified to work on Windows 7, python >=2.7,<3 and
a web browser supporting websockets with just pip installing.

In all systems::

    $ pip install sphinxserve


Docker application
~~~~~~~~~~~~~~~~~~

`Docker`_ is an extraordinary tool that simplifies the entire dependency tree
by including it in a system image. This makes the installation experience
much more pleasant and the ability to run on OSX, Windows and Linux with the
same image, assuming proper setup of the docker network and volume. Another
advantage is that a running image cannot see your filesystem by default.
Sharing directories and which ones is an explicit setup. This method is
verified to work on Linux so far.

System dependencies: docker and a web browser supporting websockets.

This installation command automatically downloads sphinxserve image (~40 MB)
and creates a small shell script ~/bin/sphinxserve that simplifies the running
interface with the following command::

    $ docker run mzdaniel/sphinxserve install | bash


Launching
=========

Assumming your sphinx project is in ~/docproj (containing conf.py) and
~/bin is in your shell $PATH::

    $ sphinxserve ~/docproj


Workflow
========

After launching sphinxserve, it will build the sphinx pages and serve them
by default on localhost:8888. Any saved changes on rst or txt files will
trigger docs rebuild.


Working in a Restructured text project
======================================

Lets put together all the pieces. A sphinx project needs at minimum 2 files:
the project file conf.py and a restructuredtext (rst) index file index.rst::

    cat > conf.py << EOF
    master_doc = 'index'
    EOF

    cat > index.rst << 'EOF'
    My awesome sphinx project
    =========================

    This is my first attempt to use `My awesome sphinx project`_
    EOF

At this point we can browse our project on localhost:8888 with just::

    sphinxserve


Thanks!
=======

* `Guido van Rossum`_ and `Linus Torvalds`_
* Georg Brandl & David Goodger for `Sphinx`_ and `reStructuredText`_
* Denis Bilenko, Armin Rigo & Christian Tismer for `Gevent`_ and `Greenlet`_
* Armin Ronacher for `Flask`_
* Jeffrey Gelens & Kenneth Reitz for `gevent websocket`_ and `flask sockets`_
* Yesudeep Mangalapilly for `watchdog`_
* Holger Krekel for `pytest`_ and `tox`_
* Eric Holscher for `Read The Docs`_
* Brian Wickman for `PEX`_
* Mark Otto, Jacob Thornton & Ryan Roemer for `Bootstrap`_  `sphinx bootstrap`_
* Hakim El Hattab & tell-k for `Revealjs`_ and `sphinx revealjs`_
* Solomon Hykes, Jerome Petazzoni and Sam Alba for `Docker`_
* The awesome Python, Linux and Git communities

.. _Guido van Rossum: http://en.wikipedia.org/wiki/Guido_van_Rossum
.. _Linus Torvalds: http://en.wikipedia.org/wiki/Linus_Torvalds
.. _python: https://www.python.org
.. _sphinx: http://sphinx-doc.org/tutorial.html
.. _restructuredtext: http://docutils.sourceforge.net/rst.html
.. _gevent: http://gevent.org
.. _greenlet: https://github.com/python-greenlet/greenlet
.. _flask: http://flask.pocoo.org
.. _gevent websocket:  https://bitbucket.org/Jeffrey/gevent-websocket
.. _flask sockets: https://github.com/kennethreitz/flask-sockets
.. _watchdog: https://github.com/gorakhargosh/watchdog
.. _pytest: http://pytest.org
.. _pex: https://github.com/pantsbuild/pex
.. _tox: https://testrun.org/tox
.. _read the docs: https://readthedocs.org
.. _bootstrap: http://getbootstrap.com
.. _sphinx bootstrap: http://ryan-roemer.github.io/sphinx-bootstrap-theme
.. _revealjs: http://lab.hakim.se/reveal-js
.. _sphinx revealjs: http://pythonhosted.org/sphinxjp.themes.revealjs
.. _docker: https://www.docker.com
