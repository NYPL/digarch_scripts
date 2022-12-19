from lxml import etree
import json
import re
import time
import argparse
import os

'''
This global variable is the namespace for the FTK output XML
'''
FO_NAMESPACE = {'fo': 'http://www.w3.org/1999/XSL/Format'}

def _make_parser():

    def validate_file_input(f):

        '''
        This script checks if the input file exists.
        Leaving the XML check out means the
        the script will work with .fo reports.
        '''

        if not os.path.exists(f):
            raise argparse.ArgumentTypeError(
            f'Directory or file does not exist: {f}'
            )
        # if f.split(sep=".")[-1].lower() != "xml":
        #     raise argparse.ArgumentTypeError(
        #     'Not a valid file type. Please use XML.'
        # )
        return f

    def validate_output(f):

        if not os.path.exists(f): 
            raise argparse.ArgumentTypeError(
            f'Target directory does not exist: {f}'
            )
        return f


    parser = argparse.ArgumentParser(description='Create a JSON report from XML')

    '''
    Note that the output argument is required because of how the script
    formats the file name 
    '''

    parser.add_argument(
        "file", 
        help="a path to valid XML",
        type=validate_file_input
    )
    parser.add_argument(
        "output",
        help="destination directory",
        type=validate_output
    )

    args = parser.parse_args()
    return args

def make_list_from_xml(tree):

    '''
    This transforms the table of contents into a list of lists
    where each list item has a title, indentation as int, and reference-id.
    This list is the intermediate data structure used to build the nested dict.
    The function returns the entire list. 
    '''

    tree = tree.xpath('/fo:root/fo:page-sequence[@master-reference="TOC"]/fo:flow', namespaces=FO_NAMESPACE)
    tree = tree[0]

    xml_list = []
    for child in tree:

        # Rows with an indent < 24 or not indent are not part of the records hierarchy.
        # The series level starts at indent 24.

        if child.get("start-indent") is None \
        or int(child.get("start-indent").split(sep="pt")[0]) < 24:
            pass
        else:
            x = [child.text, int(child.get("start-indent").split(sep="pt")[0])]
            
            # the ref-id tag is located deeper in the XML tree
            # in the page-number-citation 

            if child.xpath('fo:basic-link/fo:page-number-citation', namespaces=FO_NAMESPACE):
                y = child.xpath('fo:basic-link/fo:page-number-citation', namespaces=FO_NAMESPACE)
                refid = y[0].get('ref-id')
                x.append(refid)

            xml_list.append(x)

    #p will simplify the logic for the nested dict recursion

    p = ["Placeholder", 36, 'ref-id']

    xml_list.append(p)        
    
    return xml_list

def generate_report(tree, xml_list):
    
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

    extent_list = transform_xml_tree(extent_tree)

    for record in xml_list:
        bookmark_id = record[2]
        bookmark_title = record[0]
        r = re.match("ER", record[0])
        if r:
            append_val_to_xml_list(get_er_report(extent_list, bookmark_title, bookmark_id), xml_list)
        else:
            continue
    return xml_list

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
        y.append(row.get('id'))
        y.append(etree.tostring(row, method='text', encoding="UTF-8"))
        extents.append(y)

    return extents

def get_er_report(extent_list, title, bookmark_id):

    '''
    extract er number, er name, byte count, and file count
    title is the record title, starting with ER : Title,
    and the id is an id with a bk prefix.
    Returns a dict with the information for extent.
    '''

    report = {}

    er_components = title.split(':')
    report['er_number'] = er_components[0]
    report['er_name'] = er_components[1].strip()
    report['bookmark_id'] = bookmark_id

    extent = get_file_size(extent_list, bookmark_id)
    #extent 0 - file_size, 1 - file count
    report['file_size'] = extent[0]
    report['file_count'] = extent[1]

    return report

def get_file_size(extent_list, bookmark_id):

    '''
    extract the file size by matching the id with
    the corresponding row in bookmarks table
    returns a list with the total file size and total file count
    for the id that was passed. This function has the largest impact on performance.
    '''

    file_count = 0
    total_size = 0
    extent = []

    #the prefix for ids in the table is bf, not bk

    prefix = bookmark_id.replace('k', 'f')

    for i in range(len(extent_list)):
    
        if prefix in extent_list[i][0]:

            # within the table row the file size is stored as digits followed by
            # whitspace, followed by B for bytes. Ex: 100 B.

            table_info = extent_list[i][1].decode("utf-8")
            logical = re.findall(r'\d+\s[B]', table_info)
            
            # files that are not recognized do not return a logical size
            # and will cause errors unless they are ignored 

            if len(logical) == 0:

                pass

            else:
                file_size = int(logical[0].split(" ")[0])
                total_size += file_size
                file_count += 1
    
    extent.append(total_size)
    extent.append(file_count)
    
    return extent

def append_val_to_xml_list(extent, xml_list):

    '''
    an example dict appended would be 
    {'er_number': 'ER 10', 'er_name': 'Urban Bush Women, 2003-2011',
    'bookmark_id': 'bk156001', 'logical_size': 421128, 'file_count': 8}
    because of this transformation "ER" records have a dict
    as the third value. Series and subseries have a string value.
    '''

    for item in xml_list:
        bk_id = item[2]
        if bk_id == extent['bookmark_id']:
            item[2] = extent

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
    xml_list = make_list_from_xml(tree)
    print(time.perf_counter())
    print('Calculating extents for each file ...')
    xml_list = generate_report(tree, xml_list)
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