import digarch_scripts.package.package_images as pi

from pathlib import Path
import pytest
import shutil

import bagit


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
        "--image",
        str(transfer_files / "image.img"),
        "--dest",
        str(transfer_files),
        "--id",
        "ACQ_1234_123456",
        "--streams",
        str(transfer_files / "streams"),
        "--log",
        str(transfer_files / "process.log"),
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
        missing_arg = args[2*i]

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


def test_full_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list
):
    """Test end to end successful run"""

    monkeypatch.setattr("sys.argv", args)
    pi.main()

    pkg_dir = Path(args[4]) / args[6][:-7] / args[6]
    assert pkg_dir.exists()

    assert "process.log" in [x.name for x in (pkg_dir / "metadata").iterdir()]
