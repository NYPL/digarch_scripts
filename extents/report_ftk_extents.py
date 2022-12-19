from lxml import etree
import json
import re
import time
import argparse
import os
import pathlib

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


def create_er_list(tree: etree.ElementTree):

    '''
    This transforms the table of contents into a list of lists
    where each list item has a title, indentation as int, and reference-id.
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
                ers.append([hierarchy.copy(), level, refid])

    return ers


def add_extents_to_ers(tree: etree.ElementTree, er_list: list):

    '''
    appends extent information to the
    item in the list with the corresponding id
    if that item is an "ER" at the file level.
    returns the list with this new information appended.
    the information appended is the is the record's information:
    name, number, id, file size, and file count.
    '''

    extent_tree = tree.xpath(
        '/fo:root/fo:page-sequence[@master-reference="bookmarksPage"]/fo:flow/fo:table[@id]'\
        ,
        namespaces=FO_NAMESPACE
    )

    file_list = transform_xml_tree(extent_tree)
    ers_with_extents = []

    for er in er_list:
        bookmark_id = er[2]
        size, count = get_er_report(file_list, bookmark_id)
        ers_with_extents.append(['/'.join(er[0]), size, count])
    return ers_with_extents


def transform_xml_tree(tree):

    '''
    transforms each row in the 'bookmarksPage' table
    into a string. this string contains all the extent information
    that will be calculated later.
    the return is a list of lists where the first item is the id with
    the prefix bk and the second item is a string serialized from the XML.
    '''

    extents = []
    for row in tree:

        #row is an /fo:row in /fo:table[@id]

        y = []
        file_id=row.get('id')
        y.append(file_id)
        y.append(file_id.split('_')[0])
        y.append(etree.tostring(row, method='text', encoding="UTF-8"))
        extents.append(y)

    return extents

def get_er_report(
    er_files: list,
    bookmark_id: str) -> dict:

    '''
    extract er number, er name, byte count, and file count
    title is the record title, starting with ER : Title,
    and the id is an id with a bk prefix.
    Returns a dict with the information for extent.
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


def create_report(input, report):
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


def make_json(destination, report):

    '''
    creates a json file with the name of the collection as the file name
    destination is the file path from args parse and report
    is the collection style dict
    '''

    name = report['title']
    name = name.replace(" ", "_")

    with open(os.path.join(destination, f'{name}.json'), 'w') as file:
        json.dump(report, file)

def main():
    args = _make_parser()

    print('Parsing XML ...')
    tree = etree.parse(args.file)

    print('Creating report ...')
    xml_list = create_er_list(tree)
    xml_list = add_extents_to_ers(tree, xml_list)

    dct = {'title': 'coll', 'children': []}
    for er in xml_list:
        dct = create_report(er, dct)

    print("Writing report ...")
    make_json(args.output, dct)

if __name__ == '__main__':
    main()