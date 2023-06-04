from typing import Optional

from mypy.nodes import FuncBase
from mypy.types import Type
from mypyind.src.constants import MYPYIND_DIR


def store_fullname_if_found(
    fullname: Optional[str],
    member: str,
    object_type: Optional[Type],
    parent_f: Optional[FuncBase],
):
    found_fullnames = set(
        line.rstrip('\n')
        for line in open(MYPYIND_DIR / "fullnames.txt", 'r').readlines()
    )
    if fullname is None and object_type is not None:
        # render fullname from object_type if object_type.type.fullname exists
        _name = None
        if hasattr(object_type, 'type'):
            _name = object_type.type.fullname
        if _name is not None:
            fullname = _name + '.' + member
    if _is_matching_fullname(found_fullnames, fullname, parent_f):
        _write_fullname(fullname, parent_f)


def _write_fullname(fullname, parent_f, debug=True):
    with open(MYPYIND_DIR / 'fullnames.txt', 'a') as f:
        f.write(parent_f.fullname)
        f.write('\n')
    if debug:
        with open(MYPYIND_DIR / 'fullnames_debug.txt', 'a') as f:
            f.write(f'{fullname} is called from {parent_f.fullname}')
            f.write('\n')


def _is_matching_fullname(found_fullnames, fullname, parent_f):
    return (
        str(fullname) in found_fullnames
        and parent_f is not None
        and 'test' not in parent_f.fullname
    )
