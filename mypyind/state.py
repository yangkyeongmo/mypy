class MypyindState:
    def __init__(self):
        self._level = 0
        self._found = set()

    @property
    def level(self) -> int:
        return self._level

    def increase_level(self):
        self._level += 1

    @property
    def found(self) -> set[str]:
        return self._found

    def add_found(self, fullname: str):
        self._found.add(fullname)

    def is_in_found(self, fullname: str) -> bool:
        return fullname in self._found


mypyind_state = MypyindState()
