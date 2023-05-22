import os
import sys
from pathlib import Path

DIR = Path(__file__).parent
FULLNAMES_PATH = Path(DIR, 'fullnames.txt')
FULLNAMES_DEBUG_PATH = Path(DIR, 'fullnames_debug.txt')
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
    if not path.is_dir():
        raise Exception(f"Given file path is not dir path. Given: {path}")

    fullnames = set(open(FULLNAMES_PATH, 'r').readlines())
    options = ' '.join(REQUIRED_OPTIONS)
    cmd = f'python {MAIN_PATH} {path} {options}'

    _iterate(cmd, fullnames)


def _iterate(cmd, fullnames):
    os.system(cmd)
    i = 0
    _debug_write_level(i)
    print(f'{i=}')
    new_fullnames = set(open(FULLNAMES_PATH, 'r').readlines())
    while fullnames != new_fullnames:
        i += 1
        _debug_write_level(i)
        print(f'{i=}')
        os.system(cmd)
        fullnames = new_fullnames
        new_fullnames = set(open(FULLNAMES_PATH, 'r').readlines())


def _debug_write_level(level):
    with open(FULLNAMES_DEBUG_PATH, 'a') as f:
        f.write(f'{level=}\n')


if __name__ == '__main__':
    try:
        target = sys.argv[1]
    except IndexError:
        raise Exception("Please provide a target file path.")
    main(target=target)
