from pathlib import Path

DIR = Path(__file__).parent
FULLNAMES_PATH = Path(DIR, 'fullnames.txt')
FULLNAMES_DEBUG_PATH = Path(DIR, 'fullnames_debug.txt')
INI_PATH = Path(DIR, 'mypyind.ini')

MYPY_DIR = Path(DIR.parent, 'mypy')
MAIN_PATH = Path(MYPY_DIR, '__main__.py')

MYPYIND_DIR = Path(__file__).parent

MYPYIND_REQUIRED_OPTIONS = (
    '--cache-dir=/dev/null',  # disable caching
    '--namespace-packages',
    f'--config-file={INI_PATH}',  # use custom config file
)
