===============
Python getdents
===============

Iterate large directories efficiently with python.

About
=====

``python-getdents`` is a simple wrapper around Linux system call ``getdents64`` (see ``man getdents`` for details).

Implementation is based on solution descibed in `You can list a directory containing 8 million files! But not with ls. <http://be-n.com/spw/you-can-list-a-million-files-in-a-directory-but-not-with-ls.html>`_ article by Ben Congleton.

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

Building Wheels
~~~~~~~~~~~~~~~

.. code-block:: sh

    pip install cibuildwheel
    cibuildwheel --platform linux --output-dir wheelhouse

Run tests
=========

.. code-block:: sh

    ulimit -v 33554432 && py.test tests/

Usage
=====

.. code-block:: python

    from getdents import getdents

    for inode, type_, name in getdents("/tmp"):
        print(name)

Advanced
--------

While ``getdents`` provides a convenient wrapper with ls-like filtering, you can use ``getdents_raw`` for more control:

.. code-block:: python

    import os
    from getdents import DT_LNK, O_GETDENTS, getdents_raw

    fd = os.open("/tmp", O_GETDENTS)

    for inode, type_, name in getdents_raw(fd, 2**20):
        if type_ == DT_LNK and inode != 0:
            print("found symlink:", name, "->", os.readlink(name, dir_fd=fd))

    os.close(fd)

Batching
~~~~~~~~

In case you need more control over syscalls, you may call instance of ``getdents_raw`` instead.
Each call corresponds to single ``getdents64`` syscall, returning list of hovever many entries fits in buffer size.
Call returns ``None`` when there are no more entries to read.

.. code-block:: python

    it = getdents_raw(fd, 2**20)

    for batch in iter(it, None):
         for inode, type, name in batch:
            ...

Free-threading
~~~~~~~~~~~~~~

While it is not so wise idea to do an I/O from multiple threads on a single file descriptor, you can do it if you need to.
This package supports free-threading (nogil) in Python.

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
