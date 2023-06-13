import argparse
import os
import json
import pathlib


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
        type = validate_dir,
        help = "Path to the parent directory, e.g. M###_FAComponents",
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
) -> list[str, int, int]:
    ers = []
    for possible_er in facomponent_dir.glob('**/ER *'):
        objects_dir = possible_er.joinpath('objects')
        if possible_er.is_dir() and objects_dir.is_dir():
            #
            er = possible_er.relative_to(facomponent_dir)
            size = 0
            count = 0
            for path, dirs, files in os.walk(objects_dir):
                for f in files:
                    count += 1
                    fp = os.path.join(path, f)
                    size += os.path.getsize(fp)
            ers.append([str(er), size, count])
    return ers


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
        number, name = input[0].split('.', maxsplit=1)
        report['children'].append({
            'title': input[0],
            'er_number': number,
            'er_name': name,
            'file_size': input[1],
            'file_number': input[2]
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

    print('retrieving ER folder paths')
    ers = get_ers(args.dir)

    print('creating report')
    stub_report = {'title': 'coll', 'children': []}
    full_report = create_report(ers, stub_report)


    print('writing report')
    report_file = args.output.joinpath(f'{args.dir.name}.json')
    write_report(full_report, report_file)


if __name__=="__main__":
    main()
