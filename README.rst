===========
sphinxserve
===========

sphinxserve is a tool to effectively document projects
======================================================

Since the internet adopted HTML, many communities are trying to find ways to
write web pages in ways that can be pleasantly readable and writable. In our
python community, `reStructuredText`_ and `Sphinx`_ have been created to author
beautiful documentation. The goal of sphinxserve is to make them more
accessible, interactive, and convenient to use.


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
supports python3 which should be soon. sphinxserve also upgraded its filesystem
notification tool to watchdog, removing another system dependency and making
the code more generic, cleaner and closer to run in other operating systems.


Installation
============

sphinxserve can be installed either as a `python package`_, or as a `docker`_
application. A pex `python executable`_ will be available.

.. _python package: https://pypi.python.org/pypi/sphinxserve
.. _docker app: https://registry.hub.docker.com/u/mzdaniel/sphinxserve
.. _Python executable: https://github.com/mzdaniel/sphinxserve


Python package
~~~~~~~~~~~~~~

System dependencies: python==2.7, pip>=7, the C toolchain (package names
dependent on linux distro) to compile gevent and a web browser.

pip automatically downloads sphinxserve and its python dependencies, compiles
and builds wheel binary packages as needed and finally install sphinxserve
using::

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
