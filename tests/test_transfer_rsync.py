import shutil
from pathlib import Path
import subprocess

import bagit
import pytest

import digarch_scripts.transfer.transfer_rsync as tr


@pytest.fixture
def transfer_files(tmp_path: Path, request):
    fixture_data = Path(request.module.__file__).parent / "fixtures" / "rsync"
    shutil.copytree(fixture_data, tmp_path, dirs_exist_ok=True)
    return tmp_path


@pytest.fixture
def args(transfer_files):
    args = [
        "script_name",
        "--source",
        str(transfer_files / "rsync_files"),
        "--dest",
        str(transfer_files),
        "--carrierid",
        "ACQ_1234_123456",
    ]
    return args


def test_requires_args(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test that script requires all five args"""

    for i in range(0, 3):
        # remove a pair of list items (arg and value) for each test
        part_args = args[0 : 2 * i + 1] + args[2 * i + 3 :]

        monkeypatch.setattr("sys.argv", part_args)

        with pytest.raises(SystemExit):
            args = tr.parse_args()

        stderr = capsys.readouterr().err

        assert f"required: {args[2*i+1]}" in stderr


def test_arg_paths_must_exist(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test that script errors if path argument doesn't exist"""

    for i in range(1, 3):
        bad_args = args
        bad_path = "nonexistant"
        bad_args[2 * i] = bad_path

        monkeypatch.setattr("sys.argv", bad_args)
        with pytest.raises(SystemExit):
            args = tr.parse_args()

        stderr = capsys.readouterr().err

        assert f"{bad_path} does not exist" in stderr


def test_id_arg_must_match_pattern(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test that script errors if id argument doesn't match ACQ_####_######"""
    args[-1] = "bad_id"
    monkeypatch.setattr("sys.argv", args)
    with pytest.raises(SystemExit):
        args = tr.parse_args()

    stderr = capsys.readouterr().err

    assert f"bad_id does not match" in stderr


def test_rsync_completes_successfully(transfer_files):
    id = "ACQ_1234_123456"
    source = transfer_files / "rsync_files"
    dest = transfer_files / id
    dest.mkdir()
    tr.run_rsync(source, dest)

    assert (dest / "metadata" / f"{id}_rsync.log").exists()
    assert (dest / "objects" / "data").is_dir()
    assert True


def test_rsync_fails_gracefully(transfer_files, monkeypatch, caplog):
    tr.run_rsync("/nonexistant", transfer_files)

    assert "Transfer did not complete successfully. Delete transferred files and re-run" in caplog.text


@pytest.fixture
def mounted_image(transfer_files):
    image = transfer_files / "rsync_files.dmg"
    mount_point = transfer_files / "new"
    mount_point.mkdir()
    process = subprocess.run(["hdiutil", "attach", image, "-mountpoint", mount_point])

    return mount_point


def test_disktype_completes_successfully(mounted_image, transfer_files):
    # source make and mount tiny disk image
    dest = transfer_files
    tr.run_disktype(mounted_image, dest)
    assert (dest / "metadata" / f"{dest.name}_disktype.log").exists()


def test_disktype_skips_folders(transfer_files, caplog):
    source = transfer_files / "rsync_files"
    tr.run_disktype(source, transfer_files)

    assert "Disktype log cannot be generated for a folder. Skipping" in caplog.text


def test_full_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test end to end successful run"""

    monkeypatch.setattr("sys.argv", args)
    tr.main()

    pkg_dir = Path(args[-3]) / args[-1][:-7] / args[-1]
    assert pkg_dir.exists()
    assert bagit.Bag(str(pkg_dir / "objects")).validate()
