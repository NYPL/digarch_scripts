import json
import pathlib
import re
import shutil

import pytest

import src.digarch_scripts.report.report_hdd_extents as rhe


@pytest.fixture()
def arranged_collection(tmp_path: pathlib.Path):
    path = tmp_path.joinpath("hdd")
    shutil.copytree("tests/fixtures/report", path)
    return path


def test_identify_all_ers(arranged_collection):
    """Function should list every folder starting with ER"""
    ers = rhe.get_ers(arranged_collection)
    print(ers)
    just_ers = [re.search(r"ER\s\d+", er[0]).group() for er in ers]

    for i in range(1, 4):
        assert f"ER {i}" in just_ers
    for i in range(7, 12):
        assert f"ER {i}" in just_ers
    assert "ER 23" in just_ers


def test_hierarchy_nests_down_correctly(arranged_collection):
    """Function should include organization hierarchy.
    These are not great tests, but I'm not sure what the better strategy would be"""
    ers = rhe.get_ers(arranged_collection)
    just_titles = [er[0] for er in ers]
    print(just_titles)

    assert "M12345_FAcomponents/Series 1/Subseries(1)/ER 1 Text, 2023" in just_titles
    assert (
        "M12345_FAcomponents/Series 1/Subseries(1)/Subsubseries(2)/ER 2 File 15, 2023"
        in just_titles
    )


def test_hierarchy_nests_empty_subseries(arranged_collection):
    """Function should include organization hierarchy including empty levels"""
    ers = rhe.get_ers(arranged_collection)
    just_titles = [er[0] for er in ers]

    assert (
        "M12345_FAcomponents/Series 1/Subseries(1)/Subsubseries(2)/Subsubsubseries(3)"
        "/Subsubsubsubseries(4)/ER 10 Folder 2, 2023"
        in just_titles
    )


def test_er_outside_of_series(arranged_collection):
    """Function should include capture ERs even if they're not in a series"""
    ers = rhe.get_ers(arranged_collection)
    just_titles = [er[0] for er in ers]

    assert "M12345_FAcomponents/ER 10 File 21,2023" in just_titles


def test_correct_report_many_files(arranged_collection):
    """Test if file count and byte count is completed correctly"""
    ers = rhe.get_ers(arranged_collection)

    er_with_many_files = "ER 1 Text, 2023"
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

    er_with_folder = "ER 10 Folder 2, 2023"
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

    er_with_one_file = "ER 2 File 15, 2023"
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

    er_with_no_files = "ER 5 No Files, 2023"

    log_msg = (
        f"{er_with_no_files} does not contain any files. It will be omitted from "
        "the report."
    )
    assert log_msg in caplog.text


def test_warn_on_a_no_byte_file_in_er(arranged_collection, caplog):
    """Test if warning is logged for empty files in an ER"""
    ers = rhe.get_ers(arranged_collection)

    er_with_no_bytes = "ER 6 Zero Length, 2023"
    # rfe.add_extents_to_ers(er_with_no_bytes, bookmark_tables)
    # log warning, script should continue running
    # 'ER xxx: Title contain zero byte files.'
    log_msg = f"{er_with_no_bytes} contains the following 0-byte file: file00.txt. "
    "Review this file with the processing archivist."
    assert log_msg in caplog.text


def test_warn_on_no_bytes_in_er(arranged_collection, caplog):
    """Test if warning is logged for bookmarks with 0 bytes total and ER is omitted
    from report"""

    ers = rhe.get_ers(arranged_collection)

    er_with_no_bytes = "ER 6 Zero Length, 2023"
    # rfe.add_extents_to_ers(er_with_no_bytes, bookmark_tables)
    # log warning, script should continue running
    # 'ER xxx: Title does not contain any bytes. It will be omitted from the report'
    log_msg = f"{er_with_no_bytes} contains no files with bytes. This ER is omitted "
    "from report. Review this ER with the processing archivist."
    assert log_msg in caplog.text


def test_warn_on_no_objects_in_er(arranged_collection, caplog):
    """Test if warning is logged for empty bookmarks and ER is omitted from report"""
    ers = rhe.get_ers(arranged_collection)

    er_with_no_files = "ER 13 No objects, 2023"

    log_msg = (f"{er_with_no_files} does not contain an object folder. It will be "
               "omitted from the report."
               )
    assert log_msg in caplog.text


def test_extract_collection_name(arranged_collection):
    """Test if collection name is taken from XML"""
    coll_name = rhe.extract_collection_title(arranged_collection)

    assert coll_name == "M12345_FAcomponents"


def test_warn_on_bad_collection_name(arranged_collection, caplog):
    """Test if collection name is taken from XML"""
    coll_name_folder = arranged_collection / "M12345_FAcomponents"
    coll_name_folder.rename(arranged_collection / "Test_Coll")
    rhe.extract_collection_title(arranged_collection)
    log_msg = ("Cannot find CollectionID_FAcomponents directory. Please use "
               "CollectionID_FAcomponents naming convention for the directory "
               "containing all ERs."
               )
    assert log_msg in caplog.text


def test_skipped_ER_number_behavior(arranged_collection, caplog):
    ers = rhe.get_ers(arranged_collection)
    rhe.audit_ers(ers)

    # log warning, but continue operation
    for number in range(13, 22):
        log_msg = (f"Collection uses ER 1 to ER 23. ER {number} is skipped. "
                   "Review the ERs with the processing archivist"
                   )
        assert log_msg in caplog.text


def test_repeated_ER_number_behavior(arranged_collection, caplog):
    ers = rhe.get_ers(arranged_collection)

    rhe.audit_ers(ers)

    log_msg = ("ER 10 is used multiple times"
               )

    assert log_msg in caplog.text


@pytest.fixture
def extracted_ers(arranged_collection):
    return rhe.get_ers(arranged_collection)


def test_json_objects_contains_expected_fields(extracted_ers):
    """Test if final report aligns with expectations for ASpace import"""

    full_dict = rhe.create_report(extracted_ers, {"title": "test", "children": []})

    def recursive_validator(er_dict):
        for key, value in er_dict.items():
            if key == "title":
                assert type(value) is str
            elif key == "children":
                assert type(value) is list
                for child in value:
                    recursive_validator(child)
            elif key == "er_number":
                assert type(value) is str
            elif key == "er_name":
                assert type(value) is str
            elif key == "file_size":
                assert type(value) is int
            elif key == "file_count":
                assert type(value) is int
            else:
                assert False

    recursive_validator(full_dict)


@pytest.fixture
def expected_json():
    with open("tests/fixtures/report/report.json") as f:
        raw = f.read()

    # adjust fixture for hdd conventions
    colons_removed = re.sub(r"(ER \d+):", r"\1", raw)
    report = json.loads(colons_removed)
    report["children"][0]["title"] = "M12345_FAcomponents"

    return report


def test_create_correct_json(extracted_ers, expected_json):
    """Test that final report matches total expectations"""
    dct = rhe.create_report(extracted_ers, {"title": "coll", "children": []})

    assert dct == expected_json
