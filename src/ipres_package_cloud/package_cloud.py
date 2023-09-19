import argparse
from datetime import date
import logging
import os
from pathlib import Path
import re

import bagit

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


def create_base_dir(dest: Path, id: str) -> Path:
    print(id)
    acq_id = id.rsplit("_", 1)[0]
    package_base = dest / acq_id / id
    if package_base.exists():
        raise FileExistsError(
            f"{package_base} already exists. Make sure you are using the correct ID"
        )

    try:
        package_base.mkdir(parents=True)
    except PermissionError:
        raise PermissionError(f"{dest} is not writable")
    return package_base


def move_metadata_file(md_path: Path, pkg_dir: Path) -> None:
    md_dir = pkg_dir / "metadata"
    if not md_dir.exists():
        md_dir.mkdir()

    new_md_path = md_dir / md_path.name
    if new_md_path.exists():
        raise FileExistsError(f"{new_md_path} already exists. Not moving.")

    md_path.rename(new_md_path)
    return None


def move_payload(payload_path: Path, pkg_dir: Path) -> None:
    return None


def create_bag_in_objects(md5_path: Path, pkg_dir: Path) -> None:
    # this needs to do a lot
    bag_dir = pkg_dir / "objects"
    # move md5 file to manifest-md5.txt
    new_md5_path = bag_dir / "manifest-md5.txt"
    if new_md5_path.exists():
        raise FileExistsError("some error message")
    md5_path.rename(new_md5_path)
    # update paths in md5 file, need to match old file path to path in data, and figure difference
    relative_path = "?"
    convert_to_bagit_manifest(new_md5_path, relative_path)
    # generate baginfo.txt and bagit.txt (copying code snippet from bagit)
    create_bag_tag_files(pkg_dir)
    return None


def convert_to_bagit_manifest(md5_path: Path, replace: str) -> None:
    with open(md5_path, "r") as f:
        manifest_data = f.readlines()

    # in test the replace string would be 'files'
    updated_manifest = [
        line.replace(f"  {replace}", "  data") for line in manifest_data
    ]

    with open(md5_path, "w"):
        f.writelines(manifest_data)
    return None


def create_bag_tag_files(pkg_dir):
    LOGGER.info("Creating bagit.txt")
    txt = """BagIt-Version: 0.97\nTag-File-Character-Encoding: UTF-8\n"""
    with open("bagit.txt", "w") as bagit_file:
        bagit_file.write(txt)

    LOGGER.info("Creating bag-info.txt")
    bag_info = {}
    bag_info["Bagging-Date"] = date.strftime(date.today(), "%Y-%m-%d")
    bag_info["Bag-Software-Agent"] = "package_cloud.py"
    total_bytes, total_files = get_oxum(pkg_dir / "data")
    bag_info["Payload-Oxum"] = f"{total_bytes}.{total_files}"
    bagit._make_tag_file("bag-info.txt", bag_info)


def get_oxum(payload_dir: Path) -> (int, int):    
    total_bytes = 0
    total_files = 0

    for payload_file in payload_dir.rglob('*'):
        if payload_file.is_file():
            total_files += 1
            total_bytes += os.stat(payload_file).st_size
            
    return total_bytes, total_files


def validate_bag_in_payload(pkg_dir: Path) -> None:
    bag_dir = pkg_dir / "objects"
    bag = bagit.Bag(str(bag_dir))
    try:
        bag.validate(completeness_only=True)
        LOGGER.info(f"{bag.path} is valid.")
    except bagit.BagValidationError:
        LOGGER.warn(f"{bag.path} is not valid. Check the bag manifest and oxum.")
    return None


def main():
    args = parse_args()

    base_dir = create_base_dir(args.dest, args.id)
    move_metadata_file(args.log, base_dir)
    move_payload(args.payload, base_dir)
    create_bag_in_objects(args.md5, base_dir)
    validate_bag_in_payload(base_dir)


if __name__ == "__main__":
    main()
