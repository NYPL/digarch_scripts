import argparse
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

LOGGER = logging.getLogger(__name__)

def _configure_logging(log_folder: Path):
    log_fn = datetime.now().strftime("lint_%Y_%m_%d_%H_%M.log")
    log_fpath = log_folder / log_fn
    if not log_fpath.is_file():
        log_fpath.touch()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(levelname)8s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=log_fpath,
        encoding="utf-8",
    )

def parse_args() -> argparse.Namespace:
    """Validate and return command-line args"""

    def extant_dir(p):
        path = Path(p)
        if not path.is_dir():
            raise argparse.ArgumentTypeError(
                f'{path} does not exist'
            )
        return path

    def list_of_paths(p):
        path = extant_dir(p)
        child_dirs = []
        for child in path.iterdir():
            if child.is_dir():
                child_dirs.append(child)
        return child_dirs

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--package',
        type=extant_dir,
        nargs='+',
        dest='packages',
        action='extend'
    )
    parser.add_argument(
        '--directory',
        type=list_of_paths,
        dest='packages',
        action='extend'
    )
    parser.add_argument(
        '--log_folder',
        help='''Optional. Designate where to save the log file,
        or it will be saved in current directory''',
        default='.'
    )


    return parser.parse_args()

def main():
    _configure_logging(args.log_folder)

    valid = []
    invalid = []
    needs_review = []

    counter = 0

if __name__ == "__main__":
    main()