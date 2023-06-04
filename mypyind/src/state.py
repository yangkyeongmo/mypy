from dataclasses import dataclass


@dataclass(frozen=True)
class FoundItem:
    level: int
    from_: str


class MypyindState:
    def __init__(self, seed: str = ''):
        self._level: int = 0
        self._found: dict[str, list[FoundItem]] = {seed: []}

    @property
    def level(self) -> int:
        return self._level

    @property
    def found(self) -> dict[str, list[FoundItem]]:
        return self._found

    def increase_level(self):
        self._level += 1

    def add_found(self, fullname: str, from_: str):
        if fullname not in self._found:
            self._found[fullname] = []
        self._found[fullname].append(FoundItem(level=self._level, from_=from_))
        if from_ not in self._found:
            self._found[from_] = []

    def is_in_found(self, fullname: str) -> bool:
        return fullname in self._found

    def list_all_found(self) -> list[str]:
        return list(self._found.keys())


mypyind_state = MypyindState()
