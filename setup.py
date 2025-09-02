#!/usr/bin/env python
import sysconfig

from setuptools import Extension, setup

if sysconfig.get_config_var("Py_GIL_DISABLED"):
    options = {}
    define_macros = []
    py_limited_api = False
else:
    options = {"bdist_wheel": {"py_limited_api": "cp310"}}
    define_macros = [("Py_LIMITED_API", "0x030A00f0")]
    py_limited_api = True


setup(
    options=options,
    ext_modules=[
        Extension(
            "getdents._getdents",
            sources=["getdents/_getdents.c"],
            define_macros=define_macros,
            py_limited_api=py_limited_api,
        ),
    ],
)
