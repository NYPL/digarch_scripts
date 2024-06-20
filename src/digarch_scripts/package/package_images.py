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
    """
    Parse command line arguments.
    :return: The parsed arguments.
    """
    parser = pb.TransferParser(
        description="Create packages for all disk imaging files for a single acquisition."
    )
    parser.add_acqid()
    parser.add_source()
    parser.add_dest()

    return parser.parse_args()


def find_carriers_image_files(
    acq_id: str, source_dir: Path, log_dir: Path = None, stream_dir: Path = None
) -> dict:
    """
    Find all carrier files for a given acquisition ID in the source directory.
    """

    # Optional args kept in case process changes back to multiple source folders
    if not log_dir:
        log_dir = source_dir
    if not stream_dir:
        stream_dir = source_dir

    carrier_files = pb.find_category_of_carrier_files(
        {}, acq_id, source_dir, IMG_EXTS, "images"
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
    """
    Validate that all required files are present for each carrier.
    """
    result = True
    for carrier_name in carrier_files:
        carrier = carrier_files[carrier_name]

        missing = []
        for key in ["images", "logs"]:
            if not key in carrier.keys():
                missing.append(key)

        if missing:
            LOGGER.warning(
                f'The following required categories of files were not found for {carrier_name}: {", ".join(missing)} '
            )
            result = False

        if "images" in carrier:
            if len(carrier["images"]) > 1:
                two_sided = True
                for image in carrier["images"]:
                    if not re.match(r"s\d\.001", image.name[-6:]):
                        two_sided = False
                if not two_sided:
                    LOGGER.warning(
                        f'Multiple image files found for {carrier_name}. Only 1 allowed. If carrier has 2 disk formats, file names must end with s0.001 or s1.001: {carrier["images"]}'
                    )
                    result = False

            for image_file in carrier["images"]:
                if image_file.stat().st_size == 0:
                    LOGGER.warning(f"The following image file is 0-bytes: {image_file}")
                    result = False

        if "streams" in carrier:
            if not len(carrier["streams"]) == 1:
                LOGGER.warning(
                    f'Multiple folders of streams found for {carrier_name}. Only 1 allowed: {carrier["streams"]}'
                )
                result = False
            if not list(carrier["streams"][0].iterdir()):
                LOGGER.warning(
                    f'Streams folder for {carrier_name} appears to be empty: {carrier["streams"][0]}'
                )
                result = False
            for child in carrier["streams"][0].iterdir():
                if child.is_dir():
                    LOGGER.warning(
                        f"Folders found with streams folder for {carrier_name}. None allowed: {child}"
                    )
                    result = False

    return result


def package_carriers_image_files(carrier_files: dict, acq_dir: Path) -> None:
    """
    Create packages for all carriers in the carrier_files dictionary.
    """
    for carrier, files in carrier_files.items():
        try:
            base_dir = pb.create_package_dir(acq_dir, carrier)
            pb.move_metadata_files(files["logs"], base_dir)
            pb.create_bag_in_images(files["images"], base_dir)
            pb.create_bag_in_streams(files["streams"][0], base_dir)
        except Exception as e:
            LOGGER.error(
                f"Packaging incomplete for {carrier}. Address warnings manually.\n{e}"
            )
        finally:
            pb.validate_images_bag(base_dir)
            pb.validate_streams_bag(base_dir)

    return None


def main():
    """
    Main function for packaging images.
    """
    args = parse_args()

    carrier_files = find_carriers_image_files(args.acqid, args.source)

    if validate_carriers_image_files(carrier_files):
        package_carriers_image_files(carrier_files, args.dest)
    else:
        LOGGER.error(
            "1 or more errors with files for a carrier. Please address warnings and re-run"
        )


if __name__ == "__main__":
    main()
