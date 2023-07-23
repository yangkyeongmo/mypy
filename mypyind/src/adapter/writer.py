import json

from mypyind.src.configs import TXT_PATH, JSON_PATH

# type check
from mypyind.src.state import MypyindState


def write_state_to_text_file(state: MypyindState):
    with open(TXT_PATH, "w") as f:
        f.writelines("\n".join(sorted(state.list_all_found())))


def write_state_to_json_file(state: MypyindState):
    dump_data = dict()
    for found, info in state.found.items():
        dump_data[found] = {}
        for item in info:
            dump_data[found][item.from_] = min(
                item.level, dump_data[found].get(item.from_, 100000)
            )
    with open(JSON_PATH, "w") as f:
        json.dump(dump_data, f, indent=4)
