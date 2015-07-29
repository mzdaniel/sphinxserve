#!/usr/bin/python

from os import environ
from re import sub
from setuptools import setup

for line in open('sphinxserve/__init__.py'):
    if line.startswith('__version__'):
        version = sub(".+'(.+?)'\n", r'\1', line)

environ["PBR_VERSION"] = version

setup(setup_requires=['pbr'], pbr=True)
