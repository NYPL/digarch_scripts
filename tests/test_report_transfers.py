from pathlib import Path
import pytest
import shutil

import digarch_scripts.package.package_images as pi
import digarch_scripts.report.report_transfers as rt


@pytest.fixture
def transfer_dir(tmp_path: Path, request):
    fixture_data = Path(request.module.__file__).parent / "fixtures" / "image"
    shutil.copytree(fixture_data, tmp_path, dirs_exist_ok=True)
    acq_id = "ACQ_1234"
    carrier_files = pi.find_carriers_image_files(
        acq_id,
        tmp_path,
    )
    pi.package_carriers_image_files(carrier_files, tmp_path)
    return tmp_path / acq_id



def test_parse_args(transfers_dir):
    assert rt.parse_args() == rt.parse_args()


def test_collect_stats(transfers_dir):
    assert rt.collect_stats(Path("test")) == rt.collect_stats(Path("test"))


def test_collect_bag_stats(transfers_dir):
    assert rt.collect_bag_stats(Path("test")) == rt.collect_bag_stats(Path("test"))


def test_warn_on_invalid_bag(image_bag, caplog):
    (image_bag / "bagit.txt").unlink()
    rt.collect_bag_stats(image_bag)

    assert "Directory should be formatted as a bag" in caplog.text


def test_warn_on_missing_date_in_bag(image_bag, caplog):
    (image_bag / "bag-info.txt").write_text("Bag-Size: 1234")
    rt.collect_bag_stats(image_bag)

    assert "Directory should be formatted as a bag" in caplog.text


def test_warn_on_missing_size_in_bag(image_bag, caplog):
    (image_bag / "bagit.txt").unlink()
    rt.collect_bag_stats(image_bag)

    assert "Directory should be formatted as a bag" in caplog.text
