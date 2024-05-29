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
    parser = pb.TransferParser(
        description="Create package for single cloud-based file-transfer."
    )
    parser.add_carrierid()
    parser.add_payload()
    parser.add_log()
    parser.add_md5()
    parser.add_dest()

    return parser.parse_args()


def main():
    args = parse_args()

    base_dir = pb.create_package_dir(args.dest, args.carrierid)
    pb.move_metadata_file(args.log, base_dir)
    pb.create_bag_in_objects(args.payload, base_dir, args.md5, "rclone")
    pb.validate_objects_bag(base_dir)


if __name__ == "__main__":
    main()
