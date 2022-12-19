import argparse
import os
import json
import pathlib

def parse_args():
    parser = argparse.ArgumentParser()

    def validate_dir(d):
        path = pathlib.Path(d)
        if not path.exists():
            raise argparse.ArgumentTypeError(f'Specified directory does not exist: {d}')
        if not path.is_dir():
            raise argparse.ArgumentTypeError(f'Specified path is not a directory: {d}')

        return path

    parser.add_argument("-d", "--dir",
                        type = validate_dir,
                        help = "Path to the parent directory, e.g. M###_FAComponents")

    return parser.parse_args()



def get_ers(facomponent_dir=pathlib.Path):
    ers = []
    for possible_er in facomponent_dir.glob('**/ER *'):
        if possible_er.is_dir():
            er = possible_er.relative_to(facomponent_dir)
            size = 0
            count = 0
            for path, dirs, files in os.walk(possible_er):
                for f in files:
                    count += 1
                    fp = os.path.join(path, f)
                    size += os.path.getsize(fp)
            ers.append([str(er), size, count])
    return ers


def create_report(input, report):
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
                item = create_report(input, item)
                return report

        report['children'].append(
            create_report(input, {'title': parent, 'children': []})
        )

    return report


def main():
    args = parse_args()

    print('retrieving ER folder paths')
    ers = get_ers(args.dir)

    print('creating report')
    dct = {'title': 'coll', 'children': []}
    for er in ers:
        dct = create_report(er, dct)

    print('writing report')
    with open('test.json', 'w') as f:
        json.dump(dct, f)

if __name__=="__main__":
    main()
