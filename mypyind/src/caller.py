import abc
import json
import logging
import sys

from mypy.main import main
from mypyind.src.constants import MYPYIND_REQUIRED_OPTIONS, FULLNAMES_PATH, DATA_DIR
from mypyind.src.state import MypyindState, mypyind_state

logger = logging.getLogger(__name__)


class AbstractMypyindCaller(abc.ABC):
    def __init__(self, state: MypyindState):
        self._state = state

    def find(self, targets: list[str], at: str) -> None:
        logger.info('Start finding...')
        self._update_found()
        self._call_mypy(at, MYPYIND_REQUIRED_OPTIONS)
        while self._is_updated():
            logger.info('Found new targets.')
            self._state.increase_level()
            self._update_found()
            self._call_mypy(at, MYPYIND_REQUIRED_OPTIONS)
        logger.info('Finish finding...')
        self._finish()

    def _call_mypy(self, at: str, options: list[str]) -> None:
        logger.info('Call mypy...')
        main(None, sys.stdout, sys.stderr, [str(at)] + list(options), clean_exit=True)

    @abc.abstractmethod
    def _is_updated(self):
        ...

    @abc.abstractmethod
    def _update_found(self):
        ...

    @abc.abstractmethod
    def _finish(self):
        ...


class FilebasedMypyindCaller(AbstractMypyindCaller):
    def _is_updated(self):
        current_found = set(l.strip() for l in open(FULLNAMES_PATH, 'r').readlines())
        logger.debug((self._state._found.keys(), current_found))
        return any(not self._state.is_in_found(l) for l in current_found)

    def _update_found(self):
        fullnames = set(open(FULLNAMES_PATH, 'r').readlines())
        with open(FULLNAMES_PATH, 'w') as f:
            f.writelines(sorted(list(fullnames)))
        for l in fullnames:
            self._state.add_found(l.strip(), "")

    def _finish(self):
        fullnames = set(open(FULLNAMES_PATH, 'r').readlines())
        with open(FULLNAMES_PATH, 'w') as f:
            f.writelines(sorted(list(fullnames)))


class MemorybasedMypyindCaller(AbstractMypyindCaller):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        seeds = list(l.strip() for l in open(DATA_DIR / 'seed.txt', 'r').readlines())
        self._found = {t: {'level': -1, 'from': []} for t in seeds}  # keys represent found fullnames.
        self._new_found = dict()  # stores fullnames found in the current level.

    def _is_updated(self):
        print(self._found, self._new_found)
        return any(new_key not in self._found for new_key in self._new_found)

    def _update_found(self):
        for new_key, new_value in self._new_found.items():
            if new_key in self._found:
                self._found[new_key]['from'].extend(new_value['from'])
            else:
                self._found[new_key] = new_value
            self._found[new_key]['from'] = list(set(self._found[new_key]['from']))

    def _finish(self):
        json.dump(self._found, open(DATA_DIR / 'fullnames_2.json', 'w'))


mypyind_caller = FilebasedMypyindCaller(state=mypyind_state)
