import os
from typing import Iterator, Tuple

from ._getdents import (
    DT_BLK,
    DT_CHR,
    DT_DIR,
    DT_FIFO,
    DT_LNK,
    DT_REG,
    DT_SOCK,
    DT_UNKNOWN,
    MIN_GETDENTS_BUFF_SIZE,
    O_GETDENTS,
    getdents_raw,
)

DirectoryEntry = Tuple[int, int, str]


def getdents(path: str, buff_size: int = 32768) -> Iterator[DirectoryEntry]:
    """Get directory entries.

    Wrapper around getdents_raw(), simulates ls behaviour: ignores deleted
    files, skips . and .. entries.

    Note:
       Default buffer size is 32k, it's a default allocation size of glibc's
       readdir() implementation.

    Note:
       Larger buffer will result in a fewer syscalls, so for really large
       dirs you should pick larger value.

    Note:
       For better performance, set buffer size to be multiple of your block
       size for filesystem I/O.

    Args:
        path (str): Location of the directory.
        buff_size (int): Buffer size in bytes for getdents64 syscall.
    """

    fd = os.open(path, O_GETDENTS)

    try:
        yield from (
            (inode, type, name)
            for inode, type, name in getdents_raw(fd, buff_size)
            if not (type == DT_UNKNOWN or inode == 0 or name in (".", ".."))
        )
    finally:
        os.close(fd)


__all__ = [
    "DT_BLK",
    "DT_CHR",
    "DT_DIR",
    "DT_FIFO",
    "DT_LNK",
    "DT_REG",
    "DT_SOCK",
    "DT_UNKNOWN",
    "MIN_GETDENTS_BUFF_SIZE",
    "O_GETDENTS",
    "DirectoryEntry",
    "getdents",
    "getdents_raw",
]
