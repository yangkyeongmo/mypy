import abc
import logging
from dataclasses import dataclass

from mypyind.src.constants import FULLNAMES_PATH, FULLNAMES_DEBUG_PATH, DATA_DIR
from mypyind.src.state import MypyindState, mypyind_state

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WriterConfig:
    path: str


class AbstractMypyindWriter(abc.ABC):
    def __init__(self, state: MypyindState, config: WriterConfig = None, debug: bool = False, include_test: bool = False):
        self._state = state
        self._config = config
        self._debug = debug
        self._include_test = include_test

    def render_fullname(self, fullname: None | str, member: str, object_type, parent_f):
        if fullname is None and object_type is not None:
            # render fullname from object_type if object_type.type.fullname exists
            _name = None
            if hasattr(object_type, 'type'):
                _name = object_type.type.fullname
            if _name is not None:
                fullname = _name + '.' + member
        if parent_f is None or fullname is None:
            return
        return fullname

    def add_if_found(self, target: str, from_: str):
        if self._is_target(target=target, from_=from_):
            self._add_target(target=target, from_=from_)

    @abc.abstractmethod
    def _is_target(self, target: str, from_: str):
        """Determine if we're looking for this target."""
        ...

    @abc.abstractmethod
    def _add_target(self, target: str, from_: str):
        """Memo this target as found."""
        ...

    @abc.abstractmethod
    def dump_found(self):
        """Dump found targets to a file."""
        ...


class FilebasedMypyindWriter(AbstractMypyindWriter):
    def _is_target(self, target: str, from_: str):
        if not self._include_test and 'test' in from_:
            return False
        return self._state.is_in_found(target)

    def _add_target(self, target: str, from_: str):
        self._state.add_found(target, from_)

    def dump_found(self):
        with open(self._config.path, 'a') as f:
            for found in self._state.found:
                f.write(found + '\n')
            if self._debug:
                for found, info in self._state.found.items():
                    for item in info:
                        f.write(f'{found} is called from {item.from_} at {item.level} level.\n')


class MemorybasedMypyindWriter(AbstractMypyindWriter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        seeds = list(l.strip() for l in open(DATA_DIR / 'seed.txt', 'r').readlines())
        self._found = {t: {'level': -1, 'from': []} for t in seeds}  # keys represent found fullnames.
        self._new_found = dict()  # stores fullnames found in the current level.

    def _is_target(self, target: str, from_: str):
        if not self._include_test and 'test' in from_:
            return False
        return self._state.is_in_found(target)

    def _add_target(self, target: str, from_: str):
        if target in self._new_found:
            self._new_found[target]['from'].append(from_)
        else:
            self._new_found[target] = {'level': self._state.level, 'from': [from_]}
        if from_ not in self._new_found:
            self._new_found[from_] = {'level': self._state.level + 1, 'from': []}

    def dump_found(self):
        ...


mypyind_writer = FilebasedMypyindWriter(state=mypyind_state, debug=True)
