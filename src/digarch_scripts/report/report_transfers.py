import csv
import logging
from datetime import date
from pathlib import Path

from digarch_scripts.package import package_base

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def parse_args():
    """
    Parse command line arguments.

    :return: The parsed arguments.
    """
    parser = package_base.TransferParser(
        description="Report on the transfers in a directory."
    )
    parser.add_acqid()
    parser.add_transfers()
    parser.add_dest()

    return parser.parse_args()


def collect_stats(transfer_path: Path) -> list[date, int, int, int, int]:
    """
    Collects statistics about the transfers in the given directory.

    :param path: Path to the directory containing the transfer files.
    :return: A tuple containing the date of transfer, number of image files,
             cumulative size of image files, number of object files, and
             cumulative size of object files.
    """

    # initialize the image and object statistics
    image_date = None
    image_stats = []
    object_date = None
    object_stats = []

    # Iterate over the files in the directory.
    for path in transfer_path.iterdir():
        # Skip directories.
        if path.name == "images":
            image_date, image_stats = collect_bag_stats(path)
        elif path.name == "objects":
            object_date, object_stats = collect_bag_stats(path)
        else:
            continue

    # Return the statistics
    stats_stub = transfer_path.name.rsplit("_", 1)

    if not object_stats and not image_stats:
        LOGGER.info(f"No images or objects found for {transfer_path}.")
        return None
    else:
        if image_date:
            stats_stub.append(image_date)
        else:
            stats_stub.append(object_date)
        stats_stub.extend(image_stats if image_stats else [0, 0])
        stats_stub.extend(object_stats if object_stats else [0, 0])

        return stats_stub


def collect_bag_stats(bag_path: Path) -> tuple[date, list[int, int]]:
    """
    Collects statistics from a bag in the given directory.

    :param path: Path to the directory containing the object transfer files.
    :return: A tuple containing the date of the transfers and a list of the
             number of files and cumulative size of files.
    """

    # Initialize the statistics
    bagdate = None
    size = 0
    files = 0

    # Check that image_path is a bag
    possible_bag_info = bag_path / "bag-info.txt"
    if not possible_bag_info.exists():
        LOGGER.warning(f"Directory should be formatted as a bag: {bag_path}")
        return None

    else:
        with open(possible_bag_info, "r") as bag_info:
            for line in bag_info:
                if line.startswith("Bagging-Date:"):
                    bagdate = date.fromisoformat(line.split(":")[1].strip())
                elif line.startswith("Payload-Oxum:"):
                    size, files = line.split(":")[1].strip().split(".")

        if not bagdate:
            LOGGER.warning(f"Bagging date not found in {possible_bag_info}")
            return None

        if not size or not files:
            LOGGER.warning(f"Bagging size or files not found in {possible_bag_info}")
            return None

        return bagdate, [int(files), int(size)]


def write_stats(stats: list, dest: Path, acqid: str) -> None:
    """
    Write the statistics to a report file.

    :param stats: A list of lists containing the date of transfer, number of image files,
                  cumulative size of image files, number of object files, and cumulative size of object files.
    :param dest: The destination directory for the report.
    :param acqid: The acquisition ID.
    """
    with open(dest / f"{acqid}_transfer_report.txt", "w") as report:
        writer = csv.writer(report)
        writer.writerow(
            ["acquisition_id", "object_id", "date", "image_files", "image_size", "object_files", "object_size"]
        )
        writer.writerows(stats)

    return None


def main():
    """
    Main function for reporting on transfers.

    Collects statistics on the transfers in the given directory and writes them to a report file.
    """
    args = parse_args()

    acq_folder = args.transfers / args.acqid

    if not acq_folder.exists():
        LOGGER.error(f"Transfer folder not found: {acq_folder}")
        return
    else:
        all_stats = []
        for transfer in acq_folder.iterdir():
            stats = collect_stats(transfer)
            if stats:
                LOGGER.info(stats)
                all_stats.append(stats)
            else:
                LOGGER.warning(f"No stats found for {transfer}")

        write_stats(all_stats, args.dest, args.acqid)

    return None


if __name__ == "__main__":
    main()
