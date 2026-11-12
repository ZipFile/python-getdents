import os
import sys
import sysconfig
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from random import random
from threading import Event
from time import sleep
from typing import Iterable
from unittest.mock import ANY

from pytest import fixture, mark, raises

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

    try:
        os.close(fd)
    except OSError:
        pass


def test_not_a_directory(fixt_regular_file: int) -> None:
    with raises(NotADirectoryError):
        getdents_raw(fixt_regular_file, MIN_GETDENTS_BUFF_SIZE)


def test_small_buffer(fixt_dir: int) -> None:
    with raises(ValueError):
        getdents_raw(fixt_dir, MIN_GETDENTS_BUFF_SIZE - 1)


def test_malloc_fail(fixt_dir: int) -> None:
    with raises(MemoryError):
        getdents_raw(fixt_dir, sys.maxsize)


class TestConstructor:
    def test_incomplete_args0(self) -> None:
        with raises(TypeError):
            getdents_raw()  # type: ignore[call-arg]

    def test_incomplete_args1(self) -> None:
        with raises(TypeError):
            getdents_raw(0)

    def test_invalid_fd(self) -> None:
        with raises(TypeError):
            getdents_raw("i", 1000)  # type: ignore[arg-type]

    def test_invalid_buff_size(self) -> None:
        with raises(TypeError):
            getdents_raw(0, "i")  # type: ignore[arg-type]


@mark.parametrize("name", ["__new__", "__init__", "custom_attribute"])
class TestImmutability:
    def test_setattr(self, name: str) -> None:
        with raises(TypeError):
            setattr(getdents_raw, name, lambda *args: None)

    def test_delattr(self, name: str) -> None:
        with raises(TypeError):
            delattr(getdents_raw, name)


def _assert_ordered(iterator: Iterable[tuple[int, int, str]]) -> None:
    iterator = iter(sorted(iterator, key=lambda d: d[2]))

    assert next(iterator) == (ANY, DT_DIR, ".")
    assert next(iterator) == (ANY, DT_DIR, "..")

    for i, entry in enumerate(iterator):
        assert entry == (ANY, DT_DIR, "subdir%d" % i)


def test_getdents_raw(fixt_dir: int) -> None:
    _assert_ordered(getdents_raw(fixt_dir, MIN_GETDENTS_BUFF_SIZE))


def test_getdents_close_mid_read(fixt_dir: int) -> None:
    iterator = getdents_raw(
        fixt_dir,
        MIN_GETDENTS_BUFF_SIZE,
    )

    next(iterator)

    os.close(fixt_dir)

    with raises(OSError, match=r"getdents64"):
        all(iterator)


@mark.skipif(
    not sysconfig.get_config_var("Py_GIL_DISABLED"),
    reason="Requires Python with GIL disabled",
)
def test_getdents_free_threading(fixt_dir: int) -> None:
    iterator = getdents_raw(
        fixt_dir,
        MIN_GETDENTS_BUFF_SIZE,
    )
    event = Event()

    def read_one() -> list[tuple[int, int, str]]:
        entries = []
        event.wait()
        for e in iterator:
            entries.append(e)
            sleep(random() * 0.01)
        return entries

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(read_one) for _ in range(3)]
        event.set()
        out = []
        for future in as_completed(futures):
            out.extend(future.result())

    _assert_ordered(out)


def test_getdents_call(fixt_dir: int) -> None:
    iterator = getdents_raw(
        fixt_dir,
        MIN_GETDENTS_BUFF_SIZE,
    )
    out = []

    for dirents in iter(iterator, None):
        out.extend(dirents)

    assert sorted(out)


def test_getdents_concurrent_mixed_access(fixt_dir: int, tmp_path: Path) -> None:
    for i in range(256):
        (tmp_path / f"entry{i}").touch()

    iterator = getdents_raw(fixt_dir, MIN_GETDENTS_BUFF_SIZE)
    event = Event()

    def read_iterator() -> list[tuple[int, int, str]]:
        event.wait()
        return list(iterator)

    def read_batches() -> list[tuple[int, int, str]]:
        event.wait()
        entries = []
        while (batch := iterator()) is not None:
            entries.extend(batch)
        return entries

    with ThreadPoolExecutor(max_workers=2) as executor:
        iterator_future = executor.submit(read_iterator)
        batch_future = executor.submit(read_batches)
        event.set()
        entries = iterator_future.result() + batch_future.result()

    names = [entry[2] for entry in entries]
    expected_names = {".", "..", *(f"subdir{i}" for i in range(10))}
    expected_names.update(f"entry{i}" for i in range(256))

    assert len(names) == len(expected_names)
    assert set(names) == expected_names
