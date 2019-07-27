from sys import exit

from . import __name__ as prog
from .cli import main


if __name__ == '__main__':  # pragma: no cover
    exit(main(prog=prog))
