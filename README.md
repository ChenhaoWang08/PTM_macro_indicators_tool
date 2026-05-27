# Macro Radar

Macro Radar is a local-first macroeconomic research dashboard. It loads verified
local snapshot CSV data, computes simple macro indicators, and presents the
evidence chain in a Streamlit UI.

This project is designed for macro research workflow practice. It is not an
automated trading system, not investment advice, and not a machine-learning
forecasting system.

## Current MVP

- Streamlit dashboard with Overview, Chart, Data, and Provenance tabs.
- Local CSV loader with schema and type validation.
- DuckDB time-series storage wrapper.
- Time-series transforms: MoM, YoY, rolling mean, z-score, percentile rank.
- Conservative indicator evaluators for M2, PMI, UMCSI, building permits,
  yield curve, real rates, credit spreads, and cyclical commodities.
- Macro bias combiner that returns `Risk-On`, `Neutral`, `Risk-Off`, or
  `Insufficient Data`.
- Refresh status panel showing local snapshot path, retrieved date, observation
  end date, stale status, and documented refresh action.
- Fixture-only tests with no live network dependency.

## Data Sources

Implemented dashboard data lives under `data/official/` as static snapshots.
The app does not fetch live data at runtime.

| Indicator | Source |
| --- | --- |
| M2 | FRED `M2SL`, Federal Reserve Board |
| Yield curve | FRED `T10Y2Y`, Federal Reserve Bank of St. Louis |
| Real rates | FRED `DFII10`, Board of Governors H.15 |
| Credit spreads | FRED `BAMLH0A0HYM2`, `BAMLC0A0CM`, ICE BofA Indices |
| UMCSI | FRED `UMCSENT`, University of Michigan |
| Building permits | FRED `PERMIT`, U.S. Census Bureau and HUD |
| ISM Manufacturing PMI | ISM release distributed by PRNewswire |
| ISM Services PMI | ISM release distributed by PRNewswire |
| Cyclical commodities | World Bank Pink Sheet `COPPER`, `IRON_ORE`, `SAWNWD_MYS`, `GOLD`, `SILVER`, `CRUDE_WTI` |

Commodity snapshots use World Bank Commodity Markets Pink Sheet monthly data.
`SAWNWD_MYS` is used as a wood/lumber proxy; it is not a U.S. lumber futures
price.

See `source_registry.yaml` and `SOURCE_PROVENANCE.md` for source URLs, series
IDs, retrieved dates, observation ranges, and rights notes.

## What This Is Not

- No broker integration.
- No order execution.
- No position sizing.
- No portfolio management.
- No strategy backtesting.
- No investment advice.
- No machine-learning prediction model.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Run Tests

```bash
pytest
```

Tests use local fixtures and injected transports only. They should not call live
APIs.

## Start The Dashboard

```bash
streamlit run macro_radar/ui/app.py
```

Then open the local URL printed by Streamlit, usually:

```text
http://localhost:8501
```

## Refresh FRED Snapshots

Use FRED graph CSV:

```bash
python -m macro_radar.commands.refresh_fred_snapshots --transport graph-csv --series yield_curve real_rates credit_spreads --start 2024-01-01
```

Use FRED API:

```bash
FRED_API_KEY=your_key macro-radar-refresh-fred --series yield_curve real_rates credit_spreads
```

After a successful FRED refresh, the command updates `source_registry.yaml`
with `retrieved_at` and `observation_end`.

## Project Layout

```text
macro_radar/
  ingestion/      CSV and FRED data adapters
  storage/        DuckDB wrapper
  transforms/     Time-series and statistics functions
  indicators/     Indicator evaluators
  scoring/        Macro bias combiner
  ui/             Streamlit dashboard
data/
  official/       Verified local snapshot CSV files
tests/            Fixture-only pytest suite
```

## Add A New Indicator

1. Add a source entry to `source_registry.yaml`.
2. Include source URL, series ID or release reference, frequency, unit, rights
   note, `retrieved_at`, `observation_start`, and `observation_end`.
3. Add a local snapshot CSV with the `date,value` contract.
4. Implement an evaluator that returns `IndicatorResult`.
5. Wire the evaluator into `macro_radar/ui/app.py`.
6. Add tests for loading, calculations, missing-data behavior, and registry
   provenance.

## Acceptance Criteria

- `pytest` passes.
- Streamlit starts with `streamlit run macro_radar/ui/app.py`.
- Implemented indicators use verified local snapshots, not synthetic dashboard
  values.
- Missing indicators show `Not Implemented` or `Insufficient Data`.
- Provenance is visible in the UI.
- No secrets, API keys, account credentials, trading signals, or investment
  advice are committed.
