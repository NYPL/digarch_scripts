import shutil
from pathlib import Path

import bagit
import pytest

import digarch_scripts.package.package_images as pi


@pytest.fixture
def transfer_files(tmp_path: Path, request):
    fixture_data = Path(request.module.__file__).parent / "fixtures" / "image"
    shutil.copytree(fixture_data, tmp_path, dirs_exist_ok=True)
    return tmp_path


# Test command-line arguments
@pytest.fixture
def args(transfer_files):
    args = [
        "script_name",
        "--images_folder",
        str(transfer_files / "images"),
        "--dest",
        str(transfer_files),
        "--acqid",
        "ACQ_1234",
        "--streams_folder",
        str(transfer_files / "streams"),
        "--logs_folder",
        str(transfer_files / "logs"),
    ]
    return args


def test_requires_args(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test that script requires image, dest, and id (first 3 args)"""

    for i in range(0, 3):
        # remove a pair of list items (arg and value) for each test
        part_args = args[0 : 2 * i + 1] + args[2 * i + 3 :]

        monkeypatch.setattr("sys.argv", part_args)

        with pytest.raises(SystemExit):
            args = pi.parse_args()

        stderr = capsys.readouterr().err

        assert f"required: {args[2*i+1]}" in stderr


def test_optional_args(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test that script requires all five args"""

    for i in [3, 4]:
        # remove a pair of list items (arg and value) for each test
        part_args = args[0 : 2 * i + 1] + args[2 * i + 3 :]
        missing_arg = args[2 * i]

        monkeypatch.setattr("sys.argv", part_args)

        parsed_args = pi.parse_args()

        assert missing_arg not in parsed_args


def test_arg_paths_must_exist(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test that script errors if a path argument doesn't exist"""

    for i in [1, 2, 4, 5]:
        bad_args = args
        bad_path = "nonexistant"
        bad_args[2 * i] = bad_path

        monkeypatch.setattr("sys.argv", bad_args)
        with pytest.raises(SystemExit):
            args = pi.parse_args()

        stderr = capsys.readouterr().err

        assert f"{bad_path} does not exist" in stderr


def test_id_arg_must_match_pattern(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test that script errors if id argument doesn't match ACQ_####_######"""
    args[6] = "bad_id"
    monkeypatch.setattr("sys.argv", args)
    with pytest.raises(SystemExit):
        args = pi.parse_args()

    stderr = capsys.readouterr().err

    assert f"bad_id does not match" in stderr


def test_carrier_files_found(transfer_files):
    acq_id = "ACQ_1234"

    carrier_files = pi.find_carrier_files(
        acq_id,
        transfer_files / "images",
        transfer_files / "logs",
        transfer_files / "streams",
    )

    carrier1 = f"{acq_id}_123456"
    assert carrier1 in carrier_files
    for key in ["images", "logs", "streams"]:
        assert key in carrier_files[carrier1]
    for key in carrier_files[carrier1]:
        for item in carrier_files[carrier1][key]:
            assert isinstance(item, Path)


def test_acqid_not_found(transfer_files):
    acq_id = "ACQ_1111"

    with pytest.raises(Warning) as exc:
        pi.find_carrier_files(
            acq_id,
            transfer_files / "images",
            transfer_files / "logs",
            transfer_files / "streams",
        )

    assert f"No files found with the acquisition ID {acq_id} in filename" in str(
        exc.value
    )


def test_file_found(transfer_files):
    acq_id = "ACQ_1234"

    carrier_files = {}
    carrier_files = pi.find_category_of_carrier_files(
        carrier_files, acq_id, transfer_files / "images", [".img"], "images"
    )

    assert (
        transfer_files / "images" / "ACQ_1234_123456.img" in carrier_files[f"{acq_id}_123456"]["images"]
    )


def test_ignore_unknown_extension_for_category(transfer_files):
    acq_id = "ACQ_1234"

    carrier_files = {}
    carrier_files = pi.find_category_of_carrier_files(
        carrier_files, acq_id, transfer_files / "images", [".001"], "images"
    )

    assert f"{acq_id}_123456" not in carrier_files


def test_multiple_files_found(transfer_files):
    acq_id = "ACQ_1234"

    carrier_files = {}
    carrier_files = pi.find_category_of_carrier_files(
        carrier_files, acq_id, transfer_files / "logs", [".log"], "logs"
    )

    assert len(carrier_files[f"{acq_id}_123456"]["logs"]) == 2


@pytest.fixture
def carrier_files(transfer_files):
    acq_id = "ACQ_1234"

    carrier_files = pi.find_carrier_files(
        acq_id,
        transfer_files / "images",
        transfer_files / "logs",
        transfer_files / "streams",
    )
    return carrier_files

def test_good_validate_carrier(carrier_files, caplog):
    pi.validate_carrier_files(carrier_files)

    assert not caplog.text


@pytest.mark.parametrize("key", ['images', 'logs', 'streams'])
def test_warn_carrier_with_one_missing_category(carrier_files, key, caplog):
    carrier_files['ACQ_1234_123456'].pop(key)

    pi.validate_carrier_files(carrier_files)

    assert f'The following categories of files were not found for ACQ_1234_123456: {key}' in caplog.text


def test_warn_carrier_with_logs_no_images_or_streams(caplog):
    carrier_files = {
        'ACQ_1234_123456': {
            'logs': [Path('ACQ_1234_123456.log')]
        }
    }
    pi.validate_carrier_files(carrier_files)

    assert f'The following categories of files were not found for ACQ_1234_123456: images, streams' in caplog.text


def test_warn_carrier_with_streams_no_images_or_logs(caplog):
    carrier_files = {
        'ACQ_1234_123456': {
            'streams': [Path('ACQ_1234_123456_streams')]
        }
    }
    pi.validate_carrier_files(carrier_files)

    assert f'The following categories of files were not found for ACQ_1234_123456: images, logs' in caplog.text



def test_warn_and_skip_0_length_image(carrier_files, caplog):
    carrier_files["ACQ_1234_123457"]["images"][0].unlink()
    carrier_files["ACQ_1234_123457"]["images"][0].touch()
    pi.validate_carrier_files(carrier_files)

    assert f'The following image file is 0-bytes: {str(carrier_files["ACQ_1234_123457"]["images"][0])}' in caplog.text


def test_warn_streams_missing_a_side():
    #TODO
    assert True






'''
def test_full_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test end to end successful run"""

    monkeypatch.setattr("sys.argv", args)
    pi.main()

    acq_dir = Path(args[4]) / args[6]
    assert acq_dir.exists()

    assert "ACQ_1234_123456" in [x.name for x in acq_dir.iterdir()]
'''
