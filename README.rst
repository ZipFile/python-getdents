===============
Python getdents
===============

Iterate large directories efficiently with python.

About
=====

``python-getdents`` is a simple wrapper around Linux system call ``getdents64`` (see ``man getdents`` for details). `Here's <http://be-n.com/spw/you-can-list-a-million-files-in-a-directory-but-not-with-ls.html>`_ some study on why ``ls``, ``os.listdir()`` and others are so slow when dealing with extremely large directories.


TODO
====

* Verify that implementation works on platforms other than ``x86_64``.


Install
=======

.. code-block:: sh

    pip install getdents

For development
---------------

.. code-block:: sh

    python3 -m venv env
    . env/bin/activate
    pip install -e .

Run tests
=========

.. code-block:: sh

    ulimit -v 33554432 && py.test tests/

Or

.. code-block:: sh

    ulimit -v 33554432 && ./setup.py test

Usage
=====

.. code-block:: python

    from getdents import getdents

    for inode, type, name in getdents('/tmp', 32768):
        print(name)

Advanced
--------

.. code-block:: python

    import os
    from getdents import *

    fd = os.open('/tmp', O_GETDENTS)

    for inode, type, name in getdents_raw(fd, 2**20):
        print({
                DT_BLK:     'blockdev',
                DT_CHR:     'chardev ',
                DT_DIR:     'dir     ',
                DT_FIFO:    'pipe    ',
                DT_LNK:     'symlink ',
                DT_REG:     'file    ',
                DT_SOCK:    'socket  ',
                DT_UNKNOWN: 'unknown ',
            }[type], {
                True:  'd',
                False: ' ',
            }[inode == 0],
            name,
        )

    os.close(fd)
