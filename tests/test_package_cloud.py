import ipres_package_cloud.package_cloud as pc

import argparse
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
        str(transfer_files / 'fixtures' / 'rclone_files'),
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

        assert args[2*i+1] in stderr
