class MypyindState:
    def __init__(self, seed: str = ''):
        self._level: int = 0
        self._found: dict[str, dict[str, int | list[str]]] = {seed: {'level': -1, 'from': []}}

    @property
    def level(self) -> int:
        return self._level

    def increase_level(self):
        self._level += 1

    def add_found(self, fullname: str, from_: str):
        if fullname in self._found:
            self._found[fullname]['from'].append(from_)
        else:
            self._found[fullname] = {'level': self._level, 'from': [from_]}

    def is_in_found(self, fullname: str) -> bool:
        return fullname in self._found


mypyind_state = MypyindState()
