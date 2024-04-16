import argparse
import os
import json
import pathlib
import logging
import re
LOGGER = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser()

    def validate_dir(
        d: str
    ) -> pathlib.Path:
        path = pathlib.Path(d)
        if not path.exists():
            raise argparse.ArgumentTypeError(
                f'Specified directory does not exist: {d}'
            )
        if not path.is_dir():
            raise argparse.ArgumentTypeError(
                f'Specified path is not a directory: {d}'
            )

        return path

    def validate_output_dir(f) -> pathlib.Path:

        path = pathlib.Path(f)

        if not path.exists():
            raise argparse.ArgumentTypeError(
                f'Output directory does not exist: {f}'
            )

        return path

    parser.add_argument(
        "-d", "--dir",
        type=validate_dir,
        help="Path to the parent directory, e.g. M###_FAComponents",
        required = True
    )

    parser.add_argument(
        '-o', '--output',
        help="report destination directory",
        type=validate_output_dir,
        required=True
    )

    return parser.parse_args()


def get_ers(
    facomponent_dir: pathlib.Path
) -> list[str, int, int, str]:
    ers = []
    for possible_er in facomponent_dir.glob('**/ER *'):
        objects_dir = possible_er.joinpath('objects')
        if possible_er.is_dir():
            if objects_dir.is_dir():
                er = possible_er.relative_to(facomponent_dir)
                size = 0
                count = 0
                for path, dirs, files in os.walk(objects_dir):
                    for f in files:
                        count += 1
                        fp = os.path.join(path, f)
                        if os.path.getsize(fp) == 0:
                            LOGGER.warning(
                            f'{possible_er.name} contains the following 0-byte file: {f}. Review this file with the processing archivist.')
                        size += os.path.getsize(fp)
            else:
                LOGGER.warning(
                    f'{possible_er.name} does not contain an object folder. It will be omitted from the report.')
                continue
        if count == 0:
            LOGGER.warning(
                f'{possible_er.name} does not contain any files. It will be omitted from the report.')
            continue
        if size == 0:
            LOGGER.warning(
                f'{possible_er.name} contains no files with bytes. This ER is omitted from report. Review this ER with the processing archivist.')
            continue

        ers.append([str(er), size, count, possible_er.name])
    return ers

def extract_collection_title(facomponent_dir: pathlib.Path) -> str:
    if re.match(r'M\d+\_FAcomponents', facomponent_dir.name):
        return facomponent_dir.name
    else:
        LOGGER.warning(
            f'Parent folder does not match CollectionID_FAcomponents naming convention: {facomponent_dir.name}'
        )

def audit_ers(ers: list[list[str, str, str]]) -> None:
    er_numbers_used = {}
    for er in ers:
        number = re.match(r'ER (\d+)', er[3])

        if not number:
            LOGGER.warning(
                f'ER is missing a number: {er[3]}. Review the ERs with the processing archivist'
            )
            er_number = 0
        else:
            er_number = int(number[1])

        if not er_number in er_numbers_used.keys():
            er_numbers_used[er_number] = [er[3]]
        else:
            er_numbers_used[er_number].append(er[3])

    # test for er number gaps
    er_min = min(er_numbers_used.keys())
    er_max = max(er_numbers_used.keys())
    for i in range(er_min, er_max):
        if i not in er_numbers_used.keys():
            LOGGER.warning(
                f'Collection uses ER {er_min} to ER {er_max}. ER {i} is skipped. Review the ERs with the processing archivist'
            )

    # test for duplicate ers
    for er_number, er_names in er_numbers_used.items():
        if len(er_names) > 1:
            LOGGER.warning(
                f'ER {er_number} is used multiple times: {", ".join(er_names)}. Review the ERs with the processing archivist'
            )

    return None


def create_report(
    input: list[list[str, int, int]],
    report: dict
) -> dict:
    for er in input:
        report = process_item(er, report)

    return report


def process_item(
    input: list[str, int, int],
    report: dict
) -> dict:
    if not '/' in input[0]:
        # although not recommended, an extra character is allowed after the ER number
        parts = re.match(r'(ER \d+)[^\d]?\s(.*)', input[0])
        report['children'].append({
            'title': input[0],
            'er_number': parts.group(1),
            'er_name': parts.group(2),
            'file_size': input[1],
            'file_count': input[2]
        })
    else:
        parent, child = input[0].split('/', maxsplit=1)
        input[0] = child
        for item in report['children']:
            if item['title'] == parent:
                item = process_item(input, item)
                return report

        report['children'].append(
            process_item(input, {'title': parent, 'children': []})
        )

    return report

def write_report(
    report: dict,
    dest: pathlib.Path
) -> None:
    with open(dest, 'w') as f:
        json.dump(report, f)

def main():
    args = parse_args()

    LOGGER.info('collecting data from file system')
    colltitle = extract_collection_title(args.dir)
    ers = get_ers(args.dir)

    LOGGER.info('creating report')
    stub_report = {'title': colltitle, 'children': []}
    full_report = create_report(ers, stub_report)


    LOGGER.info('writing report')
    report_file = args.output.joinpath(f'{colltitle}.json')
    write_report(full_report, report_file)


if __name__=="__main__":
    main()
