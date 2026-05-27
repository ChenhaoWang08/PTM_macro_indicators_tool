from __future__ import annotations

import pytest

from macro_radar.ingestion.csv_loader import load_time_series_csv


def test_load_time_series_csv_reads_and_sorts(tmp_path):
    path = tmp_path / "series.csv"
    path.write_text("date,value\n2024-02-01,2\n2024-01-01,1\n", encoding="utf-8")

    df = load_time_series_csv(path)

    assert list(df.columns) == ["date", "value"]
    assert df["value"].tolist() == [1, 2]
    assert df["date"].is_monotonic_increasing


def test_load_time_series_csv_missing_required_column_raises(tmp_path):
    path = tmp_path / "series.csv"
    path.write_text("date,other\n2024-01-01,1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required"):
        load_time_series_csv(path)


def test_load_time_series_csv_non_numeric_value_raises(tmp_path):
    path = tmp_path / "series.csv"
    path.write_text("date,value\n2024-01-01,not-a-number\n", encoding="utf-8")

    with pytest.raises(ValueError, match="non-numeric"):
        load_time_series_csv(path)

