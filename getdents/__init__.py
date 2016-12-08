import os

from ._getdents import (  # noqa: ignore=F401
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


def getdents(path, buff_size=32768, close_fd=False):
    if hasattr(path, 'fileno'):
        fd = path.fileno()
    elif isinstance(path, str):
        fd = os.open(path, O_GETDENTS)
        close_fd = True
    elif isinstance(path, int):
        fd = path
    else:
        raise TypeError('Unsupported type: %s', type(path))

    try:
        yield from (
            (inode, type, name)
            for inode, type, name in getdents_raw(fd, buff_size)
            if not(type == DT_UNKNOWN or inode == 0 or name in ('.', '..'))
        )
    finally:
        if close_fd:
            os.close(fd)
