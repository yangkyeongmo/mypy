import os
import sys
from pathlib import Path

from mypyind.utils import get_fullname_file, get_fullname_debug_file

DIR = Path(__file__).parent
INI_PATH = Path(DIR, 'mypyind.ini')

MYPY_DIR = Path(DIR.parent, 'mypy')
MAIN_PATH = Path(MYPY_DIR, '__main__.py')

REQUIRED_OPTIONS = [
    '--cache-dir=/dev/null',  # disable caching
    '--namespace-packages',
    f'--config-file={INI_PATH}',  # use custom config file
]


def main(target: str):
    path = Path(target)

    fullnames = set(get_fullname_file().readlines())
    options = ' '.join(REQUIRED_OPTIONS)
    cmd = f'python {MAIN_PATH} {path} {options}'

    _iterate(cmd, fullnames)


def _iterate(cmd, fullnames):
    os.system(cmd)
    i = 0
    _debug_write_level(i)
    print(f'{i=}')
    new_fullnames = set(get_fullname_file().readlines())
    while fullnames != new_fullnames:
        i += 1
        _debug_write_level(i)
        print(f'{i=}')
        os.system(cmd)
        fullnames = new_fullnames
        new_fullnames = set(get_fullname_file().readlines())


def _debug_write_level(level):
    with get_fullname_debug_file('a') as f:
        f.write(f'{level=}\n')


if __name__ == '__main__':
    try:
        target = sys.argv[1]
    except IndexError:
        raise Exception("Please provide a target file path.")
    main(target=target)
