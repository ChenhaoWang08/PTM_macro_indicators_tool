from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd
import plotly.express as px
import streamlit as st

from macro_radar.config import PROJECT_ROOT, load_source_registry
from macro_radar.indicators.base import IndicatorResult
from macro_radar.indicators.building_permits import evaluate_building_permits
from macro_radar.indicators.commodities import evaluate_commodities
from macro_radar.indicators.credit_spreads import evaluate_credit_spreads
from macro_radar.indicators.ism import evaluate_ism_manufacturing, evaluate_ism_services
from macro_radar.indicators.m2 import evaluate_m2
from macro_radar.indicators.rates import evaluate_real_rates, evaluate_yield_curve
from macro_radar.indicators.stubs import not_implemented_indicator
from macro_radar.indicators.umcsi import evaluate_umcsi
from macro_radar.ingestion.csv_loader import load_time_series_csv
from macro_radar.scoring.macro_bias import combine_indicator_results

Evaluator = Callable[[pd.DataFrame], IndicatorResult]

EVALUATORS: dict[str, Evaluator] = {
    "m2": evaluate_m2,
    "ism_manufacturing": evaluate_ism_manufacturing,
    "ism_services": evaluate_ism_services,
    "umcsi": evaluate_umcsi,
    "building_permits": evaluate_building_permits,
    "yield_curve": evaluate_yield_curve,
    "real_rates": evaluate_real_rates,
    "credit_spreads": evaluate_credit_spreads,
    "commodities": evaluate_commodities,
}

LOADABLE_SOURCE_TYPES = {
    "official_snapshot_csv",
    "official_release_snapshot_csv",
}

REQUIRED_PROVENANCE_FIELDS = {
    "source_name",
    "source_url",
    "provenance_status",
    "retrieved_at",
    "observation_start",
    "observation_end",
}

STALE_THRESHOLDS_DAYS = {
    "daily": 7,
    "monthly": 45,
}

COMMODITY_SERIES_ORDER = (
    "copper",
    "iron_ore",
    "lumber",
    "gold",
    "silver",
    "wti",
)


def evaluate_registry_indicator(key: str, metadata: dict[str, object]) -> IndicatorResult:
    name = str(metadata.get("name", key))
    status = metadata.get("status")
    source_type = metadata.get("source_type")
    data_path = metadata.get("snapshot_path")
    evaluator = EVALUATORS.get(key)

    if status != "implemented" or evaluator is None:
        return not_implemented_indicator(key, name)

    missing_provenance = sorted(
        field for field in REQUIRED_PROVENANCE_FIELDS if not metadata.get(field)
    )
    if source_type not in LOADABLE_SOURCE_TYPES or not data_path or missing_provenance:
        details = ", ".join(missing_provenance) if missing_provenance else "valid source type/path"
        return IndicatorResult(
            key=key,
            name=name,
            status="implemented",
            latest_date=None,
            latest_value=None,
            zone="Insufficient Data",
            explanation=f"Source registry is missing verified provenance: {details}",
            dataframe=None,
        )

    try:
        df = load_registry_dataframe(key, metadata)
    except ValueError as exc:
        return IndicatorResult(
            key=key,
            name=name,
            status="implemented",
            latest_date=None,
            latest_value=None,
            zone="Insufficient Data",
            explanation=f"Data quality issue: {exc}",
            dataframe=None,
        )

    return evaluator(df)


def load_registry_dataframe(key: str, metadata: dict[str, object]) -> pd.DataFrame:
    if key == "credit_spreads":
        return load_credit_spreads_dataframe(metadata)
    if key == "commodities":
        return load_commodities_dataframe(metadata)
    return load_time_series_csv(PROJECT_ROOT / str(metadata["snapshot_path"]))


def load_credit_spreads_dataframe(metadata: dict[str, object]) -> pd.DataFrame:
    additional_series = metadata.get("additional_series")
    if not isinstance(additional_series, dict):
        raise ValueError("credit_spreads is missing additional_series")

    frames: list[pd.DataFrame] = []
    for column_name in ("high_yield_oas", "investment_grade_oas"):
        series_metadata = additional_series.get(column_name)
        if not isinstance(series_metadata, dict) or not series_metadata.get("snapshot_path"):
            raise ValueError(f"credit_spreads is missing {column_name} snapshot_path")
        frame = load_time_series_csv(PROJECT_ROOT / str(series_metadata["snapshot_path"]))
        frames.append(frame.rename(columns={"value": column_name}))

    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="date", how="inner")
    if merged.empty:
        raise ValueError("credit_spreads snapshots have no overlapping dates")
    return merged.sort_values("date").reset_index(drop=True)


def load_commodities_dataframe(metadata: dict[str, object]) -> pd.DataFrame:
    additional_series = metadata.get("additional_series")
    if not isinstance(additional_series, dict):
        raise ValueError("commodities is missing additional_series")

    frames: list[pd.DataFrame] = []
    for series_key in COMMODITY_SERIES_ORDER:
        series_metadata = additional_series.get(series_key)
        if not isinstance(series_metadata, dict) or not series_metadata.get("snapshot_path"):
            raise ValueError(f"commodities is missing {series_key} snapshot_path")
        frame = load_time_series_csv(PROJECT_ROOT / str(series_metadata["snapshot_path"]))
        frame["commodity_key"] = series_key
        frame["commodity"] = str(series_metadata.get("name", series_key))
        frame["unit"] = str(series_metadata.get("unit", metadata.get("unit", "mixed")))
        frame["series_id"] = str(series_metadata.get("series_id", "Not available"))
        frames.append(frame)

    if not frames:
        raise ValueError("commodities has no loadable snapshots")
    return pd.concat(frames, ignore_index=True).sort_values(
        ["commodity_key", "date"]
    ).reset_index(drop=True)


def build_registry_table(registry: dict[str, dict[str, object]]) -> pd.DataFrame:
    rows = []
    for key, metadata in registry.items():
        rows.append(
            {
                "key": key,
                "name": metadata.get("name"),
                "source_type": metadata.get("source_type"),
                "source_name": metadata.get("source_name"),
                "series_id": metadata.get("series_id"),
                "frequency": metadata.get("frequency"),
                "unit": metadata.get("unit"),
                "status": metadata.get("status"),
                "provenance_status": metadata.get("provenance_status"),
                "retrieved_at": metadata.get("retrieved_at"),
            }
        )
    return pd.DataFrame(rows)


def build_provenance_table(key: str, metadata: dict[str, object]) -> pd.DataFrame:
    rows = [
        {
            "field": "indicator",
            "value": key,
        },
        {
            "field": "source_url",
            "value": format_metadata_value(metadata.get("source_url")),
        },
        {
            "field": "series_id",
            "value": format_metadata_value(metadata.get("series_id")),
        },
        {
            "field": "retrieved_at",
            "value": format_metadata_value(metadata.get("retrieved_at")),
        },
        {
            "field": "observation_range",
            "value": format_observation_range(metadata),
        },
        {
            "field": "rights_note",
            "value": format_metadata_value(metadata.get("rights_note")),
        },
    ]

    additional_series = metadata.get("additional_series")
    if isinstance(additional_series, dict):
        for series_key, series_metadata in additional_series.items():
            if not isinstance(series_metadata, dict):
                continue
            rows.extend(
                [
                    {
                        "field": f"{series_key}.series_id",
                        "value": format_metadata_value(series_metadata.get("series_id")),
                    },
                    {
                        "field": f"{series_key}.source_url",
                        "value": format_metadata_value(series_metadata.get("source_url")),
                    },
                    {
                        "field": f"{series_key}.snapshot_path",
                        "value": format_metadata_value(series_metadata.get("snapshot_path")),
                    },
                    {
                        "field": f"{series_key}.retrieved_at",
                        "value": format_metadata_value(series_metadata.get("retrieved_at")),
                    },
                    {
                        "field": f"{series_key}.observation_range",
                        "value": format_observation_range(series_metadata),
                    },
                    {
                        "field": f"{series_key}.unit",
                        "value": format_metadata_value(series_metadata.get("unit")),
                    },
                    {
                        "field": f"{series_key}.rights_note",
                        "value": format_metadata_value(series_metadata.get("rights_note")),
                    },
                ]
            )

    return pd.DataFrame(rows)


def build_refresh_status_table(
    registry: dict[str, dict[str, object]],
    as_of: date | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    effective_as_of = as_of or date.today()

    for key, metadata in registry.items():
        if metadata.get("status") != "implemented":
            continue

        snapshot_path = metadata.get("snapshot_path")
        if snapshot_path:
            path_text = str(snapshot_path)
            seen_paths.add(path_text)
            rows.append(
                build_refresh_status_row(
                    key=key,
                    metadata=metadata,
                    snapshot_path=path_text,
                    as_of=effective_as_of,
                )
            )

        additional_series = metadata.get("additional_series")
        if not isinstance(additional_series, dict):
            continue
        for series_key, series_metadata in additional_series.items():
            if not isinstance(series_metadata, dict):
                continue
            sub_snapshot_path = series_metadata.get("snapshot_path")
            if not sub_snapshot_path:
                continue
            path_text = str(sub_snapshot_path)
            if path_text in seen_paths:
                continue
            seen_paths.add(path_text)
            rows.append(
                build_refresh_status_row(
                    key=f"{key}.{series_key}",
                    metadata={**metadata, **series_metadata},
                    snapshot_path=path_text,
                    as_of=effective_as_of,
                )
            )

    return pd.DataFrame(rows)


def build_refresh_status_row(
    key: str,
    metadata: dict[str, object],
    snapshot_path: str,
    as_of: date,
) -> dict[str, object]:
    observation_end = metadata.get("observation_end")
    retrieved_at = metadata.get("retrieved_at")
    frequency = format_metadata_value(metadata.get("frequency"))
    days_since_end = calculate_days_since(observation_end, as_of)
    appears_stale = is_snapshot_stale(frequency, days_since_end)

    return {
        "indicator": key,
        "snapshot_path": snapshot_path,
        "file_exists": (PROJECT_ROOT / Path(snapshot_path)).exists(),
        "retrieved_at": format_metadata_value(retrieved_at),
        "observation_end": format_metadata_value(observation_end),
        "frequency": frequency,
        "days_since_observation_end": days_since_end,
        "appears_stale": appears_stale,
        "stale_reason": build_stale_reason(frequency, days_since_end, appears_stale),
        "refresh_action": build_refresh_action(key, metadata),
    }


def build_refresh_action(key: str, metadata: dict[str, object]) -> str:
    if is_fred_refreshable(metadata):
        refresh_key = key.split(".")[0]
        observation_start = metadata.get("observation_start") or "2024-01-01"
        return (
            "python -m macro_radar.commands.refresh_fred_snapshots "
            f"--transport graph-csv --series {refresh_key} --start {observation_start}"
        )

    source_url = metadata.get("source_url")
    download_url = metadata.get("download_url")
    snapshot_path = metadata.get("snapshot_path")
    if metadata.get("source_type") == "official_release_snapshot_csv" and source_url and snapshot_path:
        return (
            f"Manual refresh required: update {snapshot_path} from {source_url}; "
            "then update source_registry.yaml retrieved_at and observation_end."
        )
    if metadata.get("source_type") == "official_snapshot_csv" and snapshot_path and (
        source_url or download_url
    ):
        source = download_url or source_url
        return (
            f"Manual refresh required: update {snapshot_path} from {source}; "
            "then update source_registry.yaml retrieved_at and observation_end."
        )

    return "No refresh action documented yet."


def is_fred_refreshable(metadata: dict[str, object]) -> bool:
    source_url = str(metadata.get("source_url") or "")
    return bool(metadata.get("series_id") and "fred.stlouisfed.org/series/" in source_url)


def build_stale_refresh_commands_table(refresh_status_table: pd.DataFrame) -> pd.DataFrame:
    if refresh_status_table.empty:
        return pd.DataFrame(columns=["refresh_action", "affected_snapshots"])

    stale_rows = refresh_status_table[refresh_status_table["appears_stale"].eq(True)]
    if stale_rows.empty:
        return pd.DataFrame(columns=["refresh_action", "affected_snapshots"])

    rows: list[dict[str, str]] = []
    for refresh_action, group in stale_rows.groupby("refresh_action", sort=False):
        rows.append(
            {
                "refresh_action": str(refresh_action),
                "affected_snapshots": ", ".join(group["indicator"].astype(str).tolist()),
            }
        )
    return pd.DataFrame(rows)


def calculate_days_since(value: object, as_of: date) -> int | None:
    if not value:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return (as_of - parsed.date()).days


def is_snapshot_stale(frequency: str, days_since_end: int | None) -> bool:
    if days_since_end is None:
        return True
    threshold = STALE_THRESHOLDS_DAYS.get(frequency)
    if threshold is None:
        return False
    return days_since_end > threshold


def build_stale_reason(
    frequency: str,
    days_since_end: int | None,
    appears_stale: bool,
) -> str:
    if days_since_end is None:
        return "Missing or invalid observation_end"
    threshold = STALE_THRESHOLDS_DAYS.get(frequency)
    if threshold is None:
        return f"No stale threshold for {frequency}"
    status = "stale" if appears_stale else "fresh"
    return f"{status}: {days_since_end} days since observation_end; threshold {threshold} days"


def format_observation_range(metadata: dict[str, object]) -> str:
    start = metadata.get("observation_start")
    end = metadata.get("observation_end")
    if not start and not end:
        return "Not available"
    if not start:
        return f"through {end}"
    if not end:
        return f"from {start}"
    return f"{start} to {end}"


def format_metadata_value(value: object) -> str:
    if value is None or value == "":
        return "Not available"
    return str(value)


def build_overview_table(
    result: IndicatorResult, metadata: dict[str, object]
) -> pd.DataFrame:
    rows = [
        {"field": "latest_date", "value": format_indicator_date(result.latest_date)},
        {"field": "latest_value", "value": format_indicator_value(result.latest_value)},
        {"field": "zone", "value": result.zone},
        {"field": "status", "value": result.status},
        {"field": "source_name", "value": format_metadata_value(metadata.get("source_name"))},
        {"field": "frequency", "value": format_metadata_value(metadata.get("frequency"))},
        {"field": "unit", "value": format_metadata_value(metadata.get("unit"))},
    ]
    return pd.DataFrame(rows)


def format_indicator_value(value: float | None) -> str:
    if value is None:
        return "Insufficient data"
    return f"{value:.2f}"


def format_indicator_date(value: object) -> str:
    if value is None:
        return "No latest date"
    return pd.to_datetime(value).date().isoformat()


def render_chart_tab(result: IndicatorResult) -> None:
    if result.dataframe is None or result.dataframe.empty:
        st.info(result.zone)
        return

    if result.key == "commodities":
        render_commodities_charts(result.dataframe)
        return

    y_columns = get_chart_y_columns(result.dataframe)
    chart = px.line(
        result.dataframe,
        x="date",
        y=y_columns,
        title=f"{result.name} Verified Snapshot Series",
        markers=True,
    )
    st.plotly_chart(chart, use_container_width=True)


def render_data_tab(result: IndicatorResult) -> None:
    if result.dataframe is None or result.dataframe.empty:
        st.info(result.zone)
        return

    if result.key == "commodities":
        render_commodities_tables(result.dataframe)
        return

    st.dataframe(result.dataframe, use_container_width=True, hide_index=True)


def render_commodities_charts(df: pd.DataFrame) -> None:
    columns = st.columns(2)
    for index, (label, frame) in enumerate(iter_commodity_frames(df)):
        with columns[index % 2]:
            unit = frame["unit"].iloc[-1] if "unit" in frame.columns else "value"
            chart = px.line(
                frame,
                x="date",
                y="value",
                title=f"{label} ({unit})",
                markers=True,
            )
            st.plotly_chart(chart, use_container_width=True)


def render_commodities_tables(df: pd.DataFrame) -> None:
    display_columns = [
        column
        for column in ("date", "value", "six_month_pct", "unit", "series_id")
        if column in df.columns
    ]
    for label, frame in iter_commodity_frames(df):
        with st.expander(label, expanded=True):
            st.dataframe(
                frame[display_columns].sort_values("date", ascending=False),
                use_container_width=True,
                hide_index=True,
            )


def iter_commodity_frames(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    frames = []
    for series_key in COMMODITY_SERIES_ORDER:
        frame = df[df["commodity_key"].eq(series_key)].sort_values("date")
        if frame.empty:
            continue
        label = str(frame["commodity"].iloc[-1])
        frames.append((label, frame))
    return frames


def main() -> None:
    st.set_page_config(page_title="Macro Radar MVP", layout="wide")
    registry = load_source_registry()
    results = {
        key: evaluate_registry_indicator(key, metadata) for key, metadata in registry.items()
    }
    summary = combine_indicator_results(list(results.values()))

    st.title("Macro Radar MVP")
    st.write("Local-first macroeconomic research dashboard.")
    st.write("Verified local snapshots for implemented indicators.")
    st.write("Not investment advice.")

    registry_table = build_registry_table(registry)
    selected_key = st.sidebar.selectbox(
        "Indicator",
        options=list(registry.keys()),
        format_func=lambda key: str(registry[key].get("name", key)),
    )
    st.sidebar.subheader("Source Registry")
    st.sidebar.dataframe(registry_table, use_container_width=True, hide_index=True)

    st.subheader("Current Macro Bias")
    col_bias, col_on, col_neutral, col_off = st.columns(4)
    col_bias.metric("Bias", str(summary["bias"]), delta=f"Score {summary['score']}")
    col_on.metric("Risk-On", int(summary["risk_on_count"]))
    col_neutral.metric("Neutral", int(summary["neutral_count"]))
    col_off.metric("Risk-Off", int(summary["risk_off_count"]))

    st.subheader("Indicator Cards")
    implemented_results = [
        result for result in results.values() if result.status == "implemented"
    ]
    card_columns = st.columns(4)
    for index, result in enumerate(implemented_results):
        with card_columns[index % 4]:
            latest_text = (
                "Insufficient data"
                if result.latest_value is None
                else f"{result.latest_value:.2f}"
            )
            date_text = (
                ""
                if result.latest_date is None
                else pd.to_datetime(result.latest_date).date().isoformat()
            )
            st.metric(result.name, latest_text, delta=result.zone, help=date_text)

    st.subheader("Refresh Status")
    refresh_status_table = build_refresh_status_table(registry)
    st.dataframe(
        refresh_status_table,
        use_container_width=True,
        hide_index=True,
    )
    stale_commands_table = build_stale_refresh_commands_table(refresh_status_table)
    if stale_commands_table.empty:
        st.success("All documented snapshots are fresh under the current stale policy.")
    else:
        st.subheader("Stale Snapshot Refresh Commands")
        st.dataframe(stale_commands_table, use_container_width=True, hide_index=True)
        for command in stale_commands_table["refresh_action"].tolist():
            st.code(str(command), language="powershell")

    selected_result = results[selected_key]
    selected_metadata = registry[selected_key]
    st.subheader(selected_result.name)
    overview_tab, chart_tab, data_tab, provenance_tab = st.tabs(
        ["Overview", "Chart", "Data", "Provenance"]
    )

    with overview_tab:
        col_value, col_zone, col_status = st.columns(3)
        col_value.metric(
            "Latest Value",
            format_indicator_value(selected_result.latest_value),
            help=format_indicator_date(selected_result.latest_date),
        )
        col_zone.metric("Zone", selected_result.zone)
        col_status.metric("Status", selected_result.status)
        st.write(selected_result.explanation)
        st.dataframe(
            build_overview_table(selected_result, selected_metadata),
            use_container_width=True,
            hide_index=True,
        )

    with chart_tab:
        render_chart_tab(selected_result)

    with data_tab:
        render_data_tab(selected_result)

    with provenance_tab:
        source_url = selected_metadata.get("source_url")
        if source_url:
            st.link_button("Open Source", str(source_url))
        st.dataframe(
            build_provenance_table(selected_key, selected_metadata),
            use_container_width=True,
            hide_index=True,
        )


def get_chart_y_columns(df: pd.DataFrame) -> str | list[str]:
    preferred_columns = ["high_yield_oas", "investment_grade_oas"]
    available = [column for column in preferred_columns if column in df.columns]
    if available:
        return available
    return "value"


if __name__ == "__main__":
    main()
