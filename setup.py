#!/usr/bin/env python

from setuptools import Extension, setup

setup(
    ext_modules=[
        Extension("getdents._getdents", sources=["getdents/_getdents.c"]),
    ],
)
