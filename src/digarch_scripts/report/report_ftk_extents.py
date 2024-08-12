from lxml import etree
import json
from collections import defaultdict
import re
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


def create_component_list(
    tree: etree.ElementTree
) -> list[list[list[str], str, str]]:

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

    components = []
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

            # only record if entry is an ER or DI
            possible_ref = child.xpath(
                'fo:basic-link/fo:page-number-citation', namespaces=FO_NAMESPACE
            )
            if possible_ref and (hierarchy[-1].startswith('ER') or hierarchy[-1].startswith('DI')):
                refid = possible_ref[0].get('ref-id')
                components.append(
                    [hierarchy.copy(), refid, hierarchy[-1]]
                )

    audit_components(components)

    return components


def audit_components(components: list[list[list[str], str, str]]) -> None:
    er_numbers_used = defaultdict(list)
    di_numbers_used = defaultdict(list)
    for component in components:
        number = re.match(r'(ER|) (\d+):', component[2])

        if not number:
            LOGGER.warning(
                f'Component is missing a number: {component[2]}. Review the bookmarks with the processing archivist'
            )
            er_numbers_used[0].append(component[2])

        elif number[1] == 'ER':
            er_numbers_used[int(number[2])].append(component[2])
        else:
            di_numbers_used[int(number[2])].append(component[2])


    def test_for_number_gaps(numbers_used: dict, type: str):
        if not numbers_used:
            return None

        min_number = min(numbers_used.keys())
        max_number = max(numbers_used.keys())
        for i in range(min_number, max_number):
            if i not in numbers_used.keys():
                LOGGER.warning(
                    f'Collection {type} component range is numbered {min_number} to {max_number}. {i} is skipped. Review the bookmarks with the processing archivist'
                )

    test_for_number_gaps(er_numbers_used, 'ER')
    test_for_number_gaps(di_numbers_used, 'DI')

    def test_for_duplicate_numbers(numbers_used: dict, type: str):
        if not numbers_used:
            return None

        for number, names in numbers_used.items():
            if len(names) > 1:
                LOGGER.warning(
                    f'{type} {number} is used multiple times: {", ".join(names)}. Review the bookmarks with the processing archivist'
                )

    test_for_duplicate_numbers(er_numbers_used, 'ER')
    test_for_duplicate_numbers(di_numbers_used, 'DI')

    return None


def transform_bookmark_tables(
    tree: etree.ElementTree
) -> list[dict]:

    '''
    transforms each row in the 'bookmarksPage' table
    into a string. this string contains all the extent information
    that will be summarized later.
    the return is a list of lists where the first item is the id with
    the prefix bk and the second item is a string serialized from the XML.
    '''

    extent_tree = tree.xpath(
        '/fo:root/fo:page-sequence[@master-reference="bookmarksPage"]/fo:flow/fo:table[@id]',
        namespaces=FO_NAMESPACE
    )

    bookmark_contents = []
    for row in extent_tree:
        # row is an /fo:row in /fo:table[@id]
        file_table = row.xpath(
            './fo:table-body/fo:table-row/fo:table-cell/fo:block',
            namespaces=FO_NAMESPACE
        )
        file_dict = {
            file_table[i].text: file_table[i + 1].text
            for i in range(0, len(file_table), 2)
        }
        file_dict['file_id'] = row.get('id')
        file_dict['bookmark_id'] = row.get('id').split('_')[0]
        bookmark_contents.append(file_dict)

    return bookmark_contents


def add_extents_to_components(
    component_list: list[list[list[str], str, str]],
    bookmark_tables: list[dict]
) -> list[list[str, int, int]]:

    '''
    summarizes the extent for each component by
    correlating the table of contents with the bookmark tables.
    Returns list of lists with hierarchal component string, file size, and file count.
    '''

    components_with_extents = []

    for component in component_list:
        bookmark_id = component[1]
        component_name = component[-1]
        size, count = get_component_report(bookmark_tables, bookmark_id, component_name)

        if count == 0:
            LOGGER.warning(
                f'{component_name} does not contain any files. It will be omitted from the report.')
            continue
        if size == 0:
            LOGGER.warning(
                f'{component_name} contains no files with bytes. This component is omitted from report. Review this component with the processing archivist.')
            continue

        components_with_extents.append([component[0], size, count])

    return components_with_extents


def get_component_report(
    component_files: list[dict],
    bookmark_id: str,
    component_name: str
) -> tuple[int, int]:

    '''
    extract the total file size and file count for a given bookmark ID
    Returns a tuple with the file size and file count.
    '''

    size = 0
    count = 0

    prefix = bookmark_id.replace('k', 'f')
    for entry in component_files:
        if entry['bookmark_id'] == prefix:

            byte_string = entry['Logical Size']
            bytes = re.findall(r'(\d+)\sB', byte_string)

            if bytes:
                count += 1
                file_size = int(bytes[0])
                if file_size == 0:
                    file_name = entry['Name']
                    #extract file name, might have to parse file table better
                    LOGGER.warning(
                        f'{component_name} contains the following 0-byte file: {file_name}. Review this file with the processing archivist.')
                size += file_size

            else:
                pass

    return size, count


def create_report(
    input: list[list[str], int, int],
    report: dict
) -> dict:

    '''
    recursive function to insert a given bookmark into a nested dictionary
    based on the hierarchy of component titles.
    Returns a nested dictionary
    '''

    if len(input[0]) == 1:
        number, name = input[0][0].split(':', maxsplit=1)
        report['children'].append({
            'title': input[0][0],
            'er_number': number,
            'er_name': name.strip(),
            'file_size': input[1],
            'file_count': input[2]
        })
    else:
        parent, child = input[0][0], input[0][1:]
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
    components = create_component_list(tree)

    bookmark_tables = transform_bookmark_tables(tree)
    components_with_extents = add_extents_to_components(components, bookmark_tables)
    colltitle = extract_collection_title(tree)
    dct = {'title': colltitle, 'children': []}
    for component in components_with_extents:
        dct = create_report(component, dct)

    print("Writing report ...")
    make_json(args.output, dct, colltitle)

if __name__ == '__main__':
    main()
