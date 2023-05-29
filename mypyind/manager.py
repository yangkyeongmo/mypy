from __future__ import annotations

import abc
import json
import os

from mypyind.constants import (
    FULLNAMES_DEBUG_PATH,
    FULLNAMES_PATH,
    MAIN_PATH,
    MYPYIND_REQUIRED_OPTIONS, DATA_DIR,
)


class AbstractMypyindManager(abc.ABC):
    def __init__(self, mypy_caller, debug: bool = False, include_test: bool = False):
        self._level = 0
        self._mypy_caller = mypy_caller
        self._debug = debug
        self._include_test = include_test

    def find(self, targets: list[str], at: str) -> None:
        self._mypy_caller.call(at, MYPYIND_REQUIRED_OPTIONS)
        while self._is_updated():
            self._level += 1
            self._update_fullnames()
            self._mypy_caller.call(at, MYPYIND_REQUIRED_OPTIONS)
        self._finish()

    def _call_mypy(self, at: str, options: list[str]) -> None:
        print(f'{self._level=}')
        cmd = f'python {MAIN_PATH} {at} {" ".join(options)}'
        os.system(cmd)

    @abc.abstractmethod
    def _is_updated(self):
        ...

    @abc.abstractmethod
    def _update_fullnames(self):
        ...

    def store_fullname_if_found(
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

    @abc.abstractmethod
    def _finish(self):
        ...


class FilebasedMypyindManager(AbstractMypyindManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._found = set(l.strip() for l in open(FULLNAMES_PATH, 'r').readlines())

    def _is_updated(self):
        current_found = set(l.strip() for l in open(FULLNAMES_PATH, 'r').readlines())
        return self._found != current_found

    def _update_fullnames(self):
        fullnames = set(l.strip() for l in open(FULLNAMES_PATH, 'r').readlines())
        with open(FULLNAMES_PATH, 'w') as f:
            f.writelines(sorted(list(fullnames)))
        self._found = fullnames

    def _is_target(self, target: str, from_: str):
        if not self._include_test and 'test' in from_:
            return False
        return target in self._found

    def _store_target(self, target: str, from_: str):
        with open(FULLNAMES_PATH, 'a') as f:
            f.write(from_ + '\n')
        if self._debug:
            with open(FULLNAMES_DEBUG_PATH, 'a') as f:
                f.write(f'{target} is called from {from_} at {self._level} level.\n')

    def _finish(self):
        fullnames = set(open(FULLNAMES_PATH, 'r').readlines())
        with open(FULLNAMES_PATH, 'w') as f:
            f.writelines(sorted(list(fullnames)))


class MemorybasedMypyindManager(AbstractMypyindManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        seeds = list(l.strip() for l in open(DATA_DIR / 'seed.txt', 'r').readlines())
        self._found = {t: {'level': -1, 'from': []} for t in seeds}  # keys represent found fullnames.
        self._new_found = dict()  # stores fullnames found in the current level.

    def _is_updated(self):
        print(self._found, self._new_found)
        return any(new_key not in self._found for new_key in self._new_found)

    def _update_fullnames(self):
        for new_key, new_value in self._new_found.items():
            if new_key in self._found:
                self._found[new_key]['from'].extend(new_value['from'])
            else:
                self._found[new_key] = new_value
            self._found[new_key]['from'] = list(set(self._found[new_key]['from']))

    def _is_target(self, target: str, from_: str):
        if not self._include_test and 'test' in from_:
            return False
        return target in self._found

    def _store_target(self, target: str, from_: str):
        print(target, from_)
        if target in self._new_found:
            self._new_found[target]['from'].append(from_)
        else:
            self._new_found[target] = {'level': self._level, 'from': [from_]}
        if from_ not in self._new_found:
            self._new_found[from_] = {'level': self._level + 1, 'from': []}

    def _finish(self):
        json.dump(self._found, open(DATA_DIR / 'fullnames_2.json', 'w'))
