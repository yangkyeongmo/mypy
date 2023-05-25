import os
import sys
from pathlib import Path

from mypy.build import MYPYIND_PATH
from mypyind.constants import FULLNAMES_PATH, MYPYIND_REQUIRED_OPTIONS, MAIN_PATH, FULLNAMES_DEBUG_PATH


def main(target: str):
    path = Path(target)

    fullnames = set(open(FULLNAMES_PATH, 'r').readlines())
    options = ' '.join(MYPYIND_REQUIRED_OPTIONS)
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

        _sort_stored_fullnames()


def _sort_stored_fullnames():
    fullnames = sorted(list(set(open(MYPYIND_PATH / 'fullnames.txt', 'r').readlines())))
    with open(MYPYIND_PATH / 'fullnames.txt', 'w') as f:
        f.writelines(fullnames)


def _debug_write_level(level):
    with open(FULLNAMES_DEBUG_PATH, 'a') as f:
        f.write(f'{level=}\n')


if __name__ == '__main__':
    try:
        target = sys.argv[1]
    except IndexError:
        raise Exception("Please provide a target file path.")
    main(target=target)
