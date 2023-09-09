import os
import sys
from pathlib import Path
from typing import Iterable
from unittest.mock import ANY

from pytest import fixture, raises

from getdents._getdents import DT_DIR, MIN_GETDENTS_BUFF_SIZE, getdents_raw


@fixture
def fixt_regular_file(tmp_path: Path) -> Iterable[int]:
    f = tmp_path / "test.txt"
    f.write_text("content")

    fd = os.open(f, os.O_RDONLY)

    yield fd

    os.close(fd)


@fixture
def fixt_dir(tmp_path: Path) -> Iterable[int]:
    for i in range(10):
        (tmp_path / f"subdir{i}").mkdir()

    fd = os.open(tmp_path, os.O_DIRECTORY | os.O_RDONLY)

    yield fd

    os.close(fd)


def test_not_a_directory(fixt_regular_file: int) -> None:
    with raises(NotADirectoryError):
        getdents_raw(fixt_regular_file, MIN_GETDENTS_BUFF_SIZE)


def test_small_buffer(fixt_dir: int) -> None:
    with raises(ValueError):
        getdents_raw(fixt_dir, MIN_GETDENTS_BUFF_SIZE - 1)


def test_malloc_fail(fixt_dir: int) -> None:
    with raises(MemoryError):
        getdents_raw(fixt_dir, sys.maxsize)


def test_getdents_raw(fixt_dir: int) -> None:
    iterator = iter(
        sorted(
            getdents_raw(
                fixt_dir,
                MIN_GETDENTS_BUFF_SIZE,
            ),
            key=lambda d: d[2],
        )
    )

    assert next(iterator) == (ANY, DT_DIR, ".")
    assert next(iterator) == (ANY, DT_DIR, "..")

    for i, entry in enumerate(iterator):
        assert entry == (ANY, DT_DIR, "subdir%d" % i)
