from __future__ import annotations

import pandas as pd
import pytest

from macro_radar.storage.duckdb_store import DuckDBStore


def test_duckdb_store_writes_and_reads_time_series():
    store = DuckDBStore()
    df = pd.DataFrame(
        {"date": pd.date_range("2024-01-01", periods=2, freq="MS"), "value": [1, 2]}
    )

    store.write_time_series("m2", df)
    result = store.read_time_series("m2")

    assert result["value"].tolist() == [1.0, 2.0]
    assert result["date"].is_monotonic_increasing


def test_duckdb_store_rejects_invalid_table_name():
    store = DuckDBStore()
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=1), "value": [1]})

    with pytest.raises(ValueError, match="Table names"):
        store.write_time_series("bad-name", df)


def test_duckdb_store_missing_table_raises():
    store = DuckDBStore()

    with pytest.raises(ValueError, match="does not exist"):
        store.read_time_series("missing_table")

