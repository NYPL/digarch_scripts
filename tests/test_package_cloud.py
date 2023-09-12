import ipres_package_cloud.package_cloud as pc

import argparse
import os
from pathlib import Path
import pytest
import shutil

@pytest.fixture
def transfer_files(tmp_path: Path, request):
    fixture_data = Path(request.module.__file__).parent / 'fixtures'
    shutil.copytree(fixture_data, tmp_path, dirs_exist_ok=True)
    return tmp_path

@pytest.fixture
def args(transfer_files):
    args = [
        "script_name",
        "--payload",
        str(transfer_files / 'rclone_files'),
        "--md5",
        str(transfer_files / 'rclone.md5'),
        "--log",
        str(transfer_files / 'rclone.log'),
        "--dest",
        str(transfer_files),
        "--id",
        "ACQ_1234_123456"
    ]
    return args

def test_requires_args(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list):
    """Test that script requires all five args"""

    for i in range(0, 5):
        # remove a pair of list items (arg and value) for each test
        part_args = args[0:2*i+1] + args[2*i+3:]

        monkeypatch.setattr(
                'sys.argv', part_args
            )

        with pytest.raises(SystemExit):
            args = pc.parse_args()

        stderr = capsys.readouterr().err

        assert f'required: {args[2*i+1]}' in stderr


def test_arg_paths_must_exist(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list):
    """Test that script errors if path argument doesn't exist"""

    for i in range(1,5):
        bad_args = args
        bad_path = 'nonexistant'
        bad_args[2*i] = bad_path

        monkeypatch.setattr(
                'sys.argv', bad_args
            )
        with pytest.raises(SystemExit):
            args = pc.parse_args()

        stderr = capsys.readouterr().err

        assert f'{bad_path} does not exist' in stderr


def test_id_arg_must_match_pattern(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list):
    args[-1] = 'bad_id'
    monkeypatch.setattr(
            'sys.argv', args
        )
    with pytest.raises(SystemExit):
        args = pc.parse_args()

    stderr = capsys.readouterr().err

    assert f'bad_id does not match' in stderr

def test_create_package_basedir_exc_on_readonly(tmp_path, args):
    id = args[-1]
    # make folder read-only
    os.chmod(tmp_path, 0o500)

    with pytest.raises(PermissionError) as exc:
        pc.create_base_dir(tmp_path, id)

    # change back to allow clean-up (might not be necessary)
    os.chmod(tmp_path, 0o777)
    assert f'{str(tmp_path)} is not writable' in str(exc.value)


def test_create_package_basedir(tmp_path, args):
    id = args[-1]
    base_dir = pc.create_base_dir(tmp_path, args[-1])

    assert base_dir.name == id
    assert base_dir.parent.name == id[:-7]

def test_create_package_basedir_with_existing_acq_dir(tmp_path, args):
    id = args[-1]
    (tmp_path / id[:-7]).mkdir()
    base_dir = pc.create_base_dir(tmp_path, args[-1])

    assert base_dir.name == id
    assert base_dir.parent.name == id[:-7]

def test_error_on_existing_package_dir(tmp_path, args):
    id = args[-1]
    base_dir = tmp_path / id[:-7] / id
    base_dir.mkdir(parents=True)

    with pytest.raises(FileExistsError) as exc:
        pc.create_base_dir(tmp_path, id)

    assert f'{base_dir} already exists. Make sure you are using the correct ID' in str(exc.value)
