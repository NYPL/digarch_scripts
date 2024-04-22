import os
import shutil
from pathlib import Path

import bagit
import pytest

import digarch_scripts.package.package_base as pb


@pytest.fixture
def transfer_files(tmp_path: Path, request):
    fixture_data = Path(request.module.__file__).parent / "fixtures" / "cloud"
    shutil.copytree(fixture_data, tmp_path, dirs_exist_ok=True)
    return tmp_path


@pytest.fixture
def payload(transfer_files):
    return transfer_files / "rclone_files"


@pytest.fixture
def md5_manifest(transfer_files):
    return transfer_files / "rclone.md5"


@pytest.fixture
def log(transfer_files):
    return transfer_files / "rclone.log"


@pytest.fixture
def id():
    return "ACQ_1234_123456"


def args(transfer_files):
    args = [
        transfer_files / "rclone.md5",
        transfer_files / "rclone.log",
        transfer_files,
    ]
    return args


def test_create_package_basedir_exc_on_readonly(tmp_path: Path, id: str):
    """Test that package folder maker reports permission error"""

    # make folder read-only
    os.chmod(tmp_path, 0o500)

    with pytest.raises(PermissionError) as exc:
        pb.create_base_dir(tmp_path, id)

    # change back to allow clean-up (might not be necessary)
    os.chmod(tmp_path, 0o777)
    assert f"{str(tmp_path)} is not writable" in str(exc.value)


def test_create_package_basedir(tmp_path: Path, id: str):
    """Test that package folder maker makes ACQ and Carrier folders"""

    base_dir = pb.create_base_dir(tmp_path, id)

    assert base_dir.name == id
    assert base_dir.parent.name == id[:-7]


def test_create_package_basedir_with_existing_acq_dir(tmp_path: Path, id: str):
    """Test that package folder maker respect existing ACQ folder"""

    (tmp_path / id[:-7]).mkdir()
    base_dir = pb.create_base_dir(tmp_path, id)

    assert base_dir.name == id
    assert base_dir.parent.name == id[:-7]


def test_error_on_existing_package_dir(tmp_path: Path, id: str):
    """Test that package folder maker errors if carrier folder exists"""

    base_dir = tmp_path / id[:-7] / id
    base_dir.mkdir(parents=True)

    with pytest.raises(FileExistsError) as exc:
        pb.create_base_dir(tmp_path, id)

    assert f"{base_dir} already exists. Make sure you are using the correct ID" in str(
        exc.value
    )


@pytest.fixture
def package_base_dir(tmp_path: Path, id: str):
    return pb.create_base_dir(tmp_path, id)


def test_move_metadata(package_base_dir: Path, log: Path):
    """Test that metadata folder and log file are moved successfully"""

    pb.move_metadata_file(log, package_base_dir)

    assert not log.exists()
    assert (package_base_dir / "metadata" / "rclone.log").exists()


def test_do_not_overwrite_metadata(package_base_dir: Path, log: Path):
    """Test that log file is not moved if a same name file exists in dest"""

    rclone_log = package_base_dir / "metadata" / log.name
    rclone_log.parent.mkdir()
    rclone_log.touch()

    with pytest.raises(FileExistsError) as exc:
        pb.move_metadata_file(log, package_base_dir)

    assert log.exists()
    assert f"{rclone_log} already exists in metadata folder. Not moving." in str(exc.value)


def test_move_multiple_metadata(package_base_dir: Path, log: Path, md5_manifest: Path):
    """Test that multiple files are moved successfully"""

    md_files = [log, md5_manifest]
    pb.move_metadata_files(md_files, package_base_dir)

    for md_file in md_files:
        assert not md_file.exists()
        assert (package_base_dir / "metadata" / md_file.name).exists()


def test_partial_halt_multiple_metadata(
    package_base_dir: Path, log: Path, md5_manifest: Path
):
    """Test that warning is issued for multiple move if a single metadata move fails"""

    rclone_log = package_base_dir / "metadata" / log.name
    rclone_log.parent.mkdir()
    rclone_log.touch()

    md_files = [log, md5_manifest]

    with pytest.raises(Warning) as exc:
        pb.move_metadata_files(md_files, package_base_dir)

    assert log.exists()
    assert (
        f"already exists in metadata folder. Not moving. One or more metadata files may have already been moved to new location"
        in str(exc.value)
    )


def test_move_payload(package_base_dir: Path, payload: Path):
    """Test that entirety of payload is moved and hierarchy is preserved"""

    source_contents = [file.relative_to(payload) for file in payload.rglob("*")]

    data_path = package_base_dir / "objects" / "data"
    pb.move_payload(payload, package_base_dir / "objects")

    # check that source is empty
    assert not any(payload.iterdir())

    assert data_path.exists()

    # compare contents of data and former source
    data_contents = [file.relative_to(data_path) for file in data_path.rglob("*")]
    assert source_contents == data_contents


def test_do_not_overwrite_payload(package_base_dir: Path, payload: Path):
    """Test that no payload file is moved if /data exists"""

    source_contents = [file for file in payload.rglob("*")]

    bag_payload = package_base_dir / "objects" / "data"
    bag_payload.mkdir(parents=True)

    with pytest.raises(FileExistsError) as exc:
        pb.move_payload(payload, package_base_dir / "objects")

    # check source has not changed
    assert source_contents == [file for file in payload.rglob("*")]
    assert f"{bag_payload} already exists. Not moving files." in str(exc.value)


@pytest.fixture
def bag_payload(package_base_dir: Path, payload: Path):
    pb.move_payload(payload, package_base_dir)
    bag_payload = package_base_dir / "data"

    return bag_payload


def test_convert_rclone_md5(bag_payload: Path, md5_manifest: Path):
    pb.convert_rclone_md5_to_bagit_manifest(md5_manifest, bag_payload.parent)
    bag_md5 = bag_payload.parent / "manifest-md5.txt"

    # Get path to correct payload in data
    # read md5 and extract filepaths
    with open(bag_md5) as m:
        md5_paths = [line.strip().split("  ")[-1] for line in m.readlines()]

    payload_files = [
        str(path.relative_to(bag_payload.parent)) for path in bag_payload.rglob("*")
    ]
    for a_file in md5_paths:
        assert a_file in payload_files


def test_create_bag(package_base_dir: Path, payload: Path, md5_manifest: Path):
    """Test that all tag files are created and rclone md5sums are correctly converted"""

    bag_path = package_base_dir / "objects"

    # might need further testing of the oxum and manifest converter functions
    pb.create_bag_in_objects(payload, md5_manifest, package_base_dir)

    assert bagit.Bag(str(bag_path)).validate(completeness_only=True)


def test_generate_valid_oxum(transfer_files: Path):
    """Test that script generates oxum correctly"""
    # test with entire fixture to text folder recursion

    total_bytes, total_files = pb.get_oxum(transfer_files)

    assert total_bytes == 59286
    assert total_files == 12


def test_validate_valid_bag(transfer_files: Path, caplog):
    """Test the log message"""

    # create tiny bag for testing
    object_dir = transfer_files / "objects"
    object_dir.mkdir()
    (transfer_files / "rclone.md5").rename(object_dir / "rlcone.md5")
    test_bag = bagit.make_bag(object_dir)

    pb.validate_bag_in_payload(transfer_files)

    assert f"{test_bag.path} is valid." in caplog.text


def test_validate_invalid_bag(transfer_files, caplog):
    """Test the log message if the bag isn't valid for some reason"""

    object_dir = transfer_files / "objects"
    object_dir.mkdir()
    (transfer_files / "rclone.md5").rename(object_dir / "rlcone.md5")

    test_bag = bagit.make_bag(object_dir)
    print(list(Path(test_bag.path).iterdir()))
    (Path(test_bag.path) / "bag-info.txt").unlink()
    pb.validate_bag_in_payload(transfer_files)

    assert (
        f"{test_bag.path} is not valid. Check the bag manifest and oxum." in caplog.text
    )
