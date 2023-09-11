#!/usr/bin/env python
from typing import Tuple

from setuptools import Extension, setup
from wheel.bdist_wheel import bdist_wheel


class bdist_wheel_abi3(bdist_wheel):
    def get_tag(self) -> Tuple[str, str, str]:
        # From https://github.com/joerick/python-abi3-package-sample/blob/main/setup.py
        python, abi, plat = super().get_tag()

        if python.startswith("cp"):
            # on CPython, our wheels are abi3 and compatible back to 3.8
            return "cp38", "abi3", plat

        return python, abi, plat


setup(
    cmdclass={"bdist_wheel": bdist_wheel_abi3},
    ext_modules=[
        Extension(
            "getdents._getdents",
            sources=["getdents/_getdents.c"],
            define_macros=[("Py_LIMITED_API", "0x030800f0")],
            py_limited_api=True,
        ),
    ],
)
