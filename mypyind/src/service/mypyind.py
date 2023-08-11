import logging

from mypyind.src.adapter.mypy import call_mypy
from mypyind.src.adapter.writer import write_state_to_json_file, write_state_to_text_file

# type check
from mypyind.src.state import MypyindState

logger = logging.getLogger(__name__)


class Mypyind:
    def __init__(self, state: MypyindState):
        self._state = state
        self._current_found = set(self._state.list_all_found())

    def execute(self, target_path: str) -> None:
        self._state.increase_level()
        try:
            call_mypy(target_path)
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except SystemExit:
            # Mypy does sys.exit(2) when it finds errors. Bypass this for iteration.
            pass
        write_state_to_json_file(self._state)
        write_state_to_text_file(self._state)

        if set(self._state.list_all_found()) != self._current_found:
            self._current_found = set(self._state.list_all_found())
            self.execute(target_path)
        else:
            logger.info("Finish finding...")
