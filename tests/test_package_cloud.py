import ipres_package_cloud.package_cloud as pc

import argparse
import os
from pathlib import Path
import pytest
import shutil

import bagit


@pytest.fixture
def transfer_files(tmp_path: Path, request):
    fixture_data = Path(request.module.__file__).parent / "fixtures"
    shutil.copytree(fixture_data, tmp_path, dirs_exist_ok=True)
    return tmp_path


@pytest.fixture
def args(transfer_files):
    args = [
        "script_name",
        "--payload",
        str(transfer_files / "rclone_files"),
        "--md5",
        str(transfer_files / "rclone.md5"),
        "--log",
        str(transfer_files / "rclone.log"),
        "--dest",
        str(transfer_files),
        "--id",
        "ACQ_1234_123456",
    ]
    return args


def test_requires_args(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test that script requires all five args"""

    for i in range(0, 5):
        # remove a pair of list items (arg and value) for each test
        part_args = args[0 : 2 * i + 1] + args[2 * i + 3 :]

        monkeypatch.setattr("sys.argv", part_args)

        with pytest.raises(SystemExit):
            args = pc.parse_args()

        stderr = capsys.readouterr().err

        assert f"required: {args[2*i+1]}" in stderr


def test_arg_paths_must_exist(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test that script errors if path argument doesn't exist"""

    for i in range(1, 5):
        bad_args = args
        bad_path = "nonexistant"
        bad_args[2 * i] = bad_path

        monkeypatch.setattr("sys.argv", bad_args)
        with pytest.raises(SystemExit):
            args = pc.parse_args()

        stderr = capsys.readouterr().err

        assert f"{bad_path} does not exist" in stderr


def test_id_arg_must_match_pattern(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test that script errors if id argument doesn't match ACQ_####_######"""
    args[-1] = "bad_id"
    monkeypatch.setattr("sys.argv", args)
    with pytest.raises(SystemExit):
        args = pc.parse_args()

    stderr = capsys.readouterr().err

    assert f"bad_id does not match" in stderr


def test_create_package_basedir_exc_on_readonly(tmp_path: Path, args: list):
    """Test that package folder maker reports permission error"""

    id = args[-1]
    # make folder read-only
    os.chmod(tmp_path, 0o500)

    with pytest.raises(PermissionError) as exc:
        pc.create_base_dir(tmp_path, id)

    # change back to allow clean-up (might not be necessary)
    os.chmod(tmp_path, 0o777)
    assert f"{str(tmp_path)} is not writable" in str(exc.value)


def test_create_package_basedir(tmp_path: Path, args: list):
    """Test that package folder maker makes ACQ and Carrier folders"""

    id = args[-1]
    base_dir = pc.create_base_dir(tmp_path, args[-1])

    assert base_dir.name == id
    assert base_dir.parent.name == id[:-7]


def test_create_package_basedir_with_existing_acq_dir(tmp_path: Path, args: list):
    """Test that package folder maker respect existing ACQ folder"""

    id = args[-1]
    (tmp_path / id[:-7]).mkdir()
    base_dir = pc.create_base_dir(tmp_path, args[-1])

    assert base_dir.name == id
    assert base_dir.parent.name == id[:-7]


def test_error_on_existing_package_dir(tmp_path: Path, args: list):
    """Test that package folder maker errors if carrier folder exists"""

    id = args[-1]
    base_dir = tmp_path / id[:-7] / id
    base_dir.mkdir(parents=True)

    with pytest.raises(FileExistsError) as exc:
        pc.create_base_dir(tmp_path, id)

    assert f"{base_dir} already exists. Make sure you are using the correct ID" in str(
        exc.value
    )


@pytest.fixture
def package_base_dir(tmp_path: Path, args: list):
    return pc.create_base_dir(tmp_path, args[-1])


def test_move_metadata(transfer_files: Path, package_base_dir: Path):
    """Test that metadata folder and log file are moved successfully"""

    source_log = transfer_files / "rclone.log"
    pc.move_metadata_file(source_log, package_base_dir)

    assert not source_log.exists()
    assert (package_base_dir / "metadata" / "rclone.log").exists()


def test_do_not_overwrite_metadata(transfer_files: Path, package_base_dir: Path):
    """Test that log file is not moved if a same name file exists in dest"""

    source_log = transfer_files / "rclone.log"
    rclone_log = package_base_dir / "metadata" / "rclone.log"
    rclone_log.parent.mkdir()
    rclone_log.touch()

    with pytest.raises(FileExistsError) as exc:
        pc.move_metadata_file(source_log, package_base_dir)

    assert source_log.exists()
    assert f"{rclone_log} already exists. Not moving." in str(exc.value)


def test_move_payload(transfer_files: Path, package_base_dir: Path):
    """Test that entirety of payload is moved and hierarchy is preserved"""

    source_payload = transfer_files / "rclone_files"
    source_contents = [
        file.relative_to(source_payload) for file in source_payload.rglob("*")
    ]

    data_path = package_base_dir / "contents" / "data"
    pc.move_payload(source_payload, package_base_dir)

    # check that source is empty
    assert not any(source_payload.iterdir())

    assert data_path.exists()

    # compare contents of data and former source
    data_contents = [file.relative_to(data_path) for file in data_path.rglob("*")]
    assert source_contents == data_contents


def test_do_not_overwrite_payload(transfer_files: Path, package_base_dir: Path):
    """Test that no payload file is moved if /data exists"""

    source_payload = transfer_files / "rclone_files"
    source_contents = [file for file in source_payload.rglob("*")]

    bag_payload = package_base_dir / "objects" / "data"
    bag_payload.mkdir(parents=True)

    with pytest.raises(FileExistsError) as exc:
        pc.move_payload(source_payload, package_base_dir)

    # check source has not changed
    assert source_contents == [file for file in source_payload.rglob("*")]
    assert f"{bag_payload} already exists. Not moving files." in str(exc.value)


def test_create_bag(transfer_files: Path, package_base_dir: Path):
    """Test that all tag files are created and rclone md5sums are correctly converted"""

    md5_path = transfer_files / "rclone.md5"
    bag_path = transfer_files / "objects"

    # might need further testing of the oxum and manifest converter functions
    pc.create_bag_in_objects(md5_path, package_base_dir)

    assert bagit.Bag(bag_path).validate(completeness_only=True)


def test_generate_valid_oxum(transfer_files: Path):
    """Test that script generates oxum correctly"""

    total_bytes, total_files = pc.get_oxum(transfer_files)

    assert total_bytes == 59347
    assert total_files == 12

    
def test_validate_valid_bag(transfer_files: Path, caplog):
    """Test the log message"""

    object_dir = transfer_files / "objects"
    object_dir.mkdir()
    (transfer_files / "rclone.md5").rename(object_dir / "rlcone.md5")

    test_bag = bagit.make_bag(object_dir)

    pc.validate_bag_in_payload(transfer_files)

    assert f"{test_bag.path} is valid." in caplog.text
    

def test_validate_invalid_bag(transfer_files, caplog):
    """Test the log message if the bag isn't valid for some reason"""

    object_dir = transfer_files / "objects"
    object_dir.mkdir()
    (transfer_files / "rclone.md5").rename(object_dir / "rlcone.md5")

    test_bag = bagit.make_bag(object_dir)
    print(list(Path(test_bag.path).iterdir()))
    (Path(test_bag.path) / 'bag-info.txt').unlink()
    pc.validate_bag_in_payload(transfer_files)
    

    assert f"{test_bag.path} is not valid. Check the bag manifest and oxum." in caplog.text


def test_full_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test end to end successful run"""

    monkeypatch.setattr("sys.argv", args)
    pc.main()

    pkg_dir = Path(args[-3]) / args[-1][:-7] / args[-1]
    assert pkg_dir.exists()
    assert bagit.Bag(pkg_dir / 'objects').validate()

    assert 'rclone.log' in [x.name for x in (pkg_dir / 'metadata').iterdir()]
