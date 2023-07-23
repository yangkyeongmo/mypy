import logging
from dataclasses import dataclass

from mypyind.src.configs import DATA_DIR

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FoundItem:
    level: int
    from_: str


class MypyindState:
    def __init__(self, seed: str = ""):
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

    def add_found(self, fullname: str, from_: str | None):
        logger.debug(f"Adding {fullname} from {from_} at level {self._level}.")
        if fullname not in self._found:
            self._found[fullname] = []
        self._found[fullname].append(FoundItem(level=self._level, from_=from_))
        if from_ is not None and from_ not in self._found:
            self._found[from_] = []

    def is_in_found(self, fullname: str) -> bool:
        return fullname in self._found

    def list_all_found(self) -> list[str]:
        return list(self._found.keys())


_seed = open(DATA_DIR / "seed.txt", "r").read().strip()
mypyind_state = MypyindState(seed=_seed)
