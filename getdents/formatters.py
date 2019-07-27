from csv import writer as csv_writer
from itertools import chain
from json import dumps as json_dumps
from sys import stdout

from ._getdents import (
    DT_BLK,
    DT_CHR,
    DT_DIR,
    DT_FIFO,
    DT_LNK,
    DT_REG,
    DT_SOCK,
    DT_UNKNOWN,
)


HEADER = ('inode', 'type', 'name')
FORMATTERS = {}
TYPE_NAMES = {
    DT_BLK: 'blk',
    DT_CHR: 'chr',
    DT_DIR: 'dir',
    DT_FIFO: 'fifo',
    DT_LNK: 'lnk',
    DT_REG: 'reg',
    DT_SOCK: 'sock',
    DT_UNKNOWN: 'unknown',
}


def formatter(name, registry=FORMATTERS):
    def deco(fn):
        registry[name] = fn
        return fn
    return deco


@formatter('plain')
def format_plain(directory_entries, file=stdout):
    for inode, type, name in directory_entries:
        print(name, file=file)


class Echo:
    def write(self, value):
        return value


@formatter('csv')
def format_csv(directory_entries, file=stdout, headers=False):
    writer = csv_writer(Echo())

    for first in directory_entries:
        if headers:
            print(writer.writerow(HEADER), end='', file=file)

        for inode, type, name in chain((first,), directory_entries):
            print(
                writer.writerow((inode, TYPE_NAMES[type], name)),
                end='', file=file,
            )


@formatter('csv-headers')
def format_csv_headers(directory_entries, file=stdout):
    return format_csv(directory_entries, file=file, headers=True)


def json_encode(inode, type, name):
    return json_dumps({
        'inode': inode,
        'type': TYPE_NAMES[type],
        'name': name,
    })


@formatter('json')
def format_json(directory_entries, file=stdout):
    for inode, type, name in directory_entries:
        print(
            '[\n', json_encode(inode, type, name),
            sep='', end='', file=file,
        )

        for inode, type, name in directory_entries:
            print(
                ',\n', json_encode(inode, type, name),
                sep='', end='', file=file,
            )

        print('\n]', file=file)


@formatter('json-stream')
def format_json_stream(directory_entries, file=stdout):
    for inode, type, name in directory_entries:
        print(json_encode(inode, type, name), file=file)
