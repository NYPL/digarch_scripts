import argparse
import logging
import re
from pathlib import Path

import digarch_scripts.package.package_base as pb

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def parse_args() -> argparse.Namespace:
    parser = pb.TransferParser(
        description="Create packages for all file transfer files for a single acquisition."
    )
    parser.add_carrierid()
    parser.add_payload()
    parser.add_log()
    parser.add_dest()

    return parser.parse_args()


def main():
    args = parse_args()

    base_dir = pb.create_package_dir(args.dest, args.carrierid)
    pb.create_bag_in_objects(args.payload, base_dir, args.log, "rsync")
    pb.validate_objects_bag(base_dir)
    pb.move_metadata_file(args.log, base_dir)


if __name__ == "__main__":
    main()
