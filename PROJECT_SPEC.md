# Macro Radar MVP Spec

## Goal

Build a local-first macroeconomic research dashboard that can load fixture CSV
or verified snapshot CSV time series, store them in DuckDB, compute simple transformations, evaluate
indicator zones, and display results in Streamlit.

## Scope

- Verified local snapshot CSV data for implemented dashboard indicators.
- Synthetic fixture data only in tests.
- Real FRED adapter for queued PR-A2 sources, with fixture-only tests.
- PR-A3 FRED snapshot refresh command and local snapshots for yield curve,
  real rates, and credit spreads.
- World Bank Pink Sheet commodity snapshots for copper, iron ore, sawnwood,
  gold, silver, and WTI.
- Local DuckDB time series storage.
- Basic transformations: MoM, YoY, rolling mean, z-score, percentile rank.
- Implemented indicators: M2, ISM manufacturing, ISM services, UMCSI, building permits,
  yield curve, real rates, credit spreads, and cyclical commodities.
- Conservative demo macro bias scoring.
- Streamlit UI with chart, table, source status, and bias summary.

## Non-goals

- No live data fetching in tests or the default UI path.
- Manual FRED adapter calls are allowed only when `FRED_API_KEY` is supplied from the environment.
- No scraping.
- No real API keys.
- No trading signals, broker integration, order execution, or investment advice.
- No machine learning.
- No PTM15, PTM16, portfolio management, or strategy backtesting.

## Modules

- `ingestion`: loads local CSV time series.
- `storage`: writes and reads time series in DuckDB.
- `transforms`: computes time series and statistical transformations.
- `indicators`: evaluates indicator status and zone.
- `scoring`: combines indicator results into a conservative macro bias.
- `ui`: presents the local dashboard.

## Data Contract

Snapshot and fixture CSV files must contain:

```text
date,value
2024-01-01,100
```

- `date` must parse as a datetime.
- `value` must parse as numeric.
- Returned data must be sorted by `date` ascending.

Implemented dashboard data must also have provenance in `source_registry.yaml`:

- `source_name`
- `source_url`
- `provenance_status`
- `retrieved_at`
- `observation_start`
- `observation_end`

## Indicator Contract

Every indicator result must expose:

- key
- name
- status
- latest_date
- latest_value
- zone
- explanation
- dataframe

Allowed zones are `Risk-On`, `Neutral`, `Risk-Off`, `Insufficient Data`, and
`Not Implemented`.

## Acceptance Criteria

- `pytest` passes.
- UI starts with `streamlit run macro_radar/ui/app.py`.
- Verified local snapshot series appear in the dashboard.
- Missing functionality does not crash and does not fake values.
- Documentation states the source and provenance for implemented snapshot data.
- FRED adapter tests use local fixtures or injected transports, never live requests.
- Refresh command can write local FRED snapshots when run explicitly by a user.

## Risks

- Static snapshots may be mistaken for current unrevised macro data.
- Indicator zones may be mistaken for trading signals.
- Future live adapters must avoid undocumented series IDs and unauthorized data.
- UI must show insufficient data instead of inventing values.
