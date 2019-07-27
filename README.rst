===============
Python getdents
===============

Iterate large directories efficiently with python.

About
=====

``python-getdents`` is a simple wrapper around Linux system call ``getdents64`` (see ``man getdents`` for details). `More details <http://be-n.com/spw/you-can-list-a-million-files-in-a-directory-but-not-with-ls.html>`_ on approach.

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
    pip install -e .[test]

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

CLI
---

Usage
~~~~~

::

    python-getdents [-h] [-b N] [-o NAME] PATH

Options
~~~~~~~

+--------------------------+-------------------------------------------------+
| Option                   | Description                                     |
+==========================+=================================================+
| ``-b N``                 | Buffer size (in bytes) to allocate when         |
|                          | iterating over directory. Default is 32768, the |
|                          | same value used by glibc, you probably want to  |
+--------------------------+ increase this value. Try starting with 16777216 |
| ``--buffer-size N``      | (16 MiB). Best performance is achieved when     |
|                          | buffer size rounds to size of the file system   |
|                          | block.                                          |
+--------------------------+-------------------------------------------------+
| ``-o NAME``              | Output format:                                  |
|                          |                                                 |
|                          | * ``plain`` (default) Print only names.         |
|                          | * ``csv`` Print as comma-separated values in    |
+--------------------------+   order: inode, type, name.                     |
| ``--output-format NAME`` | * ``csv-headers`` Same as ``csv``, but print    |
|                          |   headers on the first line also.               |
|                          | * ``json`` output as JSON array.                |
|                          | * ``json-stream`` output each directory entry   |
|                          |   as single json object separated by newline.   |
+--------------------------+-------------------------------------------------+

Exit codes
~~~~~~~~~~

* 3 - Requested buffer is too large
* 4 - ``PATH`` not found.
* 5 - ``PATH`` is not a directory.
* 6 - Not enough permissions to read contents of the ``PATH``.

Examples
~~~~~~~~

.. code-block:: sh

    python-getdents /path/to/large/dir
    python -m getdents /path/to/large/dir
    python-getdents /path/to/large/dir -o csv -b 16777216 > dir.csv
