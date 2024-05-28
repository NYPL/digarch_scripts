import argparse
import logging
import re
from pathlib import Path

import digarch_scripts.package.package_base as pb

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

IMG_EXTS = [".001", ".img", ".dsk"]
LOG_EXTS = [".log"]
STREAM_EXTS = [""]


def parse_args() -> argparse.Namespace:
    def extant_path(p: str) -> Path:
        path = Path(p)
        if not path.exists():
            raise argparse.ArgumentTypeError(f"{path} does not exist")
        return path

    def acq_id(id: str) -> Path:
        pattern = r"ACQ_\d{4}"
        old_pattern = r"M\d{4-6}"
        if not re.match(pattern, id):
            if not re.match(old_pattern, id):
                raise argparse.ArgumentTypeError(
                    f"{id} does not match the expected {type} pattern, {pattern}"
                )
        return id

    parser = argparse.ArgumentParser(description="test")
    parser.add_argument(
        "--images_folder",
        required=True,
        type=extant_path,
        help="Path to working images folder",
    )
    parser.add_argument(
        "--dest", required=True, type=extant_path, help="Path to packaged images folder"
    )
    parser.add_argument("--acqid", required=True, type=acq_id, help="ACQ_####")
    parser.add_argument(
        "--logs_folder",
        required=False,
        type=extant_path,
        help="Path to working logs folder",
    )
    parser.add_argument(
        "--streams_folder",
        required=False,
        type=extant_path,
        help="Path to working streams folder",
    )

    return parser.parse_args()


def find_category_of_carrier_files(
    carrier_files: dict, acq_id: str, source_dir: Path, exts: list, category: str
) -> dict:
    for file in source_dir.iterdir():
        if not file.suffix in exts:
            continue
        carrier_id_match = re.search(rf"{acq_id}_\d\d\d\d\d\d+", file.name)
        if not carrier_id_match:
            continue
        carrier_id = carrier_id_match.group(0)

        if not carrier_id in carrier_files:
            carrier_files[carrier_id] = {category: []}
        elif not category in carrier_files[carrier_id]:
            carrier_files[carrier_id][category] = []

        carrier_files[carrier_id][category].append(file)

    return carrier_files


def find_carrier_files(
    acq_id: str, images_dir: Path, log_dir: Path, stream_dir: Path
) -> dict:
    carrier_files = find_category_of_carrier_files(
        {}, acq_id, images_dir, IMG_EXTS, "images"
    )
    carrier_files = find_category_of_carrier_files(
        carrier_files, acq_id, log_dir, LOG_EXTS, "logs"
    )
    carrier_files = find_category_of_carrier_files(
        carrier_files, acq_id, stream_dir, STREAM_EXTS, "streams"
    )

    if not carrier_files:
        raise Warning(f"No files found with the acquisition ID {acq_id} in filename")

    return carrier_files


def validate_carrier_files(carrier_files):
    for carrier_name in carrier_files:
        carrier = carrier_files[carrier_name]
        missing = []
        for key in ['images', 'logs', 'streams']:
            if not key in carrier.keys():
                missing.append(key)

        if missing:
            LOGGER.warning(f'The following categories of files were not found for {carrier_name}: {", ".join(missing)} ')

        if 'images' in carrier:
            for image_file in carrier['images']:
                if image_file.stat().st_size == 0:
                    LOGGER.warning(f'The following image file is 0-bytes: {image_file}')

    return

def package_carriers(carrier_files: dict, acq_dir: Path) -> None:
    for carrier, files in carrier_files.items():
        base_dir = pb.create_package_dir(acq_dir, carrier)
        pb.move_metadata_files(files["logs"], base_dir)
        pb.move_diskimage_files(files["images"], base_dir)
        pb.move_stream_files(files["streams"], base_dir)


def main():
    args = parse_args()

    carrier_files = find_carrier_files(
        args.acqid, args.images_folder, args.logs_folder, args.streams_folder
    )
    if validate_carrier_files(carrier_files):
        package_carriers(carrier_files, args.dest)
    else:
        LOGGER.error("1 or more errors with files for a carrier. Please address warnings and re-run")


if __name__ == "__main__":
    main()
