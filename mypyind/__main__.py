import sys
from pathlib import Path

from mypyind import mypyind_manager
from mypyind.constants import DATA_DIR


def main(at: str):
    path = Path(at)
    targets = list(open(DATA_DIR / 'seed.txt', 'r').readlines())
    mypyind_manager.find(targets=targets, at=path)


if __name__ == '__main__':
    try:
        target = sys.argv[1]
    except IndexError:
        raise Exception("Please provide a target file path.")
    main(at=target)
