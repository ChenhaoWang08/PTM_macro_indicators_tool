from __future__ import annotations

from macro_radar.config import PROJECT_ROOT, load_source_registry
from macro_radar.ingestion.csv_loader import load_time_series_csv

IMPLEMENTED_SOURCE_TYPES = {
    "official_snapshot_csv",
    "official_release_snapshot_csv",
}

FRED_READY_SERIES = {
    "m2": "M2SL",
    "yield_curve": "T10Y2Y",
    "real_rates": "DFII10",
    "credit_spreads": "BAMLH0A0HYM2",
}

COMMODITY_SERIES = {
    "copper": "COPPER",
    "iron_ore": "IRON_ORE",
    "lumber": "SAWNWD_MYS",
    "gold": "GOLD",
    "silver": "SILVER",
    "wti": "CRUDE_WTI",
}

REQUIRED_PROVENANCE_FIELDS = {
    "source_name",
    "source_url",
    "provenance_status",
    "retrieved_at",
    "observation_start",
    "observation_end",
}


def test_implemented_registry_entries_use_verified_snapshot_sources():
    registry = load_source_registry()

    implemented = {
        key: metadata for key, metadata in registry.items() if metadata["status"] == "implemented"
    }

    assert implemented
    for key, metadata in implemented.items():
        assert metadata["source_type"] in IMPLEMENTED_SOURCE_TYPES, key
        assert "fixture" not in metadata["source_type"], key
        assert metadata["snapshot_path"], key
        assert (PROJECT_ROOT / metadata["snapshot_path"]).exists(), key
        for field in REQUIRED_PROVENANCE_FIELDS:
            assert metadata[field], f"{key} missing {field}"


def test_implemented_registry_snapshot_date_ranges_match_files():
    registry = load_source_registry()

    for key, metadata in registry.items():
        if metadata["status"] != "implemented" or metadata["source_type"] != "official_snapshot_csv":
            continue
        df = load_time_series_csv(PROJECT_ROOT / metadata["snapshot_path"])
        assert df["date"].iloc[0].date().isoformat() == str(metadata["observation_start"]), key
        assert df["date"].iloc[-1].date().isoformat() == str(metadata["observation_end"]), key


def test_pr_a2_fred_sources_are_registered_with_documented_series_ids():
    registry = load_source_registry()

    for key, series_id in FRED_READY_SERIES.items():
        metadata = registry[key]
        assert metadata["series_id"] == series_id
        assert metadata["source_url"].endswith(f"/series/{series_id}")
        assert metadata["api_endpoint"] == "https://api.stlouisfed.org/fred/series/observations"

    credit_spreads = registry["credit_spreads"]["additional_series"]
    assert credit_spreads["investment_grade_oas"]["series_id"] == "BAMLC0A0CM"
    assert credit_spreads["high_yield_oas"]["series_id"] == "BAMLH0A0HYM2"


def test_commodities_registers_world_bank_snapshot_series():
    registry = load_source_registry()
    commodities = registry["commodities"]

    assert commodities["status"] == "implemented"
    assert commodities["adapter_source_type"] == "world_bank_pink_sheet_xlsx"
    assert set(commodities["additional_series"]) == set(COMMODITY_SERIES)

    for key, series_id in COMMODITY_SERIES.items():
        metadata = commodities["additional_series"][key]
        assert metadata["series_id"] == series_id
        snapshot_path = PROJECT_ROOT / metadata["snapshot_path"]
        assert snapshot_path.exists()
        df = load_time_series_csv(snapshot_path)
        assert df["date"].iloc[0].date().isoformat() == str(metadata["observation_start"])
        assert df["date"].iloc[-1].date().isoformat() == str(metadata["observation_end"])
