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
    parser.add_argument("--images_folder", required=True, type=extant_path, help='Path to working images folder')
    parser.add_argument("--dest", required=True, type=extant_path, help='Path to packaged images folder')
    parser.add_argument("--acqid", required=True, type=acq_id, help='ACQ_####')
    parser.add_argument("--logs_folder", required=False, type=extant_path, help='Path to working logs folder')
    parser.add_argument("--streams_folder", required=False, type=extant_path, help='Path to working streams folder')

    return parser.parse_args()


def find_category_files(file_groups: dict, source_dir: Path, acq_id: str, category: str) -> dict:
    for file in source_dir.iterdir():
        carrier_id_match = re.search(rf'{acq_id}_\d\d\d\d\d\d+', file.name)
        if not carrier_id_match:
            continue
        carrier_id = carrier_id_match.group(0)

        if not carrier_id in file_groups:
            file_groups[carrier_id] = {category: []}
        elif not category in file_groups[carrier_id]:
            file_groups[carrier_id][category] = []

        file_groups[carrier_id][category].append(file)

    return file_groups


def find_carrier_files(carrier_files: dict, log_dir: Path, images_dir: Path, stream_dir: Path, acq_id: str) -> dict:
    carrier_files = find_category_files(carrier_files, log_dir, acq_id, 'logs')
    carrier_files = find_category_files(carrier_files, images_dir, acq_id, 'images')
    carrier_files = find_category_files(carrier_files, stream_dir, acq_id, 'streams')

    return carrier_files


def package_carriers(carrier_files: dict, acq_dir: Path) -> None:
    for carrier, files in carrier_files.items():
        base_dir = pb.create_package_dir(acq_dir, carrier)
        pb.move_metadata_files(files['logs'], base_dir)
        pb.move_diskimage_files(files['images'], base_dir)
        pb.move_stream_files(files['streams'], base_dir)


def main():
    args = parse_args()

    carrier_files = find_carrier_files({}, args.logs_folder, args.images_folder, args.streams_folder, args.acqid)
    package_carriers(carrier_files, args.dest)



if __name__ == "__main__":
    main()
