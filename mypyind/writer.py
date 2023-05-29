import abc
import logging

from mypyind.constants import FULLNAMES_PATH, FULLNAMES_DEBUG_PATH, DATA_DIR
from mypyind.state import MypyindState, mypyind_state

logger = logging.getLogger(__name__)


class AbstractMypyindWriter(abc.ABC):
    def __init__(self, state: MypyindState, debug: bool = False, include_test: bool = False):
        self._state = state
        self._debug = debug
        self._include_test = include_test

    def write_if_found(
        self,
        fullname: None | str,
        member: str,
        object_type,
        parent_f,
    ):
        if fullname is None and object_type is not None:
            # render fullname from object_type if object_type.type.fullname exists
            _name = None
            if hasattr(object_type, 'type'):
                _name = object_type.type.fullname
            if _name is not None:
                fullname = _name + '.' + member
        if parent_f is None or fullname is None:
            return
        if self._is_target(target=fullname, from_=parent_f.fullname):
            self._store_target(target=fullname, from_=parent_f.fullname)

    @abc.abstractmethod
    def _is_target(self, target: str, from_: str):
        ...

    @abc.abstractmethod
    def _store_target(self, target: str, from_: str):
        ...


class FilebasedMypyindWriter(AbstractMypyindWriter):
    def _is_target(self, target: str, from_: str):
        if not self._include_test and 'test' in from_:
            return False
        return self._state.is_in_found(target)

    def _store_target(self, target: str, from_: str):
        with open(FULLNAMES_PATH, 'a') as f:
            f.write(from_ + '\n')
        if self._debug:
            debug_str = f'{target} is called from {from_} at {self._state.level} level.'
            logger.debug(debug_str)
            with open(FULLNAMES_DEBUG_PATH, 'a') as f:
                f.write(debug_str + '\n')


class MemorybasedMypyindWriter(AbstractMypyindWriter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        seeds = list(l.strip() for l in open(DATA_DIR / 'seed.txt', 'r').readlines())
        self._found = {t: {'level': -1, 'from': []} for t in seeds}  # keys represent found fullnames.
        self._new_found = dict()  # stores fullnames found in the current level.

    def _is_target(self, target: str, from_: str):
        if not self._include_test and 'test' in from_:
            return False
        return target in self._found

    def _store_target(self, target: str, from_: str):
        if target in self._new_found:
            self._new_found[target]['from'].append(from_)
        else:
            self._new_found[target] = {'level': self._state.level, 'from': [from_]}
        if from_ not in self._new_found:
            self._new_found[from_] = {'level': self._state.level + 1, 'from': []}


mypyind_writer = FilebasedMypyindWriter(state=mypyind_state, debug=True)
