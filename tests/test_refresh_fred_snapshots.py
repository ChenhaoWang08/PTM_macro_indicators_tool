from __future__ import annotations

import pandas as pd
import pytest
import yaml

from macro_radar.commands.refresh_fred_snapshots import (
    FredSnapshotResult,
    collect_fred_snapshot_specs,
    refresh_fred_snapshots,
    update_source_registry_file,
    update_source_registry_metadata,
)
from macro_radar.config import load_source_registry


def test_collect_fred_snapshot_specs_includes_pr_a3_series():
    registry = load_source_registry()

    specs = collect_fred_snapshot_specs(
        registry,
        ("yield_curve", "real_rates", "credit_spreads"),
    )

    assert [(spec.key, spec.series_id) for spec in specs] == [
        ("yield_curve", "T10Y2Y"),
        ("real_rates", "DFII10"),
        ("credit_spreads.investment_grade_oas", "BAMLC0A0CM"),
        ("credit_spreads.high_yield_oas", "BAMLH0A0HYM2"),
    ]


def test_collect_fred_snapshot_specs_skips_non_fred_commodities():
    registry = load_source_registry()

    with pytest.raises(ValueError, match="No FRED snapshot specs"):
        collect_fred_snapshot_specs(registry, ("commodities",))


def test_refresh_fred_snapshots_writes_date_value_csv_without_network(tmp_path):
    specs = collect_fred_snapshot_specs(load_source_registry(), ("yield_curve",))

    def fixture_fetcher(series_id: str, start: str | None, end: str | None) -> pd.DataFrame:
        assert series_id == "T10Y2Y"
        assert start == "2024-01-01"
        assert end == "2024-01-31"
        return pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
                "value": [0.25, 0.30],
            }
        )

    results = refresh_fred_snapshots(
        specs=specs,
        fetcher=fixture_fetcher,
        observation_start="2024-01-01",
        observation_end="2024-01-31",
        output_root=tmp_path,
    )

    output_path = tmp_path / specs[0].snapshot_path
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").splitlines() == [
        "date,value",
        "2024-01-02,0.25",
        "2024-01-03,0.3",
    ]
    assert results[0].rows == 2
    assert results[0].last_date == "2024-01-03"


def test_update_source_registry_metadata_updates_top_level_series():
    registry = {
        "yield_curve": {
            "snapshot_path": "data/official/yield_curve.csv",
            "retrieved_at": "2026-05-27",
            "observation_end": "2026-05-22",
        }
    }
    results = [
        FredSnapshotResult(
            key="yield_curve",
            series_id="T10Y2Y",
            snapshot_path="data/official/yield_curve.csv",
            rows=2,
            first_date="2026-05-22",
            last_date="2026-05-26",
        )
    ]

    updated = update_source_registry_metadata(registry, results, retrieved_at="2026-05-27")

    assert updated["yield_curve"]["retrieved_at"] == "2026-05-27"
    assert updated["yield_curve"]["observation_end"] == "2026-05-26"


def test_update_source_registry_metadata_updates_nested_credit_spread_series():
    registry = {
        "credit_spreads": {
            "snapshot_path": "data/official/credit_spreads_hy.csv",
            "retrieved_at": "2026-05-27",
            "observation_end": "2026-05-25",
            "additional_series": {
                "investment_grade_oas": {
                    "snapshot_path": "data/official/credit_spreads_ig.csv",
                },
                "high_yield_oas": {
                    "snapshot_path": "data/official/credit_spreads_hy.csv",
                },
            },
        }
    }
    results = [
        FredSnapshotResult(
            key="credit_spreads.investment_grade_oas",
            series_id="BAMLC0A0CM",
            snapshot_path="data/official/credit_spreads_ig.csv",
            rows=2,
            first_date="2026-05-26",
            last_date="2026-05-27",
        ),
        FredSnapshotResult(
            key="credit_spreads.high_yield_oas",
            series_id="BAMLH0A0HYM2",
            snapshot_path="data/official/credit_spreads_hy.csv",
            rows=2,
            first_date="2026-05-26",
            last_date="2026-05-27",
        ),
    ]

    updated = update_source_registry_metadata(registry, results, retrieved_at="2026-05-28")
    additional = updated["credit_spreads"]["additional_series"]

    assert updated["credit_spreads"]["retrieved_at"] == "2026-05-28"
    assert updated["credit_spreads"]["observation_end"] == "2026-05-27"
    assert additional["investment_grade_oas"]["retrieved_at"] == "2026-05-28"
    assert additional["investment_grade_oas"]["observation_end"] == "2026-05-27"
    assert additional["high_yield_oas"]["retrieved_at"] == "2026-05-28"
    assert additional["high_yield_oas"]["observation_end"] == "2026-05-27"


def test_update_source_registry_file_persists_metadata_changes(tmp_path):
    registry_path = tmp_path / "source_registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "real_rates": {
                    "snapshot_path": "data/official/real_rates.csv",
                    "retrieved_at": "2026-05-27",
                    "observation_end": "2026-05-21",
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    results = [
        FredSnapshotResult(
            key="real_rates",
            series_id="DFII10",
            snapshot_path="data/official/real_rates.csv",
            rows=2,
            first_date="2026-05-21",
            last_date="2026-05-26",
        )
    ]

    update_source_registry_file(
        registry_path,
        results,
        retrieved_at="2026-05-28",
    )

    updated = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    assert str(updated["real_rates"]["retrieved_at"]) == "2026-05-28"
    assert str(updated["real_rates"]["observation_end"]) == "2026-05-26"
