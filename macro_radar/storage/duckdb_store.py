from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd

_VALID_TABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DuckDBStore:
    def __init__(self, db_path: str | Path = ":memory:"):
        self.connection = duckdb.connect(str(db_path))

    def write_time_series(self, name: str, df: pd.DataFrame) -> None:
        safe_name = self._validate_table_name(name)
        self._validate_time_series_frame(df)
        data = df[["date", "value"]].copy()
        data["date"] = pd.to_datetime(data["date"])
        data["value"] = pd.to_numeric(data["value"])

        self.connection.register("_macro_radar_time_series", data)
        try:
            self.connection.execute(
                f"""
                CREATE OR REPLACE TABLE "{safe_name}" AS
                SELECT
                    CAST(date AS TIMESTAMP) AS date,
                    CAST(value AS DOUBLE) AS value
                FROM _macro_radar_time_series
                ORDER BY date
                """
            )
        finally:
            self.connection.unregister("_macro_radar_time_series")

    def read_time_series(self, name: str) -> pd.DataFrame:
        safe_name = self._validate_table_name(name)
        if not self._table_exists(safe_name):
            raise ValueError(f"Time series table does not exist: {safe_name}")

        result = self.connection.execute(
            f'SELECT date, value FROM "{safe_name}" ORDER BY date'
        ).fetchdf()
        result["date"] = pd.to_datetime(result["date"])
        return result[["date", "value"]]

    def _table_exists(self, name: str) -> bool:
        tables = self.connection.execute("SHOW TABLES").fetchdf()
        return name in set(tables["name"].tolist())

    @staticmethod
    def _validate_table_name(name: str) -> str:
        if not _VALID_TABLE_NAME.fullmatch(name):
            raise ValueError("Table names may only contain letters, numbers, and underscores")
        return name

    @staticmethod
    def _validate_time_series_frame(df: pd.DataFrame) -> None:
        required_columns = {"date", "value"}
        missing_columns = required_columns.difference(df.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"DataFrame is missing required column(s): {missing}")

