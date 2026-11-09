#!/usr/bin/env python
import sys
import sysconfig

from setuptools import Extension, setup

free_threaded = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))

if not free_threaded:
    options = {"bdist_wheel": {"py_limited_api": "cp312"}}
    define_macros = [("Py_LIMITED_API", "0x030c0000")]
    py_limited_api = True
elif sys.version_info >= (3, 15):
    options = {"bdist_wheel": {"py_limited_api": "cp315"}}
    define_macros = [("Py_TARGET_ABI3T", "0x030f0000")]
    py_limited_api = True
else:
    options = {}
    define_macros = []
    py_limited_api = False


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
