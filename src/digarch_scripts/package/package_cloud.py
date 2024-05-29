import argparse
import logging
import os
import re
from datetime import date
from pathlib import Path

import bagit

import digarch_scripts.package.package_base as pb

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def parse_args() -> argparse.Namespace:
    def extant_path(p: str) -> Path:
        path = Path(p)
        if not path.exists():
            raise argparse.ArgumentTypeError(f"{path} does not exist")
        return path

    def digital_carrier_label(id: str) -> Path:
        pattern = r"ACQ_\d{4}_\d{6}"
        if not re.match(r"ACQ_\d{4}_\d{6}", id):
            raise argparse.ArgumentTypeError(
                f"{id} does not match the expected {type} pattern, {pattern}"
            )
        return id

    parser = argparse.ArgumentParser(description="test")
    parser.add_argument("--payload", required=True, type=extant_path)
    parser.add_argument("--log", required=True, type=extant_path)
    parser.add_argument("--md5", required=True, type=extant_path)
    parser.add_argument("--dest", required=True, type=extant_path)
    parser.add_argument("--id", required=True, type=digital_carrier_label)

    return parser.parse_args()


def main():
    args = parse_args()

    base_dir = pb.create_package_dir(args.dest, args.id)
    pb.move_metadata_file(args.log, base_dir)
    pb.create_bag_in_objects(args.payload, args.md5, base_dir)
    pb.validate_objects_bag(base_dir)


if __name__ == "__main__":
    main()
