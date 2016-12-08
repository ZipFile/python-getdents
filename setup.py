#!/usr/bin/env python

from setuptools import setup

from distutils.core import Extension


setup(
    name='getdents',
    version='0.1',
    description='Python binding to linux syscall getdents64.',
    long_description=open('README.rst').read(),
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: System :: Filesystems',
    ],
    keywords='getdents',
    author='Anatolii Aniskovych',
    author_email='lin.aaa.lin@gmail.com',
    url='http://github.com/ZipFile/python-getdents',
    license='BSD-2-Clause',
    packages=['getdents'],
    include_package_data=True,
    zip_safe=False,
    ext_modules = [
        Extension('getdents._getdents', sources=['getdents/_getdents.c']),
    ],
    install_requires=[
      'setuptools',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
)
