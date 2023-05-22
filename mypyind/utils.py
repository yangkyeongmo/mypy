from pathlib import Path

DIR = Path(__file__).parent
FULLNAMES_PATH = Path(DIR, 'fullnames.txt')
FULLNAMES_DEBUG_PATH = Path(DIR, 'fullnames_debug.txt')


def get_fullname_file(mode='r'):
    return open(FULLNAMES_PATH, mode)


def get_fullname_debug_file(mode='r'):
    return open(FULLNAMES_DEBUG_PATH, mode)


def store_target_fullname(fullname, object_type, member, parent_fullname):
    found_fullnames = set(
        line.rstrip('\n')
        for line in get_fullname_file().readlines()
    )
    if fullname is None and object_type is not None:
        _name = None
        if hasattr(object_type, 'type'):
            _name = object_type.type.fullname
        if _name is not None:
            fullname = _name + '.' + member

    if (
        parent_fullname is not None
        and str(fullname) in found_fullnames
    ):
        with get_fullname_file('a') as f:
            f.write(parent_fullname + '\n')
        with get_fullname_debug_file('a') as f:
            f.write(f'{fullname} is called from {parent_fullname}\n')
