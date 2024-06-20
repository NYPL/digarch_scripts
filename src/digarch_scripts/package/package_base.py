import argparse
import logging
import os
import re
from datetime import date
from pathlib import Path

import bagit

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class TransferParser(argparse.ArgumentParser):
    def extant_path(self, p: str) -> Path:
        path = Path(p)
        if not path.exists():
            raise argparse.ArgumentTypeError(f"{path} does not exist")
        return path

    def acq_id(self, id: str) -> Path:
        pattern = r"ACQ_\d{4}"
        old_pattern = r"M\d{4-6}"
        if not re.match(pattern, id):
            if not re.match(old_pattern, id):
                raise argparse.ArgumentTypeError(
                    f"{id} does not match the expected {type} pattern, {pattern}"
                )
        return id

    def carrier_id(self, id: str) -> Path:
        pattern = r"ACQ_\d{4}_\d{6,7}"
        old_pattern = r"M\d{4-6}_\d{6,7}"
        if not re.match(pattern, id):
            if not re.match(old_pattern, id):
                raise argparse.ArgumentTypeError(
                    f"{id} does not match the expected {type} pattern, {pattern}"
                )
        return id

    def add_acqid(self) -> None:
        self.add_argument(
            "--acqid", "--id", required=True, type=self.acq_id, help="ACQ_####"
        )

    def add_carrierid(self) -> None:
        self.add_argument(
            "--carrierid", required=True, type=self.carrier_id, help="ACQ_####_#######"
        )

    def add_source(self) -> None:
        self.add_argument(
            "--source",
            required=True,
            type=self.extant_path,
            help="Path to mount carrier",
        )

    def add_payload(self) -> None:
        self.add_argument(
            "--payload",
            required=True,
            type=self.extant_path,
            help="Path to files transferred from single carrier",
        )

    def add_objects_folder(self) -> None:
        self.add_argument(
            "--objects-folder",
            required=True,
            type=self.extant_path,
            help="Path to working folder with file transfers from all transfers",
        )

    def add_md5(self) -> None:
        self.add_argument(
            "--md5",
            required=True,
            type=self.extant_path,
            help="Path to a log with md5 checksums, e.g. rclone or rsync log",
        )

    def add_images_folder(self) -> None:
        self.add_argument(
            "--images_folder",
            required=True,
            type=self.extant_path,
            help="Path to working images folder",
        )

    def add_log(self) -> None:
        self.add_argument(
            "--log",
            required=True,
            type=self.extant_path,
            help="Path to a log file from the transfer process",
        )

    def add_logs_folder(self) -> None:
        self.add_argument(
            "--logs_folder",
            required=False,
            type=self.extant_path,
            help="Path to working folder with logs from all transfers",
        )

    def add_streams_folder(self) -> None:
        self.add_argument(
            "--streams_folder",
            required=False,
            type=self.extant_path,
            help="Path to working folder with streams from all transfers",
        )

    def add_dest(self) -> None:
        self.add_argument("--dest", required=True, type=self.extant_path)

    def add_transfer(self) -> None:
        self.add_argument(
            "--transfers",
            required=True,
            type=self.extant_path,
            help="Path to the directory containing all transfers",
        )

    def add_quiet(self, **kwargs) -> None:
        self.add_argument("-q", "--quiet", action="store_true", **kwargs)


def find_category_of_carrier_files(
    carrier_files: dict, acq_id: str, source_dir: Path, exts: list, category: str
) -> dict:
    for path in source_dir.iterdir():
        if not path.suffix in exts:
            continue
        carrier_id_match = re.search(rf"{acq_id}_\d\d\d\d\d\d+", path.name)
        if not carrier_id_match:
            continue
        carrier_id = carrier_id_match.group(0)

        if not carrier_id in carrier_files:
            carrier_files[carrier_id] = {category: []}
        elif not category in carrier_files[carrier_id]:
            carrier_files[carrier_id][category] = []

        carrier_files[carrier_id][category].append(path)

    return carrier_files


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


def create_bag_in_dir(
    paths: list[Path],
    pkg_dir: Path,
    type: str,
    manifest_source: Path = None,
    source: str = None,
) -> None:
    bag_dir = pkg_dir / type
    bag_dir.mkdir()

    if len(paths) == 1 and paths[0].is_dir():
        paths = list(paths[0].iterdir())

    if source == "rclone":
        convert_rclone_md5_to_bagit_manifest(manifest_source, bag_dir)
    elif source == "rsync":
        convert_rsync_log_to_bagit_manifest(manifest_source, bag_dir)
    else:
        create_bagit_manifest(paths, bag_dir)

    move_data_files(paths, bag_dir)
    create_bag_tag_files(bag_dir)


def create_bag_in_images(image_paths: list[Path], pkg_dir: Path) -> None:
    create_bag_in_dir(image_paths, pkg_dir, "images")

    return None


def create_bag_in_streams(stream_path: Path, pkg_dir: Path) -> None:
    create_bag_in_dir([stream_path], pkg_dir, "streams")
    if not list(stream_path.iterdir()):
        stream_path.rmdir()

    return None


def create_bag_in_objects(
    objects_path: Path,
    pkg_dir: Path,
    manifest_source: Path = None,
    manifest_type: str = None,
) -> None:
    create_bag_in_dir(
        [objects_path], pkg_dir, "objects", manifest_source, manifest_type
    )
    if not list(objects_path.iterdir()):
        objects_path.rmdir()

    return None


def create_bagit_manifest(paths: list[Path], bag_dir: Path) -> None:
    # paths must be files
    manifest_lines = []
    for path in paths:
        md5_hash = bagit.generate_manifest_lines(str(path), ["md5"])[0][1]
        manifest_lines.append([md5_hash, Path("data") / path.name])

    with open(bag_dir / "manifest-md5.txt", "w") as f:
        for line in manifest_lines:
            f.write(f"{line[0]}  {line[1]}")

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


def convert_rsync_log_to_bagit_manifest(
    rsync_log: Path, bag_dir: Path, prefix: Path = None
) -> None:
    # check for manifest
    new_md5_path = bag_dir / "manifest-md5.txt"
    if new_md5_path.exists():
        raise FileExistsError("manifest-md5.txt already exists, review package")

    with open(rsync_log, "r") as f:
        log_data = f.readlines()

    if not prefix:
        prefix = os.path.commonprefix(
            [
                os.path.dirname(line.split(",", 4)[3])
                for line in log_data
                if len(line.split(",")) > 1
            ]
        )
    else:
        prefix = str(prefix)

    manifest_data = []

    for line in log_data:
        parts = line.strip().split(",", 3)
        if not len(parts) == 4:
            continue

        poss_rel_path = parts[3].strip().replace(prefix[1:], "data")

        poss_md5_hash = parts[2].strip().lower()
        if not poss_md5_hash:
            continue
        elif not re.match(r"[0-9a-f]{32}", poss_md5_hash):
            LOGGER.warning(
                f"{str(rsync_log.name)} should be formatted with md5 hash in the 3rd comma-separated fields. Skipping this line: {line}"
            )
            continue

        manifest_data.append(f"{poss_md5_hash}  {poss_rel_path}\n")

    # write the manifest lines
    with open(new_md5_path, "w") as f:
        f.writelines(manifest_data)

    return None


def create_bag_tag_files(bag_dir: Path) -> None:
    txt = """BagIt-Version: 0.97\nTag-File-Character-Encoding: UTF-8\n"""
    with open(bag_dir / "bagit.txt", "w") as bagit_file:
        bagit_file.write(txt)

    bag_info = {}
    bag_info["ACQ-Object-ID"] = bag_dir.parent.name
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


def validate_bag(pkg_dir: Path, subfolder: str) -> None:
    bag_dir = pkg_dir / subfolder
    bag = bagit.Bag(str(bag_dir))
    try:
        bag.validate(completeness_only=True)
        LOGGER.info(f"{bag.path} is valid.")
    except bagit.BagValidationError:
        LOGGER.warning(f"{bag.path} is not valid. Check the bag manifest and oxum.")
    return None


def validate_objects_bag(pkg_dir: Path) -> None:
    validate_bag(pkg_dir, "objects")

    return None


def validate_images_bag(pkg_dir: Path) -> None:
    validate_bag(pkg_dir, "images")

    return None


def validate_streams_bag(pkg_dir: Path) -> None:
    validate_bag(pkg_dir, "streams")

    return None
