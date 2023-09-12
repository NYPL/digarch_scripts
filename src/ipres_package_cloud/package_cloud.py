import argparse
import logging
from pathlib import Path
import re

LOGGER = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    def extant_path(p: str) -> Path:
        path = Path(p)
        if not path.exists():
            raise argparse.ArgumentTypeError(f"{path} does not exist")
        return path

    def digital_carrier_label(id: str) -> Path:
        pattern = r'ACQ_\d{4}_\d{6}'
        if not re.match(r'ACQ_\d{4}_\d{6}', id):
            raise argparse.ArgumentTypeError(
                f'{id} does not match the expected {type} pattern, {pattern}'
            )
        return id


    parser = argparse.ArgumentParser(
        description='test'
    )
    parser.add_argument(
        '--payload',
        required=True,
        type=extant_path
    )
    parser.add_argument(
        '--log',
        required=True,
        type=extant_path
    )
    parser.add_argument(
        '--md5',
        required=True,
        type=extant_path
    )
    parser.add_argument(
        '--dest',
        required=True,
        type=extant_path
    )
    parser.add_argument(
        '--id',
        required=True,
        type=digital_carrier_label
    )

    return parser.parse_args()

def create_base_dir(dest: Path, id: str) -> Path:
    print(id)
    acq_id = id.rsplit("_", 1)[0]
    package_base = dest / acq_id / id
    if package_base.exists():
        raise FileExistsError(f'{package_base} already exists. Make sure you are using the correct ID')

    try:
        package_base.mkdir(parents = True)
    except PermissionError:
        raise PermissionError(f'{dest} is not writable')
    return package_base

def move_metadata_file():
    return None

def move_payload():
    return None

def create_bag_in_payload():
    return None

def validate_bag_in_payload():
    return None

def main():
    args = parse_args()
    LOGGER.info("I do not package anything yet")

if __name__ == "__main__":
    main()