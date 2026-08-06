import ctypes
import ctypes.util
import os
from collections.abc import Iterator

import seccomp

from .c_common import DirectoryEntry
from .c_common import parse as _parse
from .c_common import validate as _validate

_libc = ctypes.CDLL(None, use_errno=True)
_libc.syscall.argtypes = (
    ctypes.c_long,
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.c_size_t,
)
_libc.syscall.restype = ctypes.c_long
SYS_getdents64 = seccomp.resolve_syscall(seccomp.Arch(), "getdents64")


def getdents_raw(fd: int, buff_size: int) -> Iterator[DirectoryEntry]:
    _validate(fd, buff_size)

    buff = ctypes.create_string_buffer(buff_size)

    with memoryview(buff).cast("B") as data:
        while True:
            nread = _libc.syscall(
                SYS_getdents64,
                fd,
                ctypes.byref(buff),
                buff_size,
            )

            if nread == 0:
                return
            elif nread == -1:
                err = ctypes.get_errno()
                raise OSError(err, os.strerror(err))

            yield from _parse(data, nread)
