import report_hdd_extents as rhe
import pytest
import shutil
import re
import pathlib
import json


@pytest.fixture(scope='session')
def arranged_collection(tmp_path_factory):
    path = tmp_path_factory.getbasetemp().joinpath('hdd')
    shutil.copytree('fixtures/', path)
    return path

def test_identify_all_ers(arranged_collection):
    """Function should list every folder starting with ER"""
    ers = rhe.get_ers(arranged_collection)
    print(ers)
    just_ers = [re.search(r'ER\s\d+', er[0]).group() for er in ers]
  
    for i in range(1, 4):
        assert f'ER {i}' in just_ers
    for i in range(7, 12):
        assert f'ER {i}' in just_ers
    assert 'ER 23' in just_ers

def test_hierarchy_nests_down_correctly(arranged_collection):
    """Function should include organization hierarchy.
    These are not great tests, but I'm not sure what the better strategy would be"""
    ers = rhe.get_ers(arranged_collection)
    just_titles = [er[0] for er in ers]
    print(just_titles)

    assert 'M12345 Extents Test/Series 1/Subseries(1)/ER 1 Text, 2023' in just_titles
    assert 'M12345 Extents Test/Series 1/Subseries(1)/Subsubseries(2)/ER 2 File 15, 2023' in just_titles

def test_hierarchy_nests_empty_subseries(arranged_collection):
    """Function should include organization hierarchy including empty levels"""
    ers = rhe.get_ers(arranged_collection)
    just_titles = [er[0] for er in ers]

    assert 'M12345 Extents Test/Series 1/Subseries(1)/Subsubseries(2)/Subsubsubseries(3)/Subsubsubsubseries(4)/ER 10 Folder 2, 2023' in just_titles

def test_er_outside_of_series(arranged_collection):
    """Function should include capture ERs even if they're not in a series"""
    ers = rhe.get_ers(arranged_collection)
    just_titles = [er[0] for er in ers]

    assert 'M12345 Extents Test/ER 10 File 21,2023' in just_titles

def test_correct_report_many_files(arranged_collection):
    """Test if file count and byte count is completed correctly"""
    ers = rhe.get_ers(arranged_collection)

    er_with_many_files = 'ER 1 Text, 2023'
    for er in ers:
        if er[3] == er_with_many_files:
            bytes, files = er[1:3]
            break
    
    # bytes
    assert bytes == 110
    # files
    assert files == 7

def test_correct_report_on_er_with_folder_included(arranged_collection):
    """Test if file count and byte count is completed correctly
    when bookmark includes a folder that is bookmarked"""
    ers = rhe.get_ers(arranged_collection)

    er_with_folder = 'ER 10 Folder 2, 2023'
    for er in ers:
        if er[3] == er_with_folder:
            bytes, files = er[1:3]
            break
    # bytes
    assert bytes == 80
    # files
    assert files == 5


def test_correct_report_1_file(arranged_collection):
    """Test if file count and byte count is completed correctly for one file"""
    ers = rhe.get_ers(arranged_collection)

    er_with_one_file = 'ER 2 File 15, 2023'
    for er in ers:
        if er[3] == er_with_one_file:
            bytes, files = er[1:3]
            break
    # bytes
    assert bytes == 16
    # files
    assert files == 1


def test_warn_on_no_files_in_er(arranged_collection, caplog):
    """Test if warning is logged for empty bookmarks and ER is omitted from report"""
    ers = rhe.get_ers(arranged_collection)

    er_with_no_files = 'ER 5 No Files, 2023'

    log_msg = f'{er_with_no_files} does not contain any files. It will be omitted from the report.'
    assert log_msg in caplog.text

def test_warn_on_a_no_byte_file_in_er(arranged_collection, caplog):
    """Test if warning is logged for empty files in an ER"""
    ers = rhe.get_ers(arranged_collection)

    er_with_no_bytes = 'ER 6 Zero Length, 2023'
    # rfe.add_extents_to_ers(er_with_no_bytes, bookmark_tables)
    # log warning, script should continue running
    # 'ER xxx: Title contain zero byte files.'
    log_msg = f'{er_with_no_bytes} contains the following 0-byte file: file00.txt. Review this file with the processing archivist.'
    assert log_msg in caplog.text

def test_warn_on_no_bytes_in_er(arranged_collection, caplog):
    """Test if warning is logged for bookmarks with 0 bytes total and ER is omitted from report"""
    ers = rhe.get_ers(arranged_collection)

    er_with_no_bytes = 'ER 6 Zero Length, 2023'
    # rfe.add_extents_to_ers(er_with_no_bytes, bookmark_tables)
    # log warning, script should continue running
    # 'ER xxx: Title does not contain any bytes. It will be omitted from the report'
    log_msg = f'{er_with_no_bytes} contains no files with bytes. This ER is omitted from report. Review this ER with the processing archivist.'
    assert log_msg in caplog.text

def test_extract_collection_name_from_report(arranged_collection):
    """Test if collection name is taken from XML"""
    coll_name = rhe.extract_collection_title(arranged_collection)

    assert coll_name == 'M12345 Extents Test'
'''
def test_skipped_ER_number_behavior(arranged_collection, caplog):
    ers = rhe.get_ers(arranged_collection)
    rhe.audit_ers(arranged_collection)

    # log warning, but continue operation
    log_msg = (
        'Numbers used for ERs are not sequential.'
        'Numbers found: 1-12, 23'
        'You may wish to check with the processing archivist'
    )
    assert log_msg in caplog.text

def test_repeated_ER_number_behavior(arranged_collection, caplog):
    ers = rhe.get_ers(arranged_collection)

    # log error, quit script
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        rhe.audit_ers(ers)

    assert pytest_wrapped_e.type == SystemExit

    repeated_ers = [
        'ER 1 ...',
        'ER 1 ...'
    ]
    log_msg = (
        'ER numbering should be unique.'
        f'These ERs reuse the same number: {repeated_ers}'
        'You may wish to check with the processing archivist'
    )

    assert log_msg in caplog.text

@pytest.fixture
def extracted_ers(arranged_collection):
    return rhe.get_ers(arranged_collection)

def test_json_objects_contains_expected_fields(extracted_ers):
    """Test if final report aligns with expectations for ASpace import"""
    rhe.create_report(extracted_ers)

    assert False


@pytest.fixture
def expected_json():
    with open('fixtures/report.json') as f:
        report = json.load(f)
    return report

def test_create_correct_json(extracted_ers, expected_json):
    """Test that final report matches total expectations"""
    dct = {'title': 'coll', 'children': []}
    dct = rhe.create_report(extracted_ers, dct)

    assert dct == expected_json
'''
