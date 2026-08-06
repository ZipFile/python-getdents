import os
from typing import Iterator

import cffi

from .c_common import DirectoryEntry
from .c_common import parse as _parse
from .c_common import validate as _validate

_ffi = cffi.FFI()
_ffi.cdef(
    """
static const long SYS_getdents64;
long syscall(long number, ...);
"""
)
lib = _ffi.verify(
    """
#include <sys/syscall.h>
"""
)
_libc = _ffi.dlopen(None)
SYS_getdents64 = lib.SYS_getdents64


def getdents_raw(fd: int, buff_size: int) -> Iterator[DirectoryEntry]:
    _validate(fd, buff_size)
    buff = _ffi.new("char[]", buff_size)

    with memoryview(_ffi.buffer(buff, buff_size)).cast("B") as data:
        while True:
            nread = _libc.syscall(
                SYS_getdents64,
                _ffi.cast("int", fd),
                buff,
                _ffi.cast("int", buff_size),
            )

            if nread == 0:
                return
            elif nread == -1:
                err = _ffi.errno
                raise OSError(err, os.strerror(err))

            yield from _parse(data, nread)
