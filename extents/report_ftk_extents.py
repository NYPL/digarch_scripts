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

def make_series(xml_list, level=0):

    '''
    recursive function that iterates through the xml_list
    and nests records based on their level
    which is derived from the indentation.
    Returns nested dict with duplicate records.
    '''

    result = {}


    for i in range(len(xml_list)):

        try:
            xml_list[i+1]
        except:
            return result

        try:
            xml_list[i][0] in result
        except:
            return result

        # the level of the next item in the xml_list

        next_l = xml_list[i+1][1]

        # x will be the current item

        x = xml_list[i]

        # key contains three values
        # 0 - record name, 1 - level, 2 - extent (ER) or id (series)

        key = x

        val = x[2]

        if next_l > level:

                # new_dict will be equal to an empty dict until
                # the recursion reaches the file level
                # nested empty dict will be passed as the value to nest_dict

                new_dict = make_series(xml_list[i+1:], level=next_l)
                nest_dict(result, key, new_dict, level)

        elif next_l < level:

            # this will nest file level information

            nest_dict(result, key, val, level)
            return result

        else:

            # this will nest file level information

            nest_dict(result, key, val, level)

    return result

def nest_dict(data, key, val, level):

    '''
        evaluates if the value is an empty dict or extent information
        and creates dict key value pairs accordingly.
    '''

    # in this case val is an empty dict

    if type(key[2]) is str:

        key_unq = "title_" + key[2]
        child = "children_" + key[2]
        level = "level_" + key[2]
        data[key_unq] = key[0]
        data[level] = key[1]
        data[child] = val

    else:

        # reduces duplication of ER records in the nested dict

        if level != key[1]:
            pass

        elif level == 0:
            pass

        else:

            # creates a dict with file level information inside the series

            key_unq = "title_" + key[2]['bookmark_id']
            f_id = "id_" + key[2]['bookmark_id']
            f_name = "name_" + key[2]['bookmark_id']
            f_num = "num_" + key[2]['bookmark_id']
            f_size = "size_" + key[2]['bookmark_id']
            f_count = "count_" + key[2]['bookmark_id']

            data[key_unq] = key[0]
            data[f_id] = key[2]['bookmark_id']
            data[f_name] = key[2]['er_name']
            data[f_num] = key[2]['er_number']
            data[f_size] = key[2]['file_size']
            data[f_count] = key[2]['file_count']

def filter_dupes(data, l):

    '''
    recursive function that removes duplicate records from the nested dict
    by checking if the level of the record corresponds
    to the anticipated level for that depth. Function assumed that the first level
    it encounters is the correct level for that evaluation.
    For the first level, all records should have a level of 24, the next
    level -- 36, etc. each id should only occur once in the resulting dict.
    '''

    for key in data.keys():
            if "level" in key:
                if data[key] == l:

                    del_keys = []

                    for key in data.keys():
                        if "level" in key:
                            if data[key] != l:
                                prefix = key.split('_')[1]
                                del_keys.append(prefix)

                    for bad_key in del_keys:
                        data.pop("title_"+bad_key)
                        data.pop("children_"+bad_key)
                        data.pop("level_"+bad_key)

                    return data

                elif data[key] < l:

                    prefix = key.split("_")[1]

                    for key in data.keys():
                        if prefix in key:
                            if "child" in key:
                                filter_dupes(data[key], l)

                else:

                    pass


def get_collection_children(data, coll):

    '''
        recursive function that reformats the dict to prepare it for import into archivesspace.
        adds each pair of keys and values with the same unique suffix as a dict with
        generic key val names to a list under the 'children' key.
        returns a dict with the structure 'title' : series title, 'children' --> list of dicts.
        If file level, child dict does not have children but has all extent information.
        Returns a new dict with data structured this way.

    '''

    try:
        type(data) == dict
    except:
        pass

    prefixes = []

    # make a list of prefixes to iterate through

    for key in data.keys():
        if "bk" in key:
            prefix = key.split("_")[1]
            if prefix not in prefixes:
                prefixes.append(prefix)
        else:
            pass

    # for each prefix makes a new dict, fills it with the correct data types
    # and appends it in the style of a 'title' : title, 'children' : list

    for prefix in prefixes:
        series = {}
        for key in data.keys():
            if prefix in key:
                if "title" in key:
                    title = data[key]
                    series["title"] = data[key]

                    # add all the extent information to file level dicts

                    if "ER " in series['title']:

                        series['bookmark_id'] = data["id_" + prefix]
                        series['er_name'] = data["name_" + prefix]
                        series['er_number'] = data["num_" + prefix]
                        series['file_size'] = data["size_" + prefix]
                        series['file_count'] = data["count_" + prefix]

                elif "children" in key:

                    child = data[key]

                    series['children'] = []
                    [get_collection_children(data[key], {'children' : series['children']})]

        coll['children'].append(series)

    return coll

def update_collection_title(data, tree):

    '''
    Changes the collection title from M_title to the actual collection name
    as found in the XML report.
    '''

    name = str

    case_info = tree.xpath(
        '/fo:root/fo:page-sequence[@master-reference="caseInfoPage"]/fo:flow/fo:table'\
        '/fo:table-body/fo:table-row/fo:table-cell/fo:block/text()',
        namespaces=FO_NAMESPACE
    )

    for i, txt in enumerate(case_info):
        if txt == "Case Name":
            name = case_info[i+1]

    data['title'] = name

    return data

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
    print("Parsing XML ...")
    tree = etree.parse(args.file)
    print(time.perf_counter())
    print('Transforming XML into a list ...')
    xml_list = create_er_list(tree)
    print(time.perf_counter())
    print('Calculating extents for each file ...')
    xml_list = add_extents_to_ers(tree, xml_list)
    print(xml_list)
    print(time.perf_counter())
    print('Nesting series and subseries ...')
    data = make_series(xml_list)
    print(time.perf_counter())

    levels = []

    for x in xml_list:
        if x[1] not in levels:
            levels.append(x[1])

    print('Removing duplicates ...')
    for l in levels:
        filter_dupes(data, l)

    collection = {"title" : "M_Collection_Title", "children" : []}

    print('Preparing JSON file ...')
    aspace_import = get_collection_children(data, collection)

    aspace_import = update_collection_title(aspace_import, tree)

    destination = args.output

    print("File transformation succesful.")
    make_json(destination, aspace_import)

if __name__ == '__main__':
    main()