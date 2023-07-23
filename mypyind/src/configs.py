from pathlib import Path

# Directory paths
DIR = Path(__file__).parent
DATA_DIR = Path(DIR, "../data")

# Data file paths
TXT_PATH = Path(DATA_DIR, "found.txt")
JSON_PATH = Path(DATA_DIR, "found.json")
DEBUG_LOG_PATH = Path(DATA_DIR, "found.log")

# Mypy related path
MYPY_DIR = Path(DIR.parent, "mypy")
MAIN_PATH = Path(MYPY_DIR, "../__main__.py")

# Mypyind related path
MYPYIND_DIR = Path(__file__).parent
MYPYIND_PATH = Path(__file__).parent.parent / "mypyind"
INI_PATH = Path(DIR, "../mypyind.ini")
