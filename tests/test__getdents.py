import os

from unittest.mock import ANY

from pytest import fixture, mark, raises

from getdents._getdents import (
    DT_DIR,
    MIN_GETDENTS_BUFF_SIZE,
    getdents_raw,
)


@fixture
def fixt_regular_file(tmpdir):
    f = tmpdir.join('test.txt')
    f.write('content')

    fd = os.open(str(f), os.O_RDONLY)

    yield fd

    os.close(fd)


@fixture
def fixt_dir(tmpdir):
    for i in range(10):
        tmpdir.mkdir('subdir%d' % i)

    fd = os.open(str(tmpdir), os.O_DIRECTORY | os.O_RDONLY)

    yield fd

    os.close(fd)


def test_not_a_directory(fixt_regular_file):
    with raises(NotADirectoryError):
        getdents_raw(fixt_regular_file, MIN_GETDENTS_BUFF_SIZE)


def test_small_buffer(fixt_dir):
    with raises(ValueError):
        getdents_raw(fixt_dir, MIN_GETDENTS_BUFF_SIZE - 1)


@mark.skip(reason='No idea how to test this properly')
def test_malloc_fail(fixt_dir):
    with raises(MemoryError):
        getdents_raw(fixt_dir, 2**63)


def test_getdents_raw(fixt_dir):
    iterator = iter(sorted(
        getdents_raw(
            fixt_dir,
            MIN_GETDENTS_BUFF_SIZE,
        ),
        key=lambda d: d[2],
    ))

    assert next(iterator) == (ANY, DT_DIR, '.')
    assert next(iterator) == (ANY, DT_DIR, '..')

    for i, entry in enumerate(iterator):
        assert entry == (ANY, DT_DIR, 'subdir%d' % i)
