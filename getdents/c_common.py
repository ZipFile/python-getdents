import errno
import fcntl
import os
import struct
from typing import Iterable

DIRENT64_RECORD = struct.Struct("=QqHB")
DIRENT64_OFFSET = DIRENT64_RECORD.size
O_GETDENTS = os.O_DIRECTORY | os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC

try:
    _NAME_MAX = os.pathconf("/", "PC_NAME_MAX")
except OSError:
    _NAME_MAX = 255

MIN_GETDENTS_BUFF_SIZE = _NAME_MAX + DIRENT64_OFFSET

DirectoryEntry = tuple[int, int, str]


def fd_is_directory(fd: int) -> bool:
    return bool(fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_DIRECTORY)


def decode_dirent_name(raw: memoryview) -> str:
    end = len(raw)

    while end > 0 and raw[end - 1] == 0:
        end -= 1

    return os.fsdecode(raw[:end].tobytes())


def validate(fd: int, buff_size: int) -> None:
    if not isinstance(fd, int):
        raise TypeError("fd must be an int")

    if not isinstance(buff_size, int):
        raise TypeError("buff_size must be an int")

    if not fd_is_directory(fd):
        raise NotADirectoryError("fd must refer to a directory")

    if buff_size < os.fpathconf(fd, "PC_NAME_MAX") + DIRENT64_OFFSET:
        raise ValueError("buff_size is too small")


def parse(data: memoryview, nread: int) -> Iterable[DirectoryEntry]:
    bpos = 0

    while bpos < nread:
        d_ino, _, d_reclen, d_type = DIRENT64_RECORD.unpack_from(data, bpos)
        name_start = bpos + DIRENT64_OFFSET
        name_end = bpos + d_reclen
        name = decode_dirent_name(data[name_start:name_end])
        bpos += d_reclen

        yield d_ino, d_type, name
