import argparse
import logging
import os
import re
from datetime import date
from pathlib import Path

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


def create_acq_dir(dest: Path, acq_id: str) -> Path:
    acq_dir = dest / acq_id
    if acq_dir.exists():
        LOGGER.info(f"Acquisition directory already exits: {acq_dir}")
        return acq_dir

    try:
        acq_dir.mkdir(parents=True)
    except PermissionError:
        raise PermissionError(f"{dest} is not writable")
    return acq_dir


def create_package_dir(dest: Path, id: str) -> Path:
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


def move_file(file_path: Path, pkg_dir: Path, dest: str) -> None:
    dest_dir = pkg_dir / dest
    if not dest_dir.exists():
        dest_dir.mkdir(parents=True)

    new_file_path = dest_dir / file_path.name
    if new_file_path.exists():
        raise FileExistsError(
            f"{new_file_path} already exists in {dest} folder. Not moving."
        )
    print(new_file_path)
    file_path.rename(new_file_path)
    return None


def move_files(file_paths: list[Path], pkg_dir: Path, dest: str) -> None:
    for file_path in file_paths:
        try:
            move_file(file_path, pkg_dir, dest)
        except FileExistsError as e:
            raise Warning(
                f"{e} One or more files may have already been moved to the {dest} folder"
            )
    return None


def move_metadata_file(md_path: Path, pkg_dir: Path) -> None:
    return move_file(md_path, pkg_dir, "metadata")


def move_metadata_files(md_paths: list[Path], pkg_dir: Path) -> None:
    return move_files(md_paths, pkg_dir, "metadata")


def move_data_files(data_paths: list[Path], pkg_dir: Path) -> None:
    return move_files(data_paths, pkg_dir, "data")


def move_and_bag_diskimage_files(image_paths: list[Path], pkg_dir: Path) -> None:
    bag_dir = pkg_dir / "images"
    if not bag_dir.exists():
        bag_dir.mkdir()
    create_bagit_manifest(image_paths, bag_dir)
    move_data_files(image_paths, bag_dir)
    create_bag_tag_files(bag_dir)

    return None


def move_and_bag_stream_files(stream_path: list[Path], pkg_dir: Path) -> None:
    bag_dir = pkg_dir / "streams"
    if not bag_dir.exists():
        bag_dir.mkdir()
    stream_paths = list(stream_path[0].iterdir())
    create_bagit_manifest(stream_paths, bag_dir)
    move_data_files(stream_paths, bag_dir)
    create_bag_tag_files(bag_dir)

    return None


def create_bagit_manifest(paths: list[Path], bag_dir: Path) -> None:
    manifest_lines = []
    for path in paths:
        md5_hash = bagit.generate_manifest_lines(str(path), ["md5"])[0][1]
        manifest_lines.append([md5_hash, Path("data") / path.name])

    with open(bag_dir / "manifest-md5.txt", "w") as f:
        for line in manifest_lines:
            f.write(f"{line[0]}  {line[1]}")

    return None


def create_bag_in_objects(payload_path: Path, md5_path: Path, pkg_dir: Path) -> None:
    bag_dir = pkg_dir / "objects"
    bag_dir.mkdir()
    move_payload(payload_path, bag_dir)
    convert_rclone_md5_to_bagit_manifest(md5_path, bag_dir)
    # generate baginfo.txt and bagit.txt (copying code snippet from bagit)
    create_bag_tag_files(bag_dir)

    return None


def move_payload(payload_path: Path, bag_dir: Path) -> None:
    # instantiate a var for objects dir
    payload_dir = bag_dir / "data"
    # if the object folder does not exist create it
    if not payload_dir.exists():
        payload_dir.mkdir(parents=True)
    else:
        raise FileExistsError(f"{payload_dir} already exists. Not moving files.")

    for a_file in payload_path.iterdir():
        new_ob_path = payload_dir / a_file.name
        # if a payload file is already in the object directory do not move, raise error
        if new_ob_path.exists():
            raise FileExistsError(f"{new_ob_path} already exists. Not moving.")

        a_file.rename(new_ob_path)

    return None


def convert_rclone_md5_to_bagit_manifest(md5_path: Path, bag_dir: Path) -> None:
    # check for manifest
    new_md5_path = bag_dir / "manifest-md5.txt"
    if new_md5_path.exists():
        raise FileExistsError("manifest-md5.txt already exists, review package")

    with open(md5_path, "r") as f:
        manifest_data = f.readlines()

    updated_manifest = [line.replace("  ", "  data/") for line in manifest_data]
    # re-writes the manifest lines
    with open(md5_path, "w") as f:
        f.writelines(updated_manifest)
    # move md5 file to manifest-md5.txt in bag
    md5_path.rename(new_md5_path)

    return None


def create_bag_tag_files(bag_dir: Path) -> None:
    txt = """BagIt-Version: 0.97\nTag-File-Character-Encoding: UTF-8\n"""
    with open(bag_dir / "bagit.txt", "w") as bagit_file:
        bagit_file.write(txt)

    bag_info = {}
    bag_info["Bagging-Date"] = date.strftime(date.today(), "%Y-%m-%d")
    bag_info["Bag-Software-Agent"] = "digarch_scripts"
    total_bytes, total_files = get_oxum(bag_dir / "data")
    bag_info["Payload-Oxum"] = f"{total_bytes}.{total_files}"
    bagit._make_tag_file(bag_dir / "bag-info.txt", bag_info)

    return None


def get_oxum(payload_dir: Path) -> tuple[int, int]:
    total_bytes = 0
    total_files = 0

    for payload_file in payload_dir.rglob("*"):
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
        LOGGER.warning(f"{bag.path} is not valid. Check the bag manifest and oxum.")
    return None
