import sys
from pathlib import Path

from mypyind.src.caller import MypyindCaller
from mypyind.src.state import mypyind_state


def main(at: str):
    path = Path(at)
    mypyind_caller = MypyindCaller(state=mypyind_state, debug=True)
    mypyind_caller.find(at=path.name)


if __name__ == "__main__":
    try:
        target = sys.argv[1]
    except IndexError:
        raise Exception("Please provide a target file path.")
    main(at=target)
