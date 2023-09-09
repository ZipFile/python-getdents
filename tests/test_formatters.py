from io import StringIO
from typing import Any, Iterable, Iterator, TextIO

from pytest import fixture

from getdents import DirectoryEntry
from getdents._getdents import (
    DT_BLK,
    DT_CHR,
    DT_DIR,
    DT_FIFO,
    DT_LNK,
    DT_REG,
    DT_SOCK,
    DT_UNKNOWN,
)
from getdents.formatters import (
    Echo,
    FormatterRegistry,
    format_csv,
    format_csv_headers,
    format_json,
    format_json_stream,
    format_plain,
    formatter,
    json_encode,
)


@fixture
def dirents() -> Iterator[DirectoryEntry]:
    return iter(
        [
            (1, DT_BLK, "block_device"),
            (2, DT_CHR, "character_device"),
            (3, DT_DIR, "directory"),
            (4, DT_FIFO, "named_pipe"),
            (5, DT_LNK, "symbolic_link"),
            (6, DT_REG, "file"),
            (7, DT_SOCK, "socket"),
            (8, DT_UNKNOWN, "unknown"),
        ]
    )


def test_formatter() -> None:
    def fn(
        directory_entries: Iterable[DirectoryEntry],
        file: TextIO,
    ) -> None:
        """Do nothing"""

    registry: FormatterRegistry = {}

    assert formatter("test", registry=registry)(fn) is fn
    assert registry == {"test": fn}


def test_format_plain(dirents: Iterator[DirectoryEntry]) -> None:
    output = StringIO()

    format_plain(dirents, output)

    assert output.getvalue() == (
        "block_device\n"
        "character_device\n"
        "directory\n"
        "named_pipe\n"
        "symbolic_link\n"
        "file\n"
        "socket\n"
        "unknown\n"
    )


def test_echo() -> None:
    echo = Echo()
    value: Any = object()

    assert echo.write(value) is value


def test_format_csv(dirents: Iterator[DirectoryEntry]) -> None:
    output = StringIO()

    format_csv(dirents, output)

    assert output.getvalue() == (
        "1,blk,block_device\r\n"
        "2,chr,character_device\r\n"
        "3,dir,directory\r\n"
        "4,fifo,named_pipe\r\n"
        "5,lnk,symbolic_link\r\n"
        "6,reg,file\r\n"
        "7,sock,socket\r\n"
        "8,unknown,unknown\r\n"
    )


def test_format_csv_headers(dirents: Iterator[DirectoryEntry]) -> None:
    output = StringIO()

    format_csv_headers(dirents, output)

    assert output.getvalue() == (
        "inode,type,name\r\n"
        "1,blk,block_device\r\n"
        "2,chr,character_device\r\n"
        "3,dir,directory\r\n"
        "4,fifo,named_pipe\r\n"
        "5,lnk,symbolic_link\r\n"
        "6,reg,file\r\n"
        "7,sock,socket\r\n"
        "8,unknown,unknown\r\n"
    )


def test_json_encode() -> None:
    assert json_encode(0, DT_UNKNOWN, "test") == (
        '{"inode": 0, "type": "unknown", "name": "test"}'
    )


def test_format_json(dirents: Iterator[DirectoryEntry]) -> None:
    output = StringIO()

    format_json(dirents, output)

    assert output.getvalue() == (
        "[\n"
        '{"inode": 1, "type": "blk", "name": "block_device"},\n'
        '{"inode": 2, "type": "chr", "name": "character_device"},\n'
        '{"inode": 3, "type": "dir", "name": "directory"},\n'
        '{"inode": 4, "type": "fifo", "name": "named_pipe"},\n'
        '{"inode": 5, "type": "lnk", "name": "symbolic_link"},\n'
        '{"inode": 6, "type": "reg", "name": "file"},\n'
        '{"inode": 7, "type": "sock", "name": "socket"},\n'
        '{"inode": 8, "type": "unknown", "name": "unknown"}\n'
        "]\n"
    )


def test_format_json_stream(dirents: Iterator[DirectoryEntry]) -> None:
    output = StringIO()

    format_json_stream(dirents, output)

    assert output.getvalue() == (
        '{"inode": 1, "type": "blk", "name": "block_device"}\n'
        '{"inode": 2, "type": "chr", "name": "character_device"}\n'
        '{"inode": 3, "type": "dir", "name": "directory"}\n'
        '{"inode": 4, "type": "fifo", "name": "named_pipe"}\n'
        '{"inode": 5, "type": "lnk", "name": "symbolic_link"}\n'
        '{"inode": 6, "type": "reg", "name": "file"}\n'
        '{"inode": 7, "type": "sock", "name": "socket"}\n'
        '{"inode": 8, "type": "unknown", "name": "unknown"}\n'
    )
