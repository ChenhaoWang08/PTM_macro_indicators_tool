from __future__ import annotations

from datetime import date

import pandas as pd

from macro_radar.config import load_source_registry
from macro_radar.indicators.base import IndicatorResult
from macro_radar.ui.app import (
    build_overview_table,
    build_provenance_table,
    build_refresh_action,
    build_refresh_status_table,
    build_stale_refresh_commands_table,
    calculate_days_since,
    format_indicator_date,
    format_indicator_value,
    format_observation_range,
    is_snapshot_stale,
    load_registry_dataframe,
)


def test_format_observation_range_handles_full_range():
    assert (
        format_observation_range(
            {
                "observation_start": "2024-01-01",
                "observation_end": "2024-12-01",
            }
        )
        == "2024-01-01 to 2024-12-01"
    )


def test_indicator_formatters_handle_missing_and_present_values():
    assert format_indicator_value(None) == "Insufficient data"
    assert format_indicator_value(2.345) == "2.35"
    assert format_indicator_date(None) == "No latest date"
    assert format_indicator_date(pd.Timestamp("2026-05-22")) == "2026-05-22"


def test_build_overview_table_contains_selected_indicator_summary():
    registry = load_source_registry()
    result = IndicatorResult(
        key="yield_curve",
        name="10Y-2Y Yield Curve Spread",
        status="implemented",
        latest_date=pd.Timestamp("2026-05-22"),
        latest_value=0.43,
        zone="Neutral",
        explanation="test",
        dataframe=None,
    )

    table = build_overview_table(result, registry["yield_curve"])
    overview = dict(zip(table["field"], table["value"], strict=True))

    assert overview["latest_date"] == "2026-05-22"
    assert overview["latest_value"] == "0.43"
    assert overview["zone"] == "Neutral"
    assert overview["status"] == "implemented"
    assert overview["source_name"] == "Federal Reserve Bank of St. Louis via FRED"
    assert overview["frequency"] == "daily"
    assert overview["unit"] == "percent"


def test_build_provenance_table_contains_required_fields_for_selected_indicator():
    registry = load_source_registry()
    table = build_provenance_table("yield_curve", registry["yield_curve"])

    provenance = dict(zip(table["field"], table["value"], strict=True))

    assert provenance["source_url"] == "https://fred.stlouisfed.org/series/T10Y2Y"
    assert provenance["series_id"] == "T10Y2Y"
    assert provenance["retrieved_at"] == "2026-05-27"
    assert provenance["observation_range"] == "2024-01-02 to 2026-05-22"
    assert "FRED-calculated spread" in provenance["rights_note"]


def test_build_provenance_table_includes_credit_spread_subseries():
    registry = load_source_registry()
    table = build_provenance_table("credit_spreads", registry["credit_spreads"])

    provenance = dict(zip(table["field"], table["value"], strict=True))

    assert provenance["series_id"] == "BAMLH0A0HYM2"
    assert provenance["high_yield_oas.series_id"] == "BAMLH0A0HYM2"
    assert provenance["investment_grade_oas.series_id"] == "BAMLC0A0CM"
    assert (
        provenance["investment_grade_oas.source_url"]
        == "https://fred.stlouisfed.org/series/BAMLC0A0CM"
    )


def test_build_provenance_table_includes_commodity_subseries():
    registry = load_source_registry()
    table = build_provenance_table("commodities", registry["commodities"])

    provenance = dict(zip(table["field"], table["value"], strict=True))

    assert provenance["series_id"] == "COPPER"
    assert provenance["gold.series_id"] == "GOLD"
    assert provenance["silver.unit"] == "usd_per_troy_ounce"
    assert provenance["lumber.series_id"] == "SAWNWD_MYS"
    assert "wood/lumber proxy" in provenance["lumber.rights_note"]


def test_refresh_status_table_lists_each_snapshot_once():
    registry = load_source_registry()
    table = build_refresh_status_table(registry, as_of=date(2026, 5, 27))

    assert len(table) == 15
    assert table["snapshot_path"].is_unique
    assert table["file_exists"].all()
    assert "data/official/credit_spreads_hy.csv" in table["snapshot_path"].tolist()
    assert "data/official/credit_spreads_ig.csv" in table["snapshot_path"].tolist()
    assert "data/official/commodity_gold.csv" in table["snapshot_path"].tolist()
    assert "refresh_action" in table.columns


def test_refresh_status_table_flags_stale_monthly_and_fresh_daily_snapshots():
    registry = load_source_registry()
    table = build_refresh_status_table(registry, as_of=date(2026, 5, 27))
    rows = table.set_index("indicator").to_dict(orient="index")

    assert rows["m2"]["appears_stale"] is True
    assert rows["m2"]["days_since_observation_end"] == 542
    assert rows["yield_curve"]["appears_stale"] is False
    assert rows["yield_curve"]["days_since_observation_end"] == 5
    assert rows["credit_spreads.investment_grade_oas"]["appears_stale"] is False
    assert rows["commodities"]["appears_stale"] is True
    assert rows["commodities"]["days_since_observation_end"] == 56


def test_refresh_action_uses_fred_command_for_fred_snapshots():
    registry = load_source_registry()

    assert build_refresh_action("m2", registry["m2"]) == (
        "python -m macro_radar.commands.refresh_fred_snapshots "
        "--transport graph-csv --series m2 --start 2023-12-01"
    )
    assert build_refresh_action("building_permits", registry["building_permits"]) == (
        "python -m macro_radar.commands.refresh_fred_snapshots "
        "--transport graph-csv --series building_permits --start 2024-01-01"
    )
    assert build_refresh_action("credit_spreads.investment_grade_oas", registry["credit_spreads"]) == (
        "python -m macro_radar.commands.refresh_fred_snapshots "
        "--transport graph-csv --series credit_spreads --start 2024-01-02"
    )


def test_refresh_action_documents_manual_release_snapshot_refresh():
    registry = load_source_registry()

    action = build_refresh_action("ism_manufacturing", registry["ism_manufacturing"])

    assert action.startswith("Manual refresh required:")
    assert "data/official/ism_manufacturing.csv" in action
    assert registry["ism_manufacturing"]["source_url"] in action


def test_refresh_action_documents_manual_world_bank_snapshot_refresh():
    registry = load_source_registry()

    action = build_refresh_action("commodities", registry["commodities"])

    assert action.startswith("Manual refresh required:")
    assert "data/official/commodity_copper.csv" in action
    assert "CMO-Historical-Data-Monthly.xlsx" in action


def test_stale_refresh_commands_table_groups_duplicate_actions():
    refresh_status = pd.DataFrame(
        [
            {
                "indicator": "credit_spreads",
                "appears_stale": True,
                "refresh_action": "refresh credit spreads",
            },
            {
                "indicator": "credit_spreads.investment_grade_oas",
                "appears_stale": True,
                "refresh_action": "refresh credit spreads",
            },
            {
                "indicator": "yield_curve",
                "appears_stale": False,
                "refresh_action": "refresh yield curve",
            },
        ]
    )

    table = build_stale_refresh_commands_table(refresh_status)

    assert table.to_dict(orient="records") == [
        {
            "refresh_action": "refresh credit spreads",
            "affected_snapshots": "credit_spreads, credit_spreads.investment_grade_oas",
        }
    ]


def test_stale_refresh_commands_table_for_current_stale_rows_points_to_commands():
    registry = load_source_registry()
    refresh_status = build_refresh_status_table(registry, as_of=date(2026, 5, 27))
    commands = build_stale_refresh_commands_table(refresh_status)

    command_text = "\n".join(commands["refresh_action"].tolist())
    assert "--series m2 --start 2023-12-01" in command_text
    assert "--series umcsi --start 2024-01-01" in command_text
    assert "--series building_permits --start 2024-01-01" in command_text
    assert "Manual refresh required: update data/official/ism_manufacturing.csv" in command_text
    assert "Manual refresh required: update data/official/commodity_copper.csv" in command_text


def test_load_registry_dataframe_loads_six_commodity_snapshots():
    registry = load_source_registry()

    df = load_registry_dataframe("commodities", registry["commodities"])

    assert set(df["commodity_key"]) == {"copper", "iron_ore", "lumber", "gold", "silver", "wti"}
    assert df.groupby("commodity_key").size().nunique() == 1
    assert df["date"].min().date().isoformat() == "2024-01-01"
    assert df["date"].max().date().isoformat() == "2026-04-01"


def test_stale_policy_helpers_are_explicit():
    assert calculate_days_since("2026-05-20", date(2026, 5, 27)) == 7
    assert is_snapshot_stale("daily", 7) is False
    assert is_snapshot_stale("daily", 8) is True
    assert is_snapshot_stale("monthly", 45) is False
    assert is_snapshot_stale("monthly", 46) is True
