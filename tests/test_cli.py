import re
from sys import stdout
from typing import List, Tuple
from unittest.mock import Mock

from pytest import CaptureFixture, MonkeyPatch, mark, raises

import getdents.cli as cli
from getdents.cli import main, parse_args
from getdents.formatters import (
    FORMATTERS,
    Formatter,
    format_csv,
    format_json,
    format_plain,
)


@mark.parametrize(
    ["args", "expected"],
    [
        (["/tmp"], ("/tmp", 32768, format_plain)),
        (["-b", "1234", "x", "-o", "json"], ("x", 1234, format_json)),
        (
            [
                "--buffer-size",
                "9999",
                "--output-format",
                "csv",
                "xxx",
            ],
            ("xxx", 9999, format_csv),
        ),
    ],
)
def test_parse_args(args: List[str], expected: Tuple[str, int, Formatter]) -> None:
    assert parse_args(args, "test") == expected


def test_parse_args_min_buff_size(capsys: CaptureFixture[str]) -> None:
    with raises(SystemExit):
        parse_args(["test", "-b", "0"], "test")

    _, err = capsys.readouterr()

    assert re.search(r"Minimum buffer size is \d+", err) is not None


def test_main(monkeypatch: MonkeyPatch) -> None:
    format_test = Mock()
    getdents = Mock()
    directory_entries = getdents.return_value

    monkeypatch.setitem(FORMATTERS, "test", format_test)
    monkeypatch.setattr(cli, "getdents", getdents)

    assert main(["x", "-o", "test", "-b", "1024"], "test") == 0

    getdents.assert_called_once_with("x", buff_size=1024)
    format_test.assert_called_once_with(directory_entries, stdout)


def test_main_memory_error(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "getdents", Mock(side_effect=MemoryError))

    assert main(["x"]) == 3


def test_main_file_not_found_error(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "getdents", Mock(side_effect=FileNotFoundError))

    assert main(["x"]) == 4


def test_main_not_a_directory_error(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "getdents", Mock(side_effect=NotADirectoryError))

    assert main(["x"]) == 5


def test_main_permission_error(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "getdents", Mock(side_effect=PermissionError))

    assert main(["x"]) == 6


def test_main_os_error(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "getdents", Mock(side_effect=OSError))

    assert main(["x"]) == 7
