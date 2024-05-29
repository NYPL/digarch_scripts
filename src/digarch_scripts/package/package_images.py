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
    parser = pb.TransferParser(
        description="Create packages for all disk imaging files for a single acquisition."
    )
    parser.add_acqid()
    parser.add_images_folder()
    parser.add_logs_folder()
    parser.add_streams_folder()
    parser.add_dest()

    return parser.parse_args()


def find_carriers_image_files(
    acq_id: str, images_dir: Path, log_dir: Path, stream_dir: Path
) -> dict:
    carrier_files = pb.find_category_of_carrier_files(
        {}, acq_id, images_dir, IMG_EXTS, "images"
    )
    carrier_files = pb.find_category_of_carrier_files(
        carrier_files, acq_id, log_dir, LOG_EXTS, "logs"
    )
    carrier_files = pb.find_category_of_carrier_files(
        carrier_files, acq_id, stream_dir, STREAM_EXTS, "streams"
    )

    if not carrier_files:
        raise Warning(f"No files found with the acquisition ID {acq_id} in filename")

    return carrier_files


def validate_carriers_image_files(carrier_files: dict) -> bool:
    result = True
    for carrier_name in carrier_files:
        carrier = carrier_files[carrier_name]

        missing = []
        for key in ["images", "logs", "streams"]:
            if not key in carrier.keys():
                missing.append(key)

        if missing:
            LOGGER.warning(
                f'The following categories of files were not found for {carrier_name}: {", ".join(missing)} '
            )
            result = False

        if "images" in carrier:
            for image_file in carrier["images"]:
                if image_file.stat().st_size == 0:
                    LOGGER.warning(f"The following image file is 0-bytes: {image_file}")
                    result = False

        if "streams" in carrier:
            if not len(carrier["streams"]) == 1:
                LOGGER.warning(
                    f'Multiple folder of stream folders found for {carrier_name}. Only 1 allowed: {carrier["streams"]}'
                )
                result = False

    return result


def package_carriers_image_files(carrier_files: dict, acq_dir: Path) -> None:
    for carrier, files in carrier_files.items():
        try:
            base_dir = pb.create_package_dir(acq_dir, carrier)
            pb.move_metadata_files(files["logs"], base_dir)
            pb.create_bag_in_images(files["images"], base_dir)
            pb.create_bag_in_streams(files["streams"][0], base_dir)
        except:
            LOGGER.error(
                f"Packaging incomplete for {carrier}. Address warnings manually."
            )
        finally:
            pb.validate_images_bag(base_dir)
            pb.validate_streams_bag(base_dir)

    return None


def main():
    args = parse_args()

    carrier_files = find_carriers_image_files(
        args.acqid, args.images_folder, args.logs_folder, args.streams_folder
    )

    if validate_carriers_image_files(carrier_files):
        package_carriers_image_files(carrier_files, args.dest)
    else:
        LOGGER.error(
            "1 or more errors with files for a carrier. Please address warnings and re-run"
        )


if __name__ == "__main__":
    main()
