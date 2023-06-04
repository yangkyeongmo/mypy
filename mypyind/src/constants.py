from pathlib import Path

DIR = Path(__file__).parent
DATA_DIR = Path(DIR, "../data")
TXT_PATH = Path(DATA_DIR, "found.txt")
JSON_PATH = Path(DATA_DIR, "found.json")
DEBUG_LOG_PATH = Path(DATA_DIR, "found.log")

MYPY_DIR = Path(DIR.parent, "mypy")
MAIN_PATH = Path(MYPY_DIR, "../__main__.py")

MYPYIND_DIR = Path(__file__).parent
MYPYIND_PATH = Path(__file__).parent.parent / "mypyind"

INI_PATH = Path(DIR, "../mypyind.ini")
MYPYIND_REQUIRED_OPTIONS = (
    "--cache-dir=/dev/null",  # disable caching
    "--namespace-packages",
    f"--config-file={INI_PATH}",  # use custom config file
    "--show-traceback",
)
