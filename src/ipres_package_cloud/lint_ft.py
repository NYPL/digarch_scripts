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

def package_has_valid_name(package: Path) -> bool:
    """Top level folder name has to conform to ACQ_####_######"""
    folder_name = package.name
    match = re.fullmatch(r"ACQ_[0-9]{4}_[0-9]{6}", folder_name)

    if match:
        return True
    else:
        LOGGER.error(f"{folder_name} does not conform to ACQ_####_######")
        return False

def package_has_two_subfolders(package: Path) -> bool:
    """There must be two subfolders in the package"""
    pkg_folders = [ x for x in package.iterdir() if x.is_dir() ]
    if len(pkg_folders) == 2:
        return True
    else:
        LOGGER.error(f"{package} does not have exactly two subfolders")
        return False

def package_has_valid_subfolder_names(package: Path) -> bool:
    """Second level folders must be objects and metadata folder"""
    expected = set(["objects", "metadata"])
    found = set([x.name for x in package.iterdir()])

    if expected == found:
        return True
    else:
        LOGGER.error(
            f"{package.name} subfolders should have objects and metadata, found {found}"
        )
        return False

def metadata_folder_is_flat(package: Path) -> bool:
    """The metadata folder should not have folder structure"""
    metadata_path = package / "metadata"
    md_dir_ls = [x for x in metadata_path.iterdir() if x.is_dir()]
    if md_dir_ls:
        LOGGER.error(f"{package.name} has unexpected directory: {md_dir_ls}")
        return False
    else:
        return True

def metadata_folder_has_files(package: Path) -> bool:
    """The metadata folder should have one or more file"""
    metadata_path = package / "metadata"
    md_files_ls = [ x for x in metadata_path.rglob("*") if x.is_file() ]
    if md_files_ls:
        return True
    else:
        LOGGER.error(f"{package.name} metadata folder does not have any files")
        return False

def main():
    args = parse_args()
    _configure_logging(args.log_folder)

    valid = []
    invalid = []
    needs_review = []

    counter = 0

if __name__ == "__main__":
    main()