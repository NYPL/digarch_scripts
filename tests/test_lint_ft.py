from pathlib import Path

import pytest

import src.ipres_package_cloud.lint_ft as lint_ft

# Unit tests
# Argument tests
def test_package_argument(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "sys.argv",
        ["script", "--package", str(tmp_path)],
    )

    args = lint_ft.parse_args()

    assert tmp_path in args.packages


def test_directory_argument(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    child_dir = tmp_path / "child"
    child_dir.mkdir()

    monkeypatch.setattr(
        "sys.argv",
        ["script", "--directory", str(tmp_path)],
    )

    args = lint_ft.parse_args()

    assert child_dir in args.packages

# linting tests
@pytest.fixture
def good_package(tmp_path: Path):
    pkg = tmp_path.joinpath("ACQ_1234_123456")
    f_object_data = pkg / "objects" / "data"
    f_object_data.mkdir(parents=True)

    bag_files = ["bag-info.txt", "bagit.txt",
                 "manifest-md5.txt", "tagmanifest-md5.txt"]
    for f in bag_files:
        filepath = pkg / "objects" / f
        filepath.touch()
        filepath.write_bytes(b"some bytes for file")

    obj_data_file = f_object_data / "file_1.txt"
    obj_data_file.touch()
    obj_data_file.write_bytes(b"some bytes for file")

    obj_data_folder = f_object_data / "folder1"
    obj_data_folder.mkdir(parents=True, exist_ok=True)

    obj_data_folder_file = obj_data_folder / "fileinfolder.txt"
    obj_data_folder_file.touch()
    obj_data_folder_file.write_bytes(b"some bytes for file")

    f_metadata = pkg.joinpath("metadata")
    f_metadata.mkdir()

    metadata_filepath = f_metadata.joinpath("rclone.log")
    metadata_filepath.touch()
    metadata_filepath.write_bytes(b"some bytes for metadata")

    return pkg

def test_top_folder_valid_name(good_package):
    """Top level folder name has to conform to ACQ_####_######"""
    result = lint_ft.package_has_valid_name(good_package)

    assert result


def test_top_folder_invalid_name(good_package):
    """Test that package fails function when the top level folder name
    does not conform to the naming convention, ACQ_####_######"""
    bad_package = good_package
    bad_package = bad_package.rename(bad_package.parent / "ACQ_123_45")

    result = lint_ft.package_has_valid_name(bad_package)

    assert not result

def test_package_has_two_subfolders(good_package):
    """Second level folders must be two"""
    result = lint_ft.package_has_two_subfolders(good_package)

    assert result

def test_package_does_not_have_two_subfolders(good_package):
    """Test that package fails function when second level folders are
    not the correct number, i.e. 2"""
    bad_package = good_package
    new_folder = bad_package / "anotherfolder"
    new_folder.mkdir()

    result = lint_ft.package_has_two_subfolders(bad_package)

    assert not result

def test_sec_level_folder_valid_names(good_package):
    """Second level folders must only have objects and metadata folder"""
    result = lint_ft.package_has_valid_subfolder_names(good_package)

    assert result


def test_sec_level_folder_invalid_names(good_package):
    """Test that package fails function when second level folders are not named
    objects and metadata"""
    bad_package = good_package
    objects_path = bad_package / "objects"
    objects_path.rename(bad_package / "obj")

    result = lint_ft.package_has_valid_subfolder_names(bad_package)

    assert not result

def test_package_has_no_hidden_file(good_package):
    """The package should not have any hidden file"""
    result = lint_ft.package_has_no_hidden_file(good_package)

    assert result

def test_package_has_hidden_file(good_package):
    """Test that package fails function when there is any hidden file"""
    bad_package = good_package
    folder = bad_package / "objects" / "data" / "folder2"
    folder.mkdir(parents=True, exist_ok=True)
    hidden_file = folder.joinpath(".DS_Store")
    hidden_file.touch()

    result = lint_ft.package_has_no_hidden_file(bad_package)

    assert not result

def test_package_has_no_zero_bytes_file(good_package):
    """The package should not have any zero bytes file"""
    result = lint_ft.package_has_no_zero_bytes_file(good_package)

    assert result

def test_package_has_zero_bytes_file(good_package):
    """Test that package fails function when there is any zero bytes file"""
    bad_package = good_package
    zero_bytes = bad_package / "objects" / "data" / "folder1" / "zerobytes.txt"
    zero_bytes.touch()

    result = lint_ft.package_has_no_zero_bytes_file(bad_package)

    assert not result

def test_metadata_folder_is_flat(good_package):
    """The metadata folder should not have folder structure"""
    result = lint_ft.metadata_folder_is_flat(good_package)

    assert result


def test_metadata_folder_has_random_folder(good_package):
    """Test that package fails function when the second-level metadata folder
    has any folder in it"""
    bad_package = good_package
    random_dir = bad_package / "metadata" / "random_dir"
    random_dir.mkdir()

    result = lint_ft.metadata_folder_is_flat(bad_package)

    assert not result

def test_metadata_folder_has_files(good_package):
    """The metadata folder should have one or more file"""
    result = lint_ft.metadata_folder_has_files(good_package)

    assert result

def test_metadata_folder_empty(good_package):
    """Test that package fails function when the metadata does
    not have any files"""
    bad_package = good_package
    md_file = bad_package / "metadata" / "rclone.log"
    md_file.unlink()

    result = lint_ft.metadata_folder_has_files(bad_package)

    assert not result

def test_metadata_has_correct_naming_convention(good_package):
    """The metadata file name should be in the accepted list"""
    result = lint_ft.metadata_has_correct_naming_convention(good_package)

    assert result

def test_metadata_has_incorrect_naming_convention(good_package):
    """Test that package fails function when metadata file(s) has
    incorrect naming conventions"""
    bad_package = good_package
    incorrect_md_file = bad_package / "metadata" / "random_md.txt"
    incorrect_md_file.touch()

    result = lint_ft.metadata_has_correct_naming_convention(bad_package)

    assert not result

def test_objects_folder_correct_structure(good_package):
    """objects folder should have a data folder, which includes four files:
    bag-info.txt, bagit.txt, manifest-md5.txt and tagmanifest-md5.txt"""
    result = lint_ft.objects_folder_correct_structure(good_package)

    assert result

def test_objects_folder_incorrect_structure(good_package):
    """Test that package fails function if it does not have the data folder,
    or missing any of the four files: bag-info.txt, bagit.txt, manifest-md5.txt
    and tagmanifest-md5.txt"""
    bad_package = good_package
    baginfo_fp = bad_package / "objects" / "bag-info.txt"
    baginfo_fp.unlink()

    result = lint_ft.objects_folder_correct_structure(bad_package)

    assert not result

def test_objects_folder_has_no_empty_folder(good_package):
    """The objects folder should not have any empty folders"""
    result = lint_ft.objects_folder_has_no_empty_folder(good_package)

    assert result

def test_objects_folder_has_empty_folder(good_package):
    """Test that package fails function if its objects folder has empty folder(s)"""
    bad_package = good_package

    file_in_folder = bad_package / "objects" / "data" / "folder1" / "fileinfolder.txt"
    file_in_folder.unlink()

    result = lint_ft.objects_folder_has_no_empty_folder(bad_package)

    assert not result

def test_valid_package(good_package):
    """Test that package returns 'valid' when all tests are passed"""
    result = lint_ft.lint_package(good_package)

    assert result == "valid"

def test_invalid_package(good_package):
    """Test that package returns 'invalid' when failing some tests"""
    bad_package = good_package

    bag_folder = bad_package / "metadata" / "submissionDocumentation"
    bag_folder.mkdir()

    result = lint_ft.lint_package(bad_package)

    assert result == "invalid"

def test_unclear_package(good_package):
    """Test that package returns 'needs review' when failing some tests"""
    bad_package = good_package
    md_fp = bad_package / "metadata" / "rclone.log"
    md_fp.unlink()

    result = lint_ft.lint_package(bad_package)

    assert result == "needs review"
