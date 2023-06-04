import sys
from pathlib import Path

from mypyind.src.caller import mypyind_caller
from mypyind.src.constants import DATA_DIR


def main(at: str):
    path = Path(at)
    targets = list(l.strip() for l in open(DATA_DIR / 'seed.txt', 'r').readlines())
    mypyind_caller.find(targets=targets, at=path)


if __name__ == '__main__':
    try:
        target = sys.argv[1]
    except IndexError:
        raise Exception("Please provide a target file path.")
    main(at=target)
