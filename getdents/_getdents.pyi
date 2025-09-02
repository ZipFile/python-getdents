from typing import Self

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

class getdents_raw:
    def __init__(self, fd: int, buff_size: int = 1048576, /) -> None: ...
    def __next__(self) -> tuple[int, int, str]: ...
    def __iter__(self) -> Self: ...
    def __call__(self) -> list[tuple[int, int, str]] | None: ...
