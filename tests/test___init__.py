from unittest.mock import Mock, patch, sentinel

from pytest import mark, raises

from getdents import (
    DT_DIR,
    DT_REG,
    DT_SOCK,
    DT_UNKNOWN,
    O_GETDENTS,
    DirectoryEntry,
    getdents,
    ls,
    ls_a,
)

DOT_FILES: list[DirectoryEntry] = [
    (1, DT_DIR, "."),
    (2, DT_DIR, ".."),
]
BAD_FILES: list[DirectoryEntry] = [
    (0, DT_REG, "file"),
    (3, DT_UNKNOWN, "???"),
]
SKIPPED_FILES = DOT_FILES + BAD_FILES
COMMON_FILES: list[DirectoryEntry] = [
    (4, DT_DIR, "dir"),
    (5, DT_REG, "file"),
]
HIDDEN_FILE: DirectoryEntry = (6, DT_SOCK, ".hidden")
LS_FILES = [*COMMON_FILES, HIDDEN_FILE]
ALL_FILES = [*DOT_FILES, *BAD_FILES, *COMMON_FILES, HIDDEN_FILE]


@mark.parametrize(
    ["dent", "expected"],
    [
        *((d, False) for d in SKIPPED_FILES),
        *((d, True) for d in COMMON_FILES),
        (HIDDEN_FILE, False),
    ],
)
def test_ls(dent: DirectoryEntry, expected: bool) -> None:
    assert ls(dent) == expected


@mark.parametrize(
    ["dent", "expected"],
    [
        *((d, False) for d in SKIPPED_FILES),
        *((d, True) for d in COMMON_FILES),
        (HIDDEN_FILE, True),
    ],
)
def test_ls_a(dent: DirectoryEntry, expected: bool) -> None:
    assert ls_a(dent) == expected


@patch("getdents.os")
@patch("getdents.getdents_raw")
def test_path(mock_getdents_raw: Mock, mock_os: Mock) -> None:
    mock_os.open.return_value = sentinel.fd

    list(getdents("/tmp", sentinel.size))

    mock_os.open.assert_called_once_with("/tmp", O_GETDENTS)
    mock_getdents_raw.assert_called_once_with(sentinel.fd, sentinel.size)
    mock_os.close.assert_called_once_with(sentinel.fd)


@patch("getdents.os")
@patch("getdents.getdents_raw", side_effect=[Exception])
def test_path_err(mock_getdents_raw: Mock, mock_os: Mock) -> None:
    mock_os.open.return_value = sentinel.fd

    with raises(Exception):
        list(getdents("/tmp", sentinel.size))

    mock_os.open.assert_called_once_with("/tmp", O_GETDENTS)
    mock_getdents_raw.assert_called_once_with(sentinel.fd, sentinel.size)
    mock_os.close.assert_called_once_with(sentinel.fd)


@patch("getdents.os")
@patch(
    "getdents.getdents_raw",
    return_value=iter(ALL_FILES),
)
def test_filtering(mock_getdents_raw: Mock, mock_os: Mock) -> None:
    assert list(getdents(".")) == LS_FILES


@patch("getdents.os")
@patch(
    "getdents.getdents_raw",
    return_value=iter(ALL_FILES),
)
def test_no_filtering(mock_getdents_raw: Mock, mock_os: Mock) -> None:
    assert list(getdents(".", filter_function=None)) == ALL_FILES
