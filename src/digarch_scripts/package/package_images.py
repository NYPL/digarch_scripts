import argparse
import re
from pathlib import Path

import digarch_scripts.package.package_base as pb


def parse_args() -> argparse.Namespace:
    def extant_path(p: str) -> Path:
        path = Path(p)
        if not path.exists():
            raise argparse.ArgumentTypeError(f"{path} does not exist")
        return path

    def digital_carrier_label(id: str) -> Path:
        pattern = r"ACQ_\d{4}_\d{6}"
        old_pattern = r"M\d{4-6}_\d{4}"
        if not re.match(pattern, id):
            if not re.match(old_pattern, id):
                raise argparse.ArgumentTypeError(
                    f"{id} does not match the expected {type} pattern, {pattern}"
                )
        return id

    parser = argparse.ArgumentParser(description="test")
    parser.add_argument("--image", required=True, type=extant_path)
    parser.add_argument("--dest", required=True, type=extant_path)
    parser.add_argument("--id", required=True, type=digital_carrier_label)
    parser.add_argument("--log", required=False, nargs="+", type=extant_path)
    parser.add_argument("--streams", required=False, type=extant_path)
    parser.add_argument("--extracted", required=False, type=extant_path)

    return parser.parse_args()


def main():
    args = parse_args()

    base_dir = pb.create_base_dir(args.dest, args.id)
    pb.move_metadata_files(args.log, base_dir)
    pb.move_diskimage_file(args.image, base_dir)


if __name__ == "__main__":
    main()
