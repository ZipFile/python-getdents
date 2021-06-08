from typing import Iterator, Tuple

DT_BLK: int
DT_CHR: int
DT_DIR: int
DT_FIFO: int
DT_LNK: int
DT_REG: int
DT_SOCK: int
DT_UNKNOWN: int
MIN_GETDENTS_BUFF_SIZE: int
O_GETDENTS: int

def getdents_raw(fd: int, buff_size: int) -> Iterator[Tuple[int, int, str]]: ...
