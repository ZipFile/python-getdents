import re
from sys import stdout

import pretend

from pytest import mark, raises

import getdents.cli as cli
from getdents.cli import main, parse_args
from getdents.formatters import (
    FORMATTERS,
    format_csv,
    format_json,
    format_plain,
)


@mark.parametrize(['args', 'expected'], [
    (['/tmp'], ('/tmp', 32768, format_plain)),
    (['-b', '1234', 'x', '-o', 'json'], ('x', 1234, format_json)),
    ([
        '--buffer-size', '9999',
        '--output-format', 'csv',
        'xxx',
    ], ('xxx', 9999, format_csv)),
])
def test_parse_args(args, expected):
    assert parse_args(args, 'test') == expected


def test_parse_args_min_buff_size(capsys):
    with raises(SystemExit):
        parse_args(['test', '-b', '0'], 'test')

    _, err = capsys.readouterr()

    assert re.search(r'Minimum buffer size is \d+', err) is not None


def test_main(monkeypatch):
    directory_entries = pretend.stub()

    @pretend.call_recorder
    def format_test(directory_entries, file):
        pass

    @pretend.call_recorder
    def getdents(path, buff_size=32768):
        return directory_entries

    monkeypatch.setitem(FORMATTERS, 'test', format_test)
    monkeypatch.setattr(cli, 'getdents', getdents)

    assert main(['x', '-o', 'test', '-b', '1024'], 'test') == 0
    assert getdents.calls == [pretend.call('x', buff_size=1024)]
    assert format_test.calls == [pretend.call(directory_entries, stdout)]


def test_main_memory_error(monkeypatch):
    monkeypatch.setattr(cli, 'getdents', pretend.raiser(MemoryError))

    assert main(['x']) == 3


def test_main_file_not_found_error(monkeypatch):
    monkeypatch.setattr(cli, 'getdents', pretend.raiser(FileNotFoundError))

    assert main(['x']) == 4


def test_main_not_a_directory_error(monkeypatch):
    monkeypatch.setattr(cli, 'getdents', pretend.raiser(NotADirectoryError))

    assert main(['x']) == 5


def test_main_permission_error(monkeypatch):
    monkeypatch.setattr(cli, 'getdents', pretend.raiser(PermissionError))

    assert main(['x']) == 6


def test_main_os_error(monkeypatch):
    monkeypatch.setattr(cli, 'getdents', pretend.raiser(OSError))

    assert main(['x']) == 7
