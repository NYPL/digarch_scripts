import csv
import pandas as pd
from lxml import etree
import json
import argparse


FO_NAMESPACE = {'fo': 'http://www.w3.org/1999/XSL/Format'}

def extract_file_tableids(tree):
    '''
    every bookmarked file is represented by a table with a unique id,
    bf####_####
    the first #### is a shared id for all files in the bookmark
    '''

    file_tableids = []

    bf_table_ids = tree.xpath(
        '/fo:root/fo:page-sequence/fo:flow/fo:table[@id]',
        namespaces=FO_NAMESPACE
    )

    for item in bf_table_ids:
        if "bf" in item.get('id'):
            file_tableids.append(item.get('id'))

    return file_tableids


def get_file_size(tree, file_tableid):
    '''
    extract the file size based on its location in the file table
    '''

    table_cell = tree.xpath(
        f'/fo:root/fo:page-sequence/fo:flow/fo:table[@id="{file_tableid}"]'\
        '/fo:table-body/fo:table-row/fo:table-cell/fo:block/text()',
        namespaces=FO_NAMESPACE
    )
    file_size = int(table_cell[2].replace(" B",""))

    return file_size


def get_er_report(tree, bookmark, file_tableids):
    '''
    extract er number, er name, byte count, and file count
    '''

    report = {}

    er_components = bookmark.text.replace('Bookmark: ', '').split(':')
    report['er_number'] = er_components[0]
    report['er_name'] = er_components[1].strip()

    bookmark_id = bookmark.get('id')
    file_tableid_prefix = bookmark_id.replace('k','f')
    report['logical_size'] = 0
    report['file_count'] = 0

    for file_tableid in file_tableids:
        if file_tableid_prefix in file_tableid:
            report['logical_size'] += get_file_size(tree, file_tableid)
            report['file_count'] += 1

    return report


def generate_report(tree, file_tableids):
    '''
    generate a list of all bookmark ids and add up file info
    '''
    report = {}

    bookmarks = tree.xpath(
        '/fo:root/fo:page-sequence[@master-reference="bookmarksPage"]/fo:flow/'\
        'fo:block[starts-with(@id, "bk")]',
        namespaces=FO_NAMESPACE
    )

    for bookmark in bookmarks:
        if 'ER' in bookmark.text:
            report[f'{bookmark.text}'] = get_er_report(tree, bookmark, file_tableids)
        else:
            continue


    return report


def make_csv(report):
    df = pd.DataFrame(report)
    df = df.transpose()
    df.rename(columns={0:'ER Number', 1: 'ER Name', 2:'File Count', 3:'Size'})
    df.to_csv('ftk_test.csv')


def make_json(report):
    with open('ftk_test.json', 'w') as file:
        json.dump(report, file)


def main():
    parser = argparse.ArgumentParser(description='Create a CSV report from XML')
    parser.add_argument("echo", help="echo string")
    args = parser.parse_args()
    print(args.echo)
    #tree = etree.parse('ER3-Report.xml')
    #file_tableids = extract_file_tableids(tree)
    #report = generate_report(tree, file_tableids)
    #make_csv(report)
    #make_json(report)

if __name__ == '__main__':
    main()
