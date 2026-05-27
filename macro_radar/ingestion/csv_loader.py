from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_time_series_csv(path: str | Path) -> pd.DataFrame:
    """Load a local time series CSV with `date,value` columns."""
    csv_path = Path(path)
    df = pd.read_csv(csv_path)

    required_columns = {"date", "value"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"CSV is missing required column(s): {missing}")

    result = df[["date", "value"]].copy()
    try:
        result["date"] = pd.to_datetime(result["date"], errors="raise")
    except Exception as exc:
        raise ValueError("CSV date column contains invalid datetime values") from exc

    try:
        result["value"] = pd.to_numeric(result["value"], errors="raise")
    except Exception as exc:
        raise ValueError("CSV value column contains non-numeric values") from exc

    if result["value"].isna().any():
        raise ValueError("CSV value column contains missing numeric values")

    return result.sort_values("date").reset_index(drop=True)

