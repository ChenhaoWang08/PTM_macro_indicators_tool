from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd
import yaml

from macro_radar.config import PROJECT_ROOT, SOURCE_REGISTRY_PATH, load_source_registry
from macro_radar.ingestion.fred import fetch_fred_graph_csv, fetch_fred_observations

DEFAULT_REFRESH_KEYS = ("yield_curve", "real_rates", "credit_spreads")

FredFetcher = Callable[[str, str | None, str | None], pd.DataFrame]


@dataclass(frozen=True)
class FredSnapshotSpec:
    key: str
    series_id: str
    snapshot_path: Path


@dataclass(frozen=True)
class FredSnapshotResult:
    key: str
    series_id: str
    snapshot_path: Path
    rows: int
    first_date: str
    last_date: str


def collect_fred_snapshot_specs(
    registry: dict[str, dict],
    keys: tuple[str, ...] = DEFAULT_REFRESH_KEYS,
) -> list[FredSnapshotSpec]:
    specs: list[FredSnapshotSpec] = []
    for key in keys:
        if key not in registry:
            raise ValueError(f"Unknown registry key: {key}")

        metadata = registry[key]
        additional_series = metadata.get("additional_series") or {}
        series_id = metadata.get("series_id")
        snapshot_path = metadata.get("snapshot_path")
        if series_id and snapshot_path and not additional_series and _is_fred_metadata(metadata):
            specs.append(
                FredSnapshotSpec(
                    key=key,
                    series_id=str(series_id),
                    snapshot_path=Path(str(snapshot_path)),
                )
            )

        for subkey, submetadata in additional_series.items():
            sub_series_id = submetadata.get("series_id")
            sub_snapshot_path = submetadata.get("snapshot_path")
            if sub_series_id and sub_snapshot_path and _is_fred_metadata(submetadata):
                specs.append(
                    FredSnapshotSpec(
                        key=f"{key}.{subkey}",
                        series_id=str(sub_series_id),
                        snapshot_path=Path(str(sub_snapshot_path)),
                    )
                )

    if not specs:
        raise ValueError("No FRED snapshot specs found for requested keys")
    return specs


def refresh_fred_snapshots(
    specs: list[FredSnapshotSpec],
    fetcher: FredFetcher,
    observation_start: str | None = None,
    observation_end: str | None = None,
    output_root: Path = PROJECT_ROOT,
) -> list[FredSnapshotResult]:
    results: list[FredSnapshotResult] = []
    for spec in specs:
        df = fetcher(spec.series_id, observation_start, observation_end)
        _validate_snapshot_frame(spec, df)

        output_path = output_root / spec.snapshot_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df[["date", "value"]].to_csv(output_path, index=False, date_format="%Y-%m-%d")

        results.append(
            FredSnapshotResult(
                key=spec.key,
                series_id=spec.series_id,
                snapshot_path=spec.snapshot_path,
                rows=len(df),
                first_date=pd.to_datetime(df["date"].iloc[0]).date().isoformat(),
                last_date=pd.to_datetime(df["date"].iloc[-1]).date().isoformat(),
            )
        )
    return results


def update_source_registry_metadata(
    registry: dict[str, dict],
    results: list[FredSnapshotResult],
    retrieved_at: str,
) -> dict[str, dict]:
    for result in results:
        key_parts = result.key.split(".", maxsplit=1)
        parent_key = key_parts[0]
        if parent_key not in registry:
            raise ValueError(f"Refresh result references unknown registry key: {parent_key}")

        parent_metadata = registry[parent_key]
        if len(key_parts) == 1:
            parent_metadata["retrieved_at"] = retrieved_at
            parent_metadata["observation_end"] = result.last_date
            continue

        subkey = key_parts[1]
        additional_series = parent_metadata.get("additional_series")
        if not isinstance(additional_series, dict) or subkey not in additional_series:
            raise ValueError(f"Refresh result references unknown additional series: {result.key}")

        submetadata = additional_series[subkey]
        submetadata["retrieved_at"] = retrieved_at
        submetadata["observation_end"] = result.last_date
        parent_metadata["retrieved_at"] = retrieved_at

        parent_snapshot_path = parent_metadata.get("snapshot_path")
        if parent_snapshot_path and _same_path(parent_snapshot_path, result.snapshot_path):
            parent_metadata["observation_end"] = result.last_date

    return registry


def update_source_registry_file(
    registry_path: Path,
    results: list[FredSnapshotResult],
    retrieved_at: str,
) -> dict[str, dict]:
    with registry_path.open("r", encoding="utf-8") as file:
        registry = yaml.safe_load(file) or {}

    updated_registry = update_source_registry_metadata(registry, results, retrieved_at)

    with registry_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(updated_registry, file, sort_keys=False, allow_unicode=True)

    return updated_registry


def build_fetcher(transport: str, api_key: str | None = None) -> FredFetcher:
    if transport == "graph-csv":
        return fetch_fred_graph_csv
    if transport == "api":
        return lambda series_id, start, end: fetch_fred_observations(
            series_id=series_id,
            api_key=api_key,
            observation_start=start,
            observation_end=end,
        )
    raise ValueError(f"Unsupported transport: {transport}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Refresh local FRED snapshot CSV files.")
    parser.add_argument(
        "--series",
        nargs="+",
        default=list(DEFAULT_REFRESH_KEYS),
        help="Registry keys to refresh. Defaults to PR-A3 FRED keys.",
    )
    parser.add_argument("--start", default="2024-01-01", help="Observation start date.")
    parser.add_argument("--end", default=None, help="Observation end date.")
    parser.add_argument(
        "--registry-path",
        default=str(SOURCE_REGISTRY_PATH),
        help="Path to source_registry.yaml to update after snapshots are written.",
    )
    parser.add_argument(
        "--skip-registry-update",
        action="store_true",
        help="Write snapshot CSVs without updating source_registry.yaml metadata.",
    )
    parser.add_argument(
        "--transport",
        choices=("api", "graph-csv"),
        default="api",
        help="Use FRED API with FRED_API_KEY, or public FRED graph CSV.",
    )
    parser.add_argument("--api-key", default=None, help="Optional FRED API key override.")
    args = parser.parse_args(argv)

    registry = load_source_registry()
    specs = collect_fred_snapshot_specs(registry, tuple(args.series))
    fetcher = build_fetcher(args.transport, args.api_key)
    results = refresh_fred_snapshots(
        specs=specs,
        fetcher=fetcher,
        observation_start=args.start,
        observation_end=args.end,
    )

    today = date.today().isoformat()
    if not args.skip_registry_update:
        update_source_registry_file(Path(args.registry_path), results, today)

    print(f"Refreshed {len(results)} FRED snapshot(s) on {today}:")
    for result in results:
        print(
            f"- {result.key} [{result.series_id}] -> {result.snapshot_path} "
            f"({result.rows} rows, {result.first_date} to {result.last_date})"
        )
    if args.skip_registry_update:
        print("Skipped source_registry.yaml metadata update.")
    else:
        print(f"Updated source registry metadata: {args.registry_path}")


def _validate_snapshot_frame(spec: FredSnapshotSpec, df: pd.DataFrame) -> None:
    required_columns = {"date", "value"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"{spec.key} snapshot is missing required column(s): {missing}")
    if df.empty:
        raise ValueError(f"{spec.key} snapshot returned no rows")
    if df["value"].isna().any():
        raise ValueError(f"{spec.key} snapshot contains missing values")


def _same_path(left: object, right: object) -> bool:
    return Path(str(left)).as_posix() == Path(str(right)).as_posix()


def _is_fred_metadata(metadata: dict) -> bool:
    source_url = str(metadata.get("source_url") or "")
    return "fred.stlouisfed.org/series/" in source_url


if __name__ == "__main__":
    main()
