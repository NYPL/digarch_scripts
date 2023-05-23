import report_ftk_extents as rfe
import pytest
import json
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree


@pytest.fixture
def parsed_report():
    return etree.parse('fixtures/Report.xml')

def test_identify_all_ers(parsed_report):
    """Function should list every bookmark starting with ER"""
    ers = rfe.create_er_list(parsed_report)

    just_ers = [er[0].split('/')[-1].split(':')[0] for er in ers]

    for i in range(1, 12):
        assert f'ER {i}' in just_ers
    assert 'ER 23' in just_ers

def test_hierarchy_nests_down_correctly(parsed_report):
    """Function should include organization hierarchy.
    These are not great tests, but I'm not sure what the better strategy would be"""
    ers = rfe.create_er_list(parsed_report)
    just_titles = [er[0] for er in ers]

    assert 'Extents Test papers/Series 1/Subseries(1)/ER 1: Text, 2023' in just_titles
    assert 'Extents Test papers/Series 1/Subseries(1)/Subsubseries(2)/ER 2: File 15, 2023' in just_titles

def test_hierarchy_nests_empty_subseries(parsed_report):
    """Function should include organization hierarchy including empty levels"""
    ers = rfe.create_er_list(parsed_report)
    just_titles = [er[0] for er in ers]

    assert 'Extents Test papers/Series 1/Subseries(1)/Subsubseries(2)/Subsubsubseries(3)/Subsubsubsubseries(4)/ER 10: Folder 2, 2023' in just_titles

def test_hierarchy_nests_up_correctly(parsed_report):
    """Function should be able to step down in hierarchy"""
    ers = rfe.create_er_list(parsed_report)
    just_titles = [er[0] for er in ers]

    assert 'Extents Test papers/Series 1/Subseries(1)/Subsubseries(2) the second/ER 23: File 17, 2023' in just_titles
    assert 'Extents Test papers/Series 1/Subseries(1) the second/ER 4: File 18, 2023' in just_titles

def test_hierarchy_nests_reverse_order_bookmarks(parsed_report):
    """Function should parse bottom-up hierarchy"""
    ers = rfe.create_er_list(parsed_report)
    just_titles = [er[0] for er in ers]

    assert 'Extents Test papers/Series 2/ER 9: File 20,2023' in just_titles
    assert 'Extents Test papers/Series 2/Subseries(1) of Series 2/ER 8: File 2, 2023' in just_titles
    assert 'Extents Test papers/Series 2/Subseries(1) of Series 2/Subsubseries(2) of Series 2/ER 7: File 19, 2023' in just_titles

def test_er_outside_of_series(parsed_report):
    """Function should include capture ERs even if they're not in a series"""
    ers = rfe.create_er_list(parsed_report)
    just_titles = [er[0] for er in ers]

    assert 'Extents Test papers/ER 10: File 21,2023' in just_titles

def test_correct_report_many_files(parsed_report):
    """Test if file count and byte count is completed correctly"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    er_with_many_files = [['ER 1', 'bk6001']]
    extents = rfe.add_extents_to_ers(er_with_many_files, bookmark_tables)

    # bytes
    assert extents[0][1] == 110
    # files
    assert extents[0][2] == 7

def test_correct_report_on_er_with_folder_bookmarked(parsed_report):
    """Test if file count and byte count is completed correctly
    when bookmark includes a folder that is bookmarked"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    er_with_folder = [['ER 10', 'bk12001']]
    extents = rfe.add_extents_to_ers(er_with_folder, bookmark_tables)

    assert False

def test_correct_report_on_er_with_folder_not_bookmarked(parsed_report):
    """Test if file count and byte count is completed correctly
    when bookmark includes a folder that isn't bookmarked"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    er_with_folder = [['ER 3', 'bk11001']]
    extents = rfe.add_extents_to_ers(er_with_folder, bookmark_tables)

    assert False

def test_correct_report_1_file(parsed_report):
    """Test if file count and byte count is completed correctly for one file"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    er_with_one_file = [['ER 2', 'bk9001']]
    extents = rfe.add_extents_to_ers(er_with_one_file, bookmark_tables)

    assert False

def test_warn_on_no_files_in_er(parsed_report, caplog):
    """Test if warning is logged for empty bookmarks and ER is omitted from report"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    er_with_no_files = [['ER 5: No Files, 2023', 'bk27001']]

    extents = rfe.add_extents_to_ers(er_with_no_files, bookmark_tables)

    assert extents == []

    log_msg = f'{er_with_no_files[0][0]} does not contain any files. It will be omitted from the report.'
    assert log_msg in caplog.text

def test_warn_on_a_no_byte_file_in_er(parsed_report):
    """Test if warning is logged for empty files in an ER"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    er_with_no_bytes = [['ER 6: Zero Length, 2023', 'bk28001']]
    # rfe.add_extents_to_ers(er_with_no_bytes, bookmark_tables)
    # log warning, script should continue running
    # 'ER xxx: Title contain zero byte files.'
    assert False

def test_warn_on_no_bytes_in_er(parsed_report):
    """Test if warning is logged for bookmarks with 0 bytes total and ER is omitted from report"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    er_with_no_bytes = [['ER 6: Zero Length, 2023', 'bk28001']]
    # rfe.add_extents_to_ers(er_with_no_bytes, bookmark_tables)
    # log warning, script should continue running
    # 'ER xxx: Title does not contain any bytes. It will be omitted from the report'
    assert False

def test_extract_collection_name_from_report(parsed_report):
    """Test if collection name is taken from XML"""
    coll_name = rfe.extract_collection_title(parsed_report)

    assert coll_name == 'Extents Test'

@pytest.fixture
def ers_with_extents_list(parsed_report):
    ers = rfe.create_er_list(parsed_report)
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)
    ers_with_extents = rfe.add_extents_to_ers(ers, bookmark_tables)

    return ers_with_extents

def test_json_objects_contains_expected_fields(ers_with_extents_list):
    """Test if final report aligns with expectations for ASpace import"""

    assert False

def test_skipped_ER_number_behavior(parsed_report):
    ers = rfe.create_er_list(parsed_report)

    # what should script do if an ER number is skipped?
    assert False

def test_repeated_ER_number_behavior(parsed_report):
    ers = rfe.create_er_list(parsed_report)

    # what should script do if an ER number is skipped?
    assert False

@pytest.fixture
def expected_json():
    with open('fixtures/report.json') as f:
        report = json.load(f)
    return report

def test_create_correct_json(ers_with_extents_list, expected_json):
    """Test that final report matches total expectations"""
    dct = {'title': 'coll', 'children': []}
    for er in ers_with_extents_list:
        dct = rfe.create_report(er, dct)

    assert dct == expected_json
