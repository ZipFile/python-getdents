#!/usr/bin/env python

from setuptools import Extension, find_packages, setup


tests_require = ['pytest', 'pretend']

setup(
    name='getdents',
    version='0.3',
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
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'test': tests_require,
    },
    ext_modules=[
        Extension('getdents._getdents', sources=['getdents/_getdents.c']),
    ],
    entry_points = {
        'console_scripts': ['python-getdents=getdents.cli:main'],
    },
    setup_requires=['pytest-runner'],
    tests_require=tests_require,
)
