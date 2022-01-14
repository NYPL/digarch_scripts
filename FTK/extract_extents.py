import csv
import pandas as pd
from lxml import etree


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


def get_file_size(file_tableid):
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
        bookmark_id = bookmark.get('id')
        bookmark_name = tree.xpath(
            f'/fo:root/fo:page-sequence/fo:flow/fo:block[@id="{bookmark_id}"]/text()',
            namespaces=FO_NAMESPACE
        )
        file_tableid_prefix = bookmark_id.replace('k','f')
        logical_size = 0
        file_count = 0

        for file_tableid in file_tableids:
            if file_tableid_prefix in file_tableid:
                logical_size += get_file_size(file_tableid)
                file_count += 1


        if "Bookmark" in bookmark_name[0]:
            report[bookmark_id] = [
                bookmark_name[0].replace("Bookmark: ",""),
                file_count,
                logical_size
            ]

    return report

def make_csv(report):
    df = pd.DataFrame(report)
    df = df.transpose()
    df.rename(columns={0:"Bookmark Name", 1:"File Count", 2:"Size"})
    df.to_csv('ftk_test.csv')


def main():
    tree = etree.parse('/ER3-Report.xml')
    file_tableids = extract_file_tableids(tree)
    report = generate_report(tree, file_tableids)
    make_csv(report)


if __name__ == '__main__':
    main()
