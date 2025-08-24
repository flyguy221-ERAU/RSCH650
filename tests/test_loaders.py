from pathlib import Path

import pytest

from loaders import DataLoadError, read_csv_safe


def test_read_csv_safe_missing(tmp_path: Path):
    # point to a file that does not exist
    missing = tmp_path / "does_not_exist.csv"
    with pytest.raises(DataLoadError) as exc:
        read_csv_safe(missing)
    # Helpful message for users
    assert "Missing input file" in str(exc.value)


def test_read_csv_safe_bad_csv(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    bad.write_text(",,,,,\n,,")  # nonsense
    with pytest.raises(DataLoadError):
        read_csv_safe(bad)
