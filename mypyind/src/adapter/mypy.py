import io
import logging

from mypy.main import main
from mypyind.src.configs import INI_PATH

logger = logging.getLogger(__name__)
MYPY_REQUIRED_OPTIONS = [
    "--cache-dir=/dev/null",  # disable caching
    "--namespace-packages",
    f"--config-file={INI_PATH}",  # use custom config file
    "--show-traceback",
]


def call_mypy(target_path: str, options: None | list[str] = None) -> None:
    if options is None:
        options = []
    logger.info("Call mypy...")
    main(
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        args=[target_path] + MYPY_REQUIRED_OPTIONS + options,
        clean_exit=True,
    )
