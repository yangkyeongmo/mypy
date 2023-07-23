import json
import logging
import sys

from mypy.main import main
from mypyind.src.configs import TXT_PATH, JSON_PATH, INI_PATH
from mypyind.src.state import MypyindState

logger = logging.getLogger(__name__)

MYPYIND_REQUIRED_OPTIONS = (
    "--cache-dir=/dev/null",  # disable caching
    "--namespace-packages",
    f"--config-file={INI_PATH}",  # use custom config file
    "--show-traceback",
)


class MypyindCaller:
    def __init__(self, state: MypyindState):
        self._state = state
        self._current_found = set(self._state.list_all_found())

    def find(self, at: str) -> None:
        self._state.increase_level()
        logger.info(f"[Iteration {self._state.level}] Finding...")
        self._call_mypy(at, MYPYIND_REQUIRED_OPTIONS)
        self.dump()
        if set(self._state.list_all_found()) != self._current_found:
            self._current_found = set(self._state.list_all_found())
            self.find(at)
        else:
            logger.info("Finish finding...")

    def _call_mypy(self, at: str, options: list[str]) -> None:
        logger.info("Call mypy...")
        main(None, sys.stdout, sys.stderr, [str(at)] + list(options), clean_exit=True)

    def dump(self):
        self._dump_txt()
        self._dump_json()

    def _dump_txt(self):
        with open(TXT_PATH, "w") as f:
            f.writelines("\n".join(sorted(self._state.list_all_found())))

    def _dump_json(self):
        dump_data = dict()
        for found, info in self._state.found.items():
            dump_data[found] = {}
            for item in info:
                dump_data[found][item.from_] = min(
                    item.level, dump_data[found].get(item.from_, 100000)
                )
        with open(JSON_PATH, "w") as f:
            json.dump(dump_data, f, indent=4)
