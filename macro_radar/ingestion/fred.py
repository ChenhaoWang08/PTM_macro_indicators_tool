from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_GRAPH_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
_VALID_SERIES_ID = re.compile(r"^[A-Za-z0-9_]+$")


@dataclass(frozen=True)
class FredSeriesConfig:
    key: str
    series_id: str
    description: str


PR_A2_FRED_SERIES: dict[str, FredSeriesConfig] = {
    "m2": FredSeriesConfig(
        key="m2",
        series_id="M2SL",
        description="M2 Money Stock",
    ),
    "yield_curve": FredSeriesConfig(
        key="yield_curve",
        series_id="T10Y2Y",
        description="10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity",
    ),
    "real_rates": FredSeriesConfig(
        key="real_rates",
        series_id="DFII10",
        description="10-Year Treasury Inflation-Indexed Security, Constant Maturity",
    ),
    "credit_spreads_hy": FredSeriesConfig(
        key="credit_spreads_hy",
        series_id="BAMLH0A0HYM2",
        description="ICE BofA US High Yield Index Option-Adjusted Spread",
    ),
    "credit_spreads_ig": FredSeriesConfig(
        key="credit_spreads_ig",
        series_id="BAMLC0A0CM",
        description="ICE BofA US Corporate Index Option-Adjusted Spread",
    ),
}

Transport = Callable[[str], dict[str, Any]]


def build_fred_observations_url(
    series_id: str,
    api_key: str,
    observation_start: str | None = None,
    observation_end: str | None = None,
    frequency: str | None = None,
    aggregation_method: str | None = None,
    units: str = "lin",
    base_url: str = FRED_OBSERVATIONS_URL,
) -> str:
    """Build a FRED observations API URL for one documented series ID."""
    _validate_series_id(series_id)
    if not api_key:
        raise ValueError("FRED API key is required")

    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "units": units,
        "sort_order": "asc",
    }
    if observation_start:
        params["observation_start"] = observation_start
    if observation_end:
        params["observation_end"] = observation_end
    if frequency:
        params["frequency"] = frequency
    if aggregation_method:
        params["aggregation_method"] = aggregation_method

    return f"{base_url}?{urlencode(params)}"


def build_fred_graph_csv_url(
    series_id: str,
    observation_start: str | None = None,
    observation_end: str | None = None,
    base_url: str = FRED_GRAPH_CSV_URL,
) -> str:
    """Build a FRED graph CSV URL for local snapshot refreshes."""
    _validate_series_id(series_id)
    params = {"id": series_id}
    if observation_start:
        params["cosd"] = observation_start
    if observation_end:
        params["coed"] = observation_end
    return f"{base_url}?{urlencode(params)}"


def parse_fred_observations(payload: dict[str, Any]) -> pd.DataFrame:
    """Parse a FRED observations JSON payload into a `date,value` DataFrame."""
    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise ValueError("FRED payload is missing an observations list")

    rows: list[dict[str, object]] = []
    for observation in observations:
        if not isinstance(observation, dict):
            raise ValueError("FRED observation entries must be objects")
        value = observation.get("value")
        if value in (None, "."):
            continue
        rows.append(
            {
                "date": observation.get("date"),
                "value": value,
            }
        )

    df = pd.DataFrame(rows, columns=["date", "value"])
    if df.empty:
        return pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"), "value": pd.Series(dtype="float64")})

    try:
        df["date"] = pd.to_datetime(df["date"], errors="raise")
    except Exception as exc:
        raise ValueError("FRED payload contains invalid observation dates") from exc

    try:
        df["value"] = pd.to_numeric(df["value"], errors="raise")
    except Exception as exc:
        raise ValueError("FRED payload contains non-numeric observation values") from exc

    return df.sort_values("date").reset_index(drop=True)


def fetch_fred_observations(
    series_id: str,
    api_key: str | None = None,
    observation_start: str | None = None,
    observation_end: str | None = None,
    frequency: str | None = None,
    aggregation_method: str | None = None,
    units: str = "lin",
    transport: Transport | None = None,
) -> pd.DataFrame:
    """Fetch observations from FRED.

    Tests should pass a local fixture-backed `transport`; production use should
    provide `api_key` or set `FRED_API_KEY`.
    """
    resolved_api_key = api_key or os.getenv("FRED_API_KEY")
    if not resolved_api_key:
        raise ValueError("FRED API key is required; set FRED_API_KEY or pass api_key")

    url = build_fred_observations_url(
        series_id=series_id,
        api_key=resolved_api_key,
        observation_start=observation_start,
        observation_end=observation_end,
        frequency=frequency,
        aggregation_method=aggregation_method,
        units=units,
    )
    payload = transport(url) if transport is not None else _default_transport(url)
    return parse_fred_observations(payload)


def fetch_fred_graph_csv(
    series_id: str,
    observation_start: str | None = None,
    observation_end: str | None = None,
) -> pd.DataFrame:
    """Fetch FRED's public graph CSV and normalize it to `date,value`."""
    url = build_fred_graph_csv_url(
        series_id=series_id,
        observation_start=observation_start,
        observation_end=observation_end,
    )
    df = pd.read_csv(url)
    expected_columns = {"observation_date", series_id}
    missing_columns = expected_columns.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"FRED graph CSV is missing required column(s): {missing}")

    result = df[["observation_date", series_id]].rename(
        columns={"observation_date": "date", series_id: "value"}
    )
    result = result[result["value"].notna() & (result["value"] != ".")].copy()
    result["date"] = pd.to_datetime(result["date"], errors="raise")
    result["value"] = pd.to_numeric(result["value"], errors="raise")
    return result.sort_values("date").reset_index(drop=True)


def _default_transport(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _validate_series_id(series_id: str) -> None:
    if not _VALID_SERIES_ID.fullmatch(series_id):
        raise ValueError("FRED series_id may only contain letters, numbers, and underscores")
