from unittest.mock import Mock, patch, sentinel

from pytest import mark, raises

from getdents import DT_DIR, DT_REG, DT_UNKNOWN, O_GETDENTS, getdents


@patch('getdents.os')
@patch('getdents.getdents_raw')
def test_file_like(mock_getdents_raw, mock_os):
    mock_file = Mock(spec_set=['fileno'])
    mock_file.fileno.return_value = sentinel.fd

    list(getdents(mock_file, sentinel.size))

    assert mock_file.fileno.called
    assert mock_getdents_raw.called_once_with(sentinel.fd, sentinel.size)


@patch('getdents.os')
@patch('getdents.getdents_raw')
def test_path(mock_getdents_raw, mock_os):
    mock_path = Mock(spec='/tmp')
    mock_os.open.return_value = sentinel.fd

    list(getdents(mock_path, sentinel.size))

    assert mock_os.open.called_once_with(mock_path, O_GETDENTS)
    assert mock_getdents_raw.called_once_with(sentinel.fd, sentinel.size)


@mark.parametrize(['close_fd'], [(True,), (False,)])
@patch('getdents.os')
@patch('getdents.getdents_raw')
def test_fd(mock_getdents_raw, mock_os, close_fd):
    mock_fd = Mock(spec=4)

    list(getdents(mock_fd, sentinel.size, close_fd))

    assert mock_getdents_raw.called_once_with(mock_fd, sentinel.size)
    assert mock_os.close.called is close_fd


@patch('getdents.getdents_raw')
def test_alien(mock_getdents_raw):
    with raises(TypeError):
        list(getdents(object()))

    assert not mock_getdents_raw.called


@patch('getdents.getdents_raw', return_value=iter([
    (1, DT_DIR, '.'),
    (2, DT_DIR, '..'),
    (3, DT_DIR, 'dir'),
    (4, DT_REG, 'file'),
    (5, DT_UNKNOWN, '???'),
    (0, DT_REG, 'deleted'),
]))
def test_filtering(mock_getdents_raw):
    assert list(getdents(0)) == [
        (3, DT_DIR, 'dir'),
        (4, DT_REG, 'file'),
    ]
