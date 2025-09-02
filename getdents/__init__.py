import os
from collections.abc import Callable
from typing import Iterator, TypeAlias

from .__about__ import __version__
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

DOT_ENTRIES = (".", "..")
DirectoryEntry: TypeAlias = tuple[
    int,  # inode
    int,  # type
    str,  # name
]
DirectoryEntryFilterFunction: TypeAlias = Callable[[DirectoryEntry], bool]


def ls(d: DirectoryEntry) -> bool:
    """``ls``-like filter for raw directory entries"""
    return not (d[0] == 0 or d[1] == DT_UNKNOWN or d[2][0] == ".")


def ls_a(d: DirectoryEntry) -> bool:
    """``ls -a``-like filter for raw directory entries"""
    return not (d[0] == 0 or d[1] == DT_UNKNOWN or d[2] in DOT_ENTRIES)


def getdents(
    path: str,
    buff_size: int = 1048576,
    filter_function: DirectoryEntryFilterFunction | None = ls_a,
) -> Iterator[DirectoryEntry]:
    """Get directory entries.

    Wrapper around getdents_raw(), simulates ls behaviour: ignores deleted
    files, skips . and .. entries.

    Note:
       Buffer size of glibc's readdir() is 32KiB. You probably want more, so
       our default is set to 1MiB.

    Note:
       Larger buffer will result in a fewer syscalls, so for really large
       dirs you should pick larger value.

    Note:
       For better performance, set buffer size to be multiple of your block
       size for filesystem I/O.

    Args:
        path: Location of the directory.
        buff_size: Buffer size in bytes for getdents64 syscall.
        filter_function: Function to filter directory entries.
    """

    fd = os.open(path, O_GETDENTS)

    try:
        it: Iterator[DirectoryEntry] = getdents_raw(fd, buff_size)

        if filter_function:
            it = filter(filter_function, it)

        yield from it
    finally:
        os.close(fd)


__all__ = [
    "__version__",
    "DOT_ENTRIES",
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
    "ls",
    "ls_a",
]
