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


def generate_report(tree, file_tableids):
    report = []

    for bookmark in tree.xpath(
        '/fo:root/fo:page-sequence/fo:flow/fo:block[@id]',
        namespaces=FO_NAMESPACE
    ):
        bookmark_id = bookmark.get('id')

    if 'bk' in bookmark_id:
        name = tree.xpath(
            f'/fo:root/fo:page-sequence/fo:flow/fo:block[@id="{bookmark_id}"]/text()',
            namespaces=FO_NAMESPACE
        )
        table_id = bookmark_id.replace('k','f')
        logical_size = 0
        file_count = 0

        for x in file_tableids:
            if table_id in x:
                table_cell = tree.xpath(
                    f'/fo:root/fo:page-sequence/fo:flow/fo:table[@id="{x}"]/fo:table-body/fo:table-row/fo:table-cell/fo:block/text()',
                    namespaces=FO_NAMESPACE
                )
                new_file = int(table_cell[2].replace(" B",""))
                logical_size += new_file
                file_count += 1

        if "Bookmark" in name[0]:
            report[bookmark_id] = [
                name[0].replace("Bookmark: ",""),
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
