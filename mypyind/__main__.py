import sys

from mypyind.src.view.command import run_mypyind

if __name__ == "__main__":
    try:
        target_path = sys.argv[1]
    except IndexError:
        raise Exception("Please provide a target file path.")
    run_mypyind(target_path=target_path)
