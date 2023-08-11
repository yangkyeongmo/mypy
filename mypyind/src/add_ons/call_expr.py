from datetime import datetime

from mypyind.src.adapter.writer import write_log_to_log_file
from mypyind.src.configs import DEBUG_LOG_PATH
from mypyind.src.state import global_mypyind_state

# type check
from mypyind.src.state import MypyindState


class CallExprAddOn:
    """Add-on for mypyind, added on mypy's call expr function."""

    def __init__(self, state: MypyindState, include_test: bool = False):
        self._state = state
        self._include_test = include_test

    def render_fullname(
        self, fullname: None | str, member: str, object_type, parent_f
    ) -> str | None:
        if fullname is None and object_type is not None:
            # render fullname from object_type if object_type.type.fullname exists
            _name = None
            if hasattr(object_type, "type"):
                _name = object_type.type.fullname
            if _name is not None:
                fullname = _name + "." + member
        if parent_f is None or fullname is None:
            return
        return fullname

    def add_if_found(self, target: str, from_: str):
        if (not self._include_test and "test" in from_) or not self._state.is_in_found(target):
            return
        self._state.add_found(target, from_)
        write_log_to_log_file(log=f"[{self._state.level}] [{target}] is called from [{from_}]")


call_expr_add_on = CallExprAddOn(state=global_mypyind_state)
