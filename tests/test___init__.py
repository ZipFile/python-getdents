from unittest.mock import Mock, patch, sentinel

from pytest import raises

from getdents import DT_DIR, DT_REG, DT_UNKNOWN, O_GETDENTS, getdents


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
    return_value=iter(
        [
            (1, DT_DIR, "."),
            (2, DT_DIR, ".."),
            (3, DT_DIR, "dir"),
            (4, DT_REG, "file"),
            (5, DT_UNKNOWN, "???"),
            (0, DT_REG, "deleted"),
        ]
    ),
)
def test_filtering(mock_getdents_raw: Mock, mock_os: Mock) -> None:
    assert list(getdents(".")) == [
        (3, DT_DIR, "dir"),
        (4, DT_REG, "file"),
    ]
