from pathlib import Path

from mypyind.src.service.mypyind import Mypyind
from mypyind.src.state import global_mypyind_state


def run_mypyind(target_path: str):
    path = Path(target_path).absolute()
    mypyind = Mypyind(state=global_mypyind_state)
    mypyind.execute(target_path=str(path))
