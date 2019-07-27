from argparse import ArgumentParser
from sys import stderr

from . import MIN_GETDENTS_BUFF_SIZE, getdents
from .formatters import FORMATTERS


def parse_args(args, prog):
    parser = ArgumentParser(
        prog=prog,
        description='Print directory contents.',
    )

    parser.add_argument('path', metavar='PATH')
    parser.add_argument(
        '-b', '--buffer-size',
        metavar='N',
        type=int,
        default=32768,
        help=(
            'Buffer size (in bytes) to allocate when iterating over directory'
        ),
    )
    parser.add_argument(
        '-o', '--output-format',
        metavar='NAME',
        default='plain',
        choices=list(FORMATTERS),
        help='Output format: %s' % ', '.join(sorted(FORMATTERS)),
    )

    parsed_args = parser.parse_args(args)
    buff_size = parsed_args.buffer_size

    if buff_size < MIN_GETDENTS_BUFF_SIZE:
        parser.error('Minimum buffer size is %s' % MIN_GETDENTS_BUFF_SIZE)

    return parsed_args.path, buff_size, FORMATTERS[parsed_args.output_format]


def main(args=None, prog=None):
    path, buff_size, fmt = parse_args(args, prog)

    try:
        fmt(getdents(path, buff_size=buff_size))
    except MemoryError:
        print(
            'Not enough memory to allocate', buff_size, 'bytes of data',
            file=stderr,
        )
        return 3
    except FileNotFoundError as e:
        print(e, file=stderr)
        return 4
    except NotADirectoryError as e:
        print(e, file=stderr)
        return 5
    except PermissionError as e:
        print(e, file=stderr)
        return 6
    except OSError as e:
        print(e, file=stderr)
        return 7

    return 0
