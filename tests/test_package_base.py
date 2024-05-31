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
def rclone_payload(transfer_files):
    return transfer_files / "rclone_files"


@pytest.fixture
def rclone_md5_manifest(transfer_files):
    return transfer_files / "rclone.md5"


@pytest.fixture
def rclone_log(transfer_files):
    return transfer_files / "rclone.log"


@pytest.fixture
def image_files(tmp_path: Path, request):
    fixture_data = Path(request.module.__file__).parent / "fixtures" / "image"
    shutil.copytree(fixture_data, tmp_path, dirs_exist_ok=True)
    return tmp_path


@pytest.fixture
def rsync_files(tmp_path: Path, request):
    fixture_data = Path(request.module.__file__).parent / "fixtures" / "rsync"
    shutil.copytree(fixture_data, tmp_path, dirs_exist_ok=True)
    return tmp_path


@pytest.fixture
def rsync_payload(rsync_files):
    return rsync_files / "rsync_files"


@pytest.fixture
def rsync_log(rsync_files):
    return rsync_files / "rsync.log"


@pytest.fixture
def acqid():
    return "ACQ_1234_123456"


def args(transfer_files):
    args = [
        transfer_files / "rclone.md5",
        transfer_files / "rclone.log",
        transfer_files,
    ]
    return args


CREATE_DIR = [
    (pb.create_acq_dir, "ACQ_1234"),
    (pb.create_package_dir, "ACQ_1234_123456"),
]


def test_file_found(image_files):
    acq_id = "ACQ_1234"

    carrier_files = {}
    carrier_files = pb.find_category_of_carrier_files(
        carrier_files, acq_id, image_files / "images", [".img"], "images"
    )

    assert (
        image_files / "images" / "ACQ_1234_123456.img"
        in carrier_files[f"{acq_id}_123456"]["images"]
    )


def test_ignore_unknown_extension_for_category(image_files):
    acq_id = "ACQ_1234"

    carrier_files = {}
    carrier_files = pb.find_category_of_carrier_files(
        carrier_files, acq_id, image_files / "images", [".001"], "images"
    )

    assert f"{acq_id}_123456" not in carrier_files


def test_multiple_files_found(image_files):
    acq_id = "ACQ_1234"

    carrier_files = {}
    carrier_files = pb.find_category_of_carrier_files(
        carrier_files, acq_id, image_files / "logs", [".log"], "logs"
    )

    assert len(carrier_files[f"{acq_id}_123456"]["logs"]) == 2


@pytest.mark.parametrize("tested_function,id", CREATE_DIR)
def test_create_dir_exc_on_readonly(tmp_path: Path, id: str, tested_function):
    """Test that package folder maker reports permission error"""

    # make folder read-only
    os.chmod(tmp_path, 0o500)

    with pytest.raises(PermissionError) as exc:
        tested_function(tmp_path, id)

    # change back to allow clean-up (might not be necessary)
    os.chmod(tmp_path, 0o777)
    assert f"{str(tmp_path)} is not writable" in str(exc.value)


def test_create_acq_dir(tmp_path: Path):
    """Test that package folder maker makes ACQ and Carrier folders"""

    id = "ACQ_1234"
    base_dir = pb.create_acq_dir(tmp_path, id)

    assert base_dir.name == id
    assert base_dir.parent.name == tmp_path.name


def test_create_pkg_dir(tmp_path: Path, acqid: str):
    """Test that package folder maker makes ACQ and Carrier folders"""

    base_dir = pb.create_package_dir(tmp_path, acqid)

    assert base_dir.name == acqid
    assert base_dir.parent.name == acqid[:-7]


def test_create_package_basedir_with_existing_acq_dir(tmp_path: Path, acqid: str):
    """Test that package folder maker respect existing ACQ folder"""

    (tmp_path / acqid[:-7]).mkdir()
    base_dir = pb.create_package_dir(tmp_path, acqid)

    assert base_dir.name == acqid
    assert base_dir.parent.name == acqid[:-7]


def test_error_on_existing_package_dir(tmp_path: Path, acqid: str):
    """Test that package folder maker errors if carrier folder exists"""

    base_dir = tmp_path / acqid[:-7] / acqid
    base_dir.mkdir(parents=True)

    with pytest.raises(FileExistsError) as exc:
        pb.create_package_dir(tmp_path, acqid)

    assert f"{base_dir} already exists. Make sure you are using the correct ID" in str(
        exc.value
    )


@pytest.fixture
def package_base_dir(tmp_path: Path, acqid: str):
    return pb.create_package_dir(tmp_path, acqid)


MOVE_FILE = [
    (pb.move_metadata_file, "metadata"),
]


@pytest.mark.parametrize("test_function,dest", MOVE_FILE)
def test_move_file(package_base_dir: Path, rclone_log: Path, test_function, dest: str):
    """Test that metadata folder and log file are moved successfully"""

    test_function(rclone_log, package_base_dir)

    assert not rclone_log.exists()
    assert (package_base_dir / dest / "rclone.log").exists()


@pytest.mark.parametrize("test_function,dest", MOVE_FILE)
def test_do_not_overwrite_file(
    package_base_dir: Path, rclone_log: Path, test_function, dest: str
):
    """Test that log file is not moved if a same name file exists in dest"""

    rclone_log = package_base_dir / dest / rclone_log.name
    rclone_log.parent.mkdir()
    rclone_log.touch()

    with pytest.raises(FileExistsError) as exc:
        test_function(rclone_log, package_base_dir)

    assert rclone_log.exists()
    assert f"{rclone_log} already exists in {dest} folder. Not moving." in str(
        exc.value
    )


MOVE_FILES = [
    (pb.move_metadata_files, "metadata"),
    (pb.move_data_files, "data"),
]


@pytest.mark.parametrize("test_function,dest", MOVE_FILES)
def test_move_multiple_file(
    package_base_dir: Path, rclone_log: Path, rclone_md5_manifest: Path, test_function, dest: str
):
    """Test that multiple files are moved successfully"""
    parts = dest.split("/")

    md_files = [rclone_log, rclone_md5_manifest]
    test_function(md_files, package_base_dir)

    for md_file in md_files:
        assert not md_file.exists()
        assert (package_base_dir / dest / md_file.name).exists()


@pytest.mark.parametrize("test_function,dest", MOVE_FILES)
def test_partial_halt_multiple_files(
    package_base_dir: Path, rclone_log: Path, rclone_md5_manifest: Path, test_function, dest: str
):
    """Test that warning is issued for multiple move if a single metadata move fails"""

    rclone_log = package_base_dir / dest / rclone_log.name
    rclone_log.parent.mkdir()
    rclone_log.touch()

    md_files = [rclone_log, rclone_md5_manifest]

    with pytest.raises(Warning) as exc:
        test_function(md_files, package_base_dir)

    assert rclone_log.exists()
    assert (
        f"already exists in {dest} folder. Not moving. One or more files may have already been moved to the {dest} folder"
        in str(exc.value)
    )


@pytest.fixture
def bag_payload(package_base_dir: Path, rclone_payload: Path):
    pb.move_data_files(list(rclone_payload.iterdir()), package_base_dir)
    bag_payload = package_base_dir / "data"

    return bag_payload


def test_convert_rclone_md5(bag_payload: Path, rclone_md5_manifest: Path):
    pb.convert_rclone_md5_to_bagit_manifest(rclone_md5_manifest, bag_payload.parent)
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


@pytest.fixture
def rsync_bag_payload(package_base_dir: Path, rsync_payload: Path):
    pb.move_data_files(list(rsync_payload.iterdir()), package_base_dir)
    bag_payload = package_base_dir / "data"

    return bag_payload


def test_convert_rsync_log(rsync_bag_payload: Path, rsync_log: Path, rsync_files):
    pb.convert_rsync_log_to_bagit_manifest(rsync_log, rsync_bag_payload.parent)
    bag_md5 = rsync_bag_payload.parent / "manifest-md5.txt"

    # Get path to correct payload in data
    # read md5 and extract filepaths
    with open(bag_md5) as m:
        md5_paths = [line.strip().split("  ")[-1] for line in m.readlines()]

    payload_files = [
        str(path.relative_to(rsync_bag_payload.parent)) for path in rsync_bag_payload.rglob("*")
    ]

    for a_file in md5_paths:
        assert a_file in payload_files


def test_convert_rsync_log_replaces_prefix_with_data(rsync_bag_payload: Path, rsync_log: Path):
    prefix = "/Users/fortitude/dev/digarch-scripts-poetry/tests/fixtures/rsync/rsync_files"
    pb.convert_rsync_log_to_bagit_manifest(rsync_log, rsync_bag_payload.parent, prefix)
    bag_md5 = rsync_bag_payload.parent / "manifest-md5.txt"

    #extract paths from manifest
    with open(bag_md5) as m:
        md5_paths = [line.strip().split("  ")[-1] for line in m.readlines()]

    #extract paths from log
    rsync_paths = []
    with open(rsync_log) as m:
        lines = m.readlines()
        for line in lines:
            parts = line.strip().split(", ")
            if len(parts) > 3 and parts[2].strip():
                rsync_paths.append(line.strip().split(", ")[-1].replace(prefix[1:], 'data'))

    #assert difference
    assert set(md5_paths) == set(rsync_paths)


def test_convert_rsync_log_requires_specific_format(rsync_bag_payload: Path, rsync_log: Path, caplog):
    rsync_log.write_text('time, size, not a hash, good/path')
    pb.convert_rsync_log_to_bagit_manifest(rsync_log, rsync_bag_payload.parent)

    assert f"{str(rsync_log)} should be formatted with md5 hash in the 3rd comma-separated fields" in caplog.text


def test_create_bag(package_base_dir: Path, rclone_payload: Path, rclone_md5_manifest: Path):
    """Test that all tag files are created and rclone md5sums are correctly converted"""

    bag_path = package_base_dir / "objects"

    # might need further testing of the oxum and manifest converter functions
    pb.create_bag_in_objects(rclone_payload, package_base_dir, rclone_md5_manifest, 'rclone')

    assert bagit.Bag(str(bag_path)).validate(completeness_only=True)


def test_generate_valid_oxum(transfer_files: Path):
    """Test that script generates oxum correctly"""
    # test with entire fixture to text folder recursion

    total_bytes, total_files = pb.get_oxum(transfer_files)

    assert total_bytes == 59286
    assert total_files == 12


VALIDATE_BAGS = [
    (pb.validate_objects_bag, "objects"),
    (pb.validate_images_bag, "images"),
    (pb.validate_streams_bag, "streams"),
]


@pytest.mark.parametrize("test_function,type", VALIDATE_BAGS)
def test_validate_valid_bag(transfer_files: Path, test_function, type: str, caplog):
    """Test the log message"""

    # create tiny bag for testing
    sub_dir = transfer_files / type
    sub_dir.mkdir()
    (transfer_files / "rclone.md5").rename(sub_dir / "rlcone.md5")
    test_bag = bagit.make_bag(sub_dir)

    test_function(transfer_files)

    assert f"{test_bag.path} is valid." in caplog.text


@pytest.mark.parametrize("test_function,type", VALIDATE_BAGS)
def test_validate_invalid_bag(transfer_files, test_function, type: str, caplog):
    """Test the log message if the bag isn't valid for some reason"""

    sub_dir = transfer_files / type
    sub_dir.mkdir()
    (transfer_files / "rclone.md5").rename(sub_dir / "rlcone.md5")

    test_bag = bagit.make_bag(sub_dir)
    print(list(Path(test_bag.path).iterdir()))
    (Path(test_bag.path) / "bag-info.txt").unlink()
    test_function(transfer_files)

    assert (
        f"{test_bag.path} is not valid. Check the bag manifest and oxum." in caplog.text
    )
