from lxml import etree
import json
import re
import time
import argparse
import os
import pathlib
import logging

LOGGER = logging.getLogger(__name__)

# Namespace for the FTK output XML
FO_NAMESPACE = {'fo': 'http://www.w3.org/1999/XSL/Format'}

def _make_parser():

    def validate_file_input(f) -> pathlib.Path:
        '''
        Ensure the input file exists
        '''

        path = pathlib.Path(f)

        if not path.exists():
            raise argparse.ArgumentTypeError(
                f'Directory or file does not exist: {f}'
            )

        if not path.suffix.lower() in ['.xml', '.fo']:
            raise argparse.ArgumentTypeError(
                'Not a valid file type. Expect .xml or .fo'
            )

        return path

    def validate_output_dir(f) -> pathlib.Path:

        path = pathlib.Path(f)

        if not path.exists():
            raise argparse.ArgumentTypeError(
                f'Output directory does not exist: {f}'
            )

        return path


    parser = argparse.ArgumentParser(
        description='Create a JSON report from XML'
    )

    parser.add_argument(
        '-f', '--file',
        help="path to FTK XML report",
        type=validate_file_input,
        required=True
    )

    parser.add_argument(
        '-o', '--output',
        help="destination directory",
        type=validate_output_dir,
        required=True
    )

    return parser.parse_args()


def create_er_list(
    tree: etree.ElementTree
) -> list[list[str, str]]:

    '''
    This transforms the table of contents into a list of lists
    where each list item has the hierarchy of titles and a reference-id.
    This list is the intermediate data structure used to build the nested dict.
    The function returns the entire list.
    '''

    tree = tree.xpath(
        '/fo:root/fo:page-sequence[@master-reference="TOC"]/fo:flow',
        namespaces=FO_NAMESPACE
    )[0]

    ers = []
    hierarchy = []
    for child in tree:
        # skip rows with an indent < 24
        if not child.get("start-indent"):
            continue

        indent = int(child.get("start-indent").split(sep="pt")[0])
        level = (indent//12) - 2

        if level >= 0:
            # build a list of parents based on level
            if level <= len(hierarchy) - 1:
                hierarchy = hierarchy[:level]
            elif level > len(hierarchy) + 1:
                raise ValueError(
                    f'Unexpected jump in hierarchy at {child.text}'
                )
            hierarchy.append(child.text)

            # only record if entry is an ER
            possible_ref = child.xpath(
                'fo:basic-link/fo:page-number-citation', namespaces=FO_NAMESPACE
            )
            if possible_ref and hierarchy[-1].startswith('ER'):
                refid = possible_ref[0].get('ref-id')
                ers.append(
                    ['/'.join(hierarchy.copy()), refid]
                )

    return ers


def transform_bookmark_tables(
    tree: etree.ElementTree
) -> list[list[str, str, str]]:

    '''
    transforms each row in the 'bookmarksPage' table
    into a string. this string contains all the extent information
    that will be summarized later.
    the return is a list of lists where the first item is the id with
    the prefix bk and the second item is a string serialized from the XML.
    '''

    extent_tree = tree.xpath(
        '/fo:root/fo:page-sequence[@master-reference="bookmarksPage"]/fo:flow/fo:table[@id]'\
        ,
        namespaces=FO_NAMESPACE
    )

    bookmark_contents = []
    for row in extent_tree:

        #row is an /fo:row in /fo:table[@id]

        bookmark_id = row.get('id')
        id_number = bookmark_id.split('_')[0]
        file_table = etree.tostring(row, method='text', encoding="UTF-8")
        bookmark_contents.append([bookmark_id, id_number, file_table])

    return bookmark_contents


def add_extents_to_ers(
    er_list: list[list[str, str]],
    bookmark_tables: list[list[str, int, int]]
) -> list[list[str, int, int]]:

    '''
    summarizes the extent for each ER by
    correlating the table of contents with the bookmark tables.
    Returns list of lists with hierarchal ER string, file size, and file count.
    '''

    ers_with_extents = []

    for er in er_list:
        bookmark_id = er[1]
        size, count = get_er_report(bookmark_tables, bookmark_id)

        if count == 0:
            er_name = er[0].split('/')[-1]
            LOGGER.warning(
                f'{er_name} does not contain any files. It will be omitted from the report.')
            continue

        ers_with_extents.append([er[0], size, count])

    return ers_with_extents


def get_er_report(
    er_files: list[str, str, str],
    bookmark_id: str
) -> tuple([int, int]):

    '''
    extract the total file size and file count for a given bookmark ID
    Returns a tuple with the file size and file count.
    '''

    size = 0
    count = 0

    prefix = bookmark_id.replace('k', 'f')
    for entry in er_files:
        if prefix in entry:

            # filesize should be stored as a string in the first column
            # empty files are skipped
            byte_string = entry[2].decode("utf-8")
            nonzero_bytes = re.findall(r'(\d+)\sB', byte_string)

            if nonzero_bytes:
                file_size = int(nonzero_bytes[0])
                size += file_size
                count += 1
            else:
                pass

    return size, count


def create_report(
    input: list[str, int, int],
    report: dict
) -> dict:

    '''
    recursive function to insert a given bookmark into a nested dictionary
    based on the hierarchy of component titles.
    Returns a nested dictionary
    '''

    if not '/' in input[0]:
        number, name = input[0].split(':', maxsplit=1)
        report['children'].append({
            'title': input[0],
            'er_number': number,
            'er_name': name.strip(),
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

def extract_collection_title(
    tree: etree.ElementTree
    ) -> str:

    case_info = tree.xpath(
        '/fo:root/fo:page-sequence[@master-reference="caseInfoPage"]/fo:flow/fo:table'\
        '/fo:table-body/fo:table-row/fo:table-cell/fo:block/text()',
        namespaces=FO_NAMESPACE
    )

    for i, txt in enumerate(case_info):
        if txt == "Case Name":
            collname = case_info[i+1]

    return collname

def make_json(
    destination: pathlib.Path,
    report: dict,
    collname
) -> None:

    '''
    creates a json file with the name of the collection as the file name
    destination is the file path from args parse and report
    is the collection style dict
    '''

    name = collname
    name = name.replace(" ", "_")

    with open(os.path.join(destination, f'{name}.json'), 'w') as file:
        json.dump(report, file)


def main() -> None:
    args = _make_parser()

    print('Parsing XML ...')
    tree = etree.parse(args.file)

    print('Creating report ...')
    ers = create_er_list(tree)
    bookmark_tables = transform_bookmark_tables(tree)
    ers_with_extents = add_extents_to_ers(ers, bookmark_tables)
    colltitle = extract_collection_title(tree)
    dct = {'title': colltitle, 'children': []}
    for er in ers_with_extents:
        dct = create_report(er, dct)

    print("Writing report ...")
    make_json(args.output, dct, colltitle)

if __name__ == '__main__':
    main()