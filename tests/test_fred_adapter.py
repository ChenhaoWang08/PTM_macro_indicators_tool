from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from macro_radar.ingestion.fred import (
    PR_A2_FRED_SERIES,
    build_fred_graph_csv_url,
    build_fred_observations_url,
    fetch_fred_graph_csv,
    fetch_fred_observations,
    parse_fred_observations,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_pr_a2_series_ids_are_documented_in_adapter():
    assert PR_A2_FRED_SERIES["m2"].series_id == "M2SL"
    assert PR_A2_FRED_SERIES["yield_curve"].series_id == "T10Y2Y"
    assert PR_A2_FRED_SERIES["real_rates"].series_id == "DFII10"
    assert PR_A2_FRED_SERIES["credit_spreads_hy"].series_id == "BAMLH0A0HYM2"
    assert PR_A2_FRED_SERIES["credit_spreads_ig"].series_id == "BAMLC0A0CM"


def test_build_fred_observations_url_contains_expected_parameters():
    url = build_fred_observations_url(
        series_id="M2SL",
        api_key="test_key",
        observation_start="2024-01-01",
        observation_end="2024-12-01",
        frequency="m",
        aggregation_method="eop",
    )
    query = parse_qs(urlparse(url).query)

    assert query["series_id"] == ["M2SL"]
    assert query["api_key"] == ["test_key"]
    assert query["file_type"] == ["json"]
    assert query["sort_order"] == ["asc"]
    assert query["observation_start"] == ["2024-01-01"]
    assert query["observation_end"] == ["2024-12-01"]
    assert query["frequency"] == ["m"]
    assert query["aggregation_method"] == ["eop"]


def test_build_fred_observations_url_rejects_invalid_series_id():
    with pytest.raises(ValueError, match="series_id"):
        build_fred_observations_url("BAD-ID", api_key="test_key")


def test_build_fred_graph_csv_url_contains_expected_parameters():
    url = build_fred_graph_csv_url(
        series_id="T10Y2Y",
        observation_start="2024-01-01",
        observation_end="2024-12-31",
    )
    query = parse_qs(urlparse(url).query)

    assert query["id"] == ["T10Y2Y"]
    assert query["cosd"] == ["2024-01-01"]
    assert query["coed"] == ["2024-12-31"]


def test_parse_fred_observations_returns_date_value_dataframe_and_skips_missing_values():
    payload = _load_fixture("fred_observations_m2.json")

    df = parse_fred_observations(payload)

    assert list(df.columns) == ["date", "value"]
    assert df["date"].tolist() == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-03-01")]
    assert df["value"].tolist() == [20843.9, 20973.9]


def test_fetch_fred_observations_uses_fixture_transport_without_network():
    payload = _load_fixture("fred_observations_m2.json")
    requested_urls: list[str] = []

    def fixture_transport(url: str) -> dict:
        requested_urls.append(url)
        return payload

    df = fetch_fred_observations(
        series_id="M2SL",
        api_key="test_key",
        observation_start="2024-01-01",
        observation_end="2024-03-01",
        transport=fixture_transport,
    )

    assert len(requested_urls) == 1
    assert "series_id=M2SL" in requested_urls[0]
    assert df["value"].tolist() == [20843.9, 20973.9]


def test_fetch_fred_observations_requires_api_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)

    with pytest.raises(ValueError, match="FRED API key"):
        fetch_fred_observations(series_id="M2SL", transport=lambda _url: {})


def test_fetch_fred_graph_csv_normalizes_and_drops_missing_values(monkeypatch):
    raw = pd.DataFrame(
        {
            "observation_date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "T10Y2Y": [0.25, None, 0.30],
        }
    )
    monkeypatch.setattr(pd, "read_csv", lambda _url: raw)

    df = fetch_fred_graph_csv("T10Y2Y", observation_start="2024-01-01")

    assert df["date"].tolist() == [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-04")]
    assert df["value"].tolist() == [0.25, 0.30]
