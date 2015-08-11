#!/usr/bin/python

from os import environ
from re import sub
from setuptools import setup

for line in open('setup.cfg'):
    if line.startswith('version'):
        version = sub(".+ = (.+?)\n", r'\1', line)

environ["PBR_VERSION"] = version

setup(setup_requires=['pbr'], pbr=True)
