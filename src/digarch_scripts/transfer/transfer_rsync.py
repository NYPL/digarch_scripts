import argparse
import logging
import re
import subprocess
from pathlib import Path

import digarch_scripts.package.package_base as pb

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def parse_args() -> argparse.Namespace:
    parser = pb.TransferParser(
        description="Create packages for all file transfer files for a single acquisition."
    )
    parser.add_carrierid()
    parser.add_source()
    parser.add_dest()
    parser.add_quiet(help="Suppresses progress bar from rsync")

    return parser.parse_args()


def run_rsync(source: Path, dest: Path, quiet: bool = None) -> None:
    log_folder = (dest / "metadata")
    log_folder.mkdir()
    log_file = log_folder / f"{dest.name}_rsync.log"
    objects_folder = (dest / "objects")
    objects_folder.mkdir()

    cmd = [
        "rsync",
        "-arP",
        f"{source}/",
        objects_folder / "data",
        "--checksum-choice=md5",
        f"--log-file={log_file}",
        "--log-file-format=, %l, %C, %f",
    ]

    if quiet:
        cmd.append("-q")

    process = subprocess.run(cmd)

    if process.returncode != 0:
        LOGGER.warning("Transfer did not complete successfully. Delete transferred files and re-run")

    return


def create_bag_files_in_objects(base_dir: Path, rsync_log: Path, source: Path):
    objects_dir = base_dir / "objects"
    pb.create_bag_tag_files(objects_dir)
    pb.convert_rsync_log_to_bagit_manifest(rsync_log, objects_dir, source)


def run_disktype(source: Path, dest: Path) -> None:
    #determine device to unmount and run disktype on
    if not source.is_mount():
        LOGGER.info(f"Disktype log cannot be generated for a folder. Skipping")
        return

    output = subprocess.check_output(["df", source]).decode("utf8")
    device = re.search(r'(/dev/[a-z0-9]+)', output).group(0)
    parent_device = re.search(r'(/dev/[a-z]+\d)', device).group(0)

    LOGGER.info(f"Dismounting device {device} in order to run disktype, may require password for sudo")
    process = subprocess.run(['diskutil', 'unmount', device])

    if process.returncode != 0:
        LOGGER.warning(f"Unable to dismount {source}. Disktype report not generated. Create manually")
        return

    output = subprocess.check_output(["sudo", "disktype", parent_device]).decode("utf8")

    LOGGER.info(f"Output from disktype: {output}")
    metadata_folder = dest / "metadata"
    if not metadata_folder.exists():
        metadata_folder.mkdir()
    with open(dest / "metadata" / f"{dest.name}_disktype.log", "w") as f:
        f.write(output)

    #remount
    subprocess.run(['diskutil', 'mount', device])
    LOGGER.info("Device remounted")

    return


def main():
    args = parse_args()

    base_dir = pb.create_package_dir(args.dest, args.carrierid)

    run_rsync(args.source, base_dir, args.quiet)
    rsync_log = base_dir / "metadata" / f"{base_dir.name}_rsync.log"
    create_bag_files_in_objects(base_dir, rsync_log, args.source)

    run_disktype(args.source, base_dir)

    pb.validate_objects_bag(base_dir)


if __name__ == "__main__":
    main()
