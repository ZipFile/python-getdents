#!/usr/bin/env python

from setuptools import Extension, setup

setup(
    ext_modules=[
        Extension(
            "getdents._getdents",
            sources=["getdents/_getdents.c"],
            define_macros=[("Py_LIMITED_API", "0x030800f0")],
            py_limited_api=True,
        ),
    ],
)
