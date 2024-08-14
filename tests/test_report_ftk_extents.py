import src.digarch_scripts.report.report_ftk_extents as rfe
import pytest
import json
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree


def test_parse_xml():
    """Function should return etree object"""
    tree = rfe.parse_xml('tests/fixtures/report/Report.xml')

    assert type(tree) is etree._ElementTree

def test_quit_on_invalid_xml(tmp_path):
    """Entire script should quit if XML can't be parse"""
    bad_xml = tmp_path / "bad.xml"
    # <a>\x07</a> write xml with ASCII control character
    with open(bad_xml, 'wb') as f:
        f.write(b"\x3c\x61\x3e\x07\x3c\x2f\x61\x3e")

    msg = "FTK report cannot be parsed. Edit the unreadable characters in the report with a text editor."
    with pytest.raises(SystemExit, match=msg):
        rfe.parse_xml(bad_xml)

@pytest.fixture
def parsed_report():
    return rfe.parse_xml('tests/fixtures/report/Report.xml')

@pytest.fixture
def components(parsed_report):
    return rfe.create_component_list(parsed_report)

def test_identify_all_components(components):
    """Function should list every bookmark starting with ER and DI"""
    just_components = [component[0][-1].split(':')[0] for component in components]

    for i in range(1, 12):
        assert f'ER {i}' in just_components
    assert 'ER 23' in just_components

def test_hierarchy_nests_down_correctly(components):
    """Function should include organization hierarchy.
    These are not great tests, but I'm not sure what the better strategy would be"""
    just_titles = [component[0] for component in components]

    assert ['Extents Test papers', 'Series 1', 'Subseries(1)', 'ER 1: Text, 2023'] in just_titles
    assert ['Extents Test papers', 'Series 1', 'Subseries(1)', 'Subsubseries(2)', 'ER 2: File 15, 2023'] in just_titles

def test_hierarchy_nests_empty_subseries(components):
    """Function should include organization hierarchy including empty levels"""
    just_titles = [component[0] for component in components]

    assert ['Extents Test papers', 'Series 1', 'Subseries(1)', 'Subsubseries(2)', 'Subsubsubseries(3)', 'Subsubsubsubseries(4)', 'ER 10: Folder 2, 2023'] in just_titles

def test_hierarchy_nests_up_correctly(components):
    """Function should be able to step down in hierarchy"""
    just_titles = [component[0] for component in components]

    assert ['Extents Test papers', 'Series 1', 'Subseries(1)', 'Subsubseries(2) the second', 'ER 23: File 17, 2023'] in just_titles
    assert ['Extents Test papers', 'Series 1', 'Subseries(1) the second', 'ER 4: File 18, 2023'] in just_titles

def test_hierarchy_nests_reverse_order_bookmarks(components):
    """Function should parse bottom-up hierarchy"""
    just_titles = [component[0] for component in components]

    assert ['Extents Test papers', 'Series 2', 'ER 9: File 20,2023'] in just_titles
    assert ['Extents Test papers', 'Series 2', 'Subseries(1) of Series 2', 'ER 8: File 2, 2023'] in just_titles
    assert ['Extents Test papers', 'Series 2', 'Subseries(1) of Series 2', 'Subsubseries(2) of Series 2', 'ER 7: File 19, 2023'] in just_titles

def test_component_outside_of_series(components):
    """Function should include capture components even if they're not in a series"""
    just_titles = [component[0] for component in components]

    assert ['Extents Test papers', 'ER 10: File 21,2023'] in just_titles

def test_correct_report_many_files(parsed_report):
    """Test if file count and byte count is completed correctly"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    component_with_many_files = [['ER 1', 'bk6001']]
    extents = rfe.add_extents_to_components(component_with_many_files, bookmark_tables)

    # bytes
    assert extents[0][1] == 110
    # files
    assert extents[0][2] == 7

def test_correct_report_on_component_with_folder_bookmarked(parsed_report):
    """Test if file count and byte count is completed correctly
    when bookmark includes a folder that is bookmarked"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    component_with_folder = [['ER 10', 'bk12001']]
    extents = rfe.add_extents_to_components(component_with_folder, bookmark_tables)

    # bytes
    assert extents[0][1] == 80
    # files
    assert extents[0][2] == 5

def test_correct_report_on_disk_image(parsed_report):
    """Test if file count and byte count is completed correctly
    when bookmark includes a folder that is bookmarked"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    component_with_folder = [['DI 1', 'bk31001']]
    extents = rfe.add_extents_to_components(component_with_folder, bookmark_tables)

    # bytes
    assert extents[0][1] == 7168
    # files
    assert extents[0][2] == 1

def test_correct_report_on_component_with_folder_not_bookmarked(parsed_report):
    """Test if file count and byte count is completed correctly
    when bookmark includes a folder that isn't bookmarked"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    component_with_folder = [['ER 3', 'bk11001']]
    extents = rfe.add_extents_to_components(component_with_folder, bookmark_tables)

    # bytes
    assert extents[0][1] == 60
    # files
    assert extents[0][2] == 5

def test_correct_report_1_file(parsed_report):
    """Test if file count and byte count is completed correctly for one file"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    component_with_one_file = [['ER 2', 'bk9001']]
    extents = rfe.add_extents_to_components(component_with_one_file, bookmark_tables)

    # bytes
    assert extents[0][1] == 16
    # files
    assert extents[0][2] == 1

def test_warn_on_no_files_in_er(parsed_report, caplog):
    """Test if warning is logged for empty bookmarks and component is omitted from report"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    component_with_no_files = [[['hier', 'archy', 'list'], 'bk27001', 'ER 5: No Files, 2023']]

    extents = rfe.add_extents_to_components(component_with_no_files, bookmark_tables)

    assert extents == []

    log_msg = f'{component_with_no_files[0][-1]} does not contain any files. It will be omitted from the report.'
    assert log_msg in caplog.text

def test_warn_on_a_no_byte_file_in_er(parsed_report, caplog):
    """Test if warning is logged for empty files in an component"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    component_with_no_bytes = [[['hier', 'archy', 'list'], 'bk28001', 'ER 6: Zero Length, 2023']]
    rfe.add_extents_to_components(component_with_no_bytes, bookmark_tables)
    log_msg = f'{component_with_no_bytes[0][-1]} contains the following 0-byte file: file00.txt. Review this file with the processing archivist.'
    assert log_msg in caplog.text

def test_warn_on_no_bytes_in_er(parsed_report, caplog):
    """Test if warning is logged for bookmarks with 0 bytes total and component is omitted from report"""
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)

    component_with_no_bytes = [[['hier', 'archy', 'list'], 'bk28001', 'ER 6: Zero Length, 2023']]
    extents = rfe.add_extents_to_components(component_with_no_bytes, bookmark_tables)

    assert extents == []

    log_msg = f'{component_with_no_bytes[0][-1]} contains no files with bytes. This component is omitted from report. Review this component with the processing archivist.'
    assert log_msg in caplog.text


def test_extract_collection_name_from_report(parsed_report):
    """Test if collection name is taken from XML"""
    coll_name = rfe.extract_collection_title(parsed_report)

    assert coll_name == 'M12345 Extents Test'

@pytest.fixture
def components_with_extents_list(parsed_report):
    components = rfe.create_component_list(parsed_report)
    bookmark_tables = rfe.transform_bookmark_tables(parsed_report)
    components_with_extents = rfe.add_extents_to_components(components, bookmark_tables)

    return components_with_extents

def test_json_objects_contains_expected_fields(components_with_extents_list):
    """Test if final report aligns with expectations for ASpace import"""

    full_dict = {'title': 'slug', 'children': []}
    for component in components_with_extents_list:
        rfe.create_report(component, full_dict)

    def recursive_validator(component_dict):
        for key, value in component_dict.items():
            if key == 'title':
                assert type(value) is str
            elif key == 'children':
                assert type(value) is list
                for child in value:
                    recursive_validator(child)
            elif key == 'er_number':
                assert type(value) is str
            elif key == 'er_name':
                assert type(value) is str
            elif key == 'file_size':
                assert type(value) is int
            elif key == 'file_count':
                assert type(value) is int
            else:
                assert False

    recursive_validator(full_dict)


def test_skipped_number_behavior(parsed_report, caplog):
    """Test if script flags when component numbering is not sequential"""
    components = rfe.create_component_list(parsed_report)

    for i in range(13, 23):
        assert f'Collection ER component range is numbered 1 to 23. {i} is skipped. Review the bookmarks with the processing archivist' in caplog.text


def test_component_missing_number_behavior(components, caplog):
    """Test if script flags when component number is reused"""
    components[0][2] = "ER ?: File 21,2023"

    rfe.audit_components(components)

    log_msg = f'Component is missing a number: ER ?: File 21,2023. Review the bookmarks with the processing archivist'
    assert log_msg in caplog.text


def test_repeated_component_number_behavior(components, caplog):
    """Test if script flags when component number is reused"""
    rfe.audit_components(components)

    log_msg = f'ER 10 is used multiple times: ER 10: File 21,2023, ER 10: Folder 2, 2023. Review the bookmarks with the processing archivist'

    assert log_msg in caplog.text


@pytest.fixture
def expected_json():
    with open('tests/fixtures/report/report.json') as f:
        report = json.load(f)
    return report

def test_create_correct_json(components_with_extents_list, expected_json):
    """Test that final report matches total expectations"""
    dct = {'title': 'coll', 'children': []}
    for component in components_with_extents_list:
        dct = rfe.create_report(component, dct)

    assert dct == expected_json
