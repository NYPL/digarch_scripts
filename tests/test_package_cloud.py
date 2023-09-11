import ipres_package_cloud.package_cloud as pc

from pathlib import Path
import pytest
import shutil

@pytest.fixture
def transfer_files(tmp_path: Path, request):
    fixture_data = Path(request.module.__file__).parent / 'fixtures'
    shutil.copytree(fixture_data, tmp_path, dirs_exist_ok=True)
    return tmp_path
