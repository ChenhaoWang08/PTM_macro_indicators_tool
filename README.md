# Macro Radar

Macro Radar is a local-first macroeconomic research dashboard for exploring macro conditions through verified local data snapshots.

It loads documented CSV snapshots, validates their structure, computes simple macro indicators, and presents the evidence chain in a Streamlit UI. The goal is to make macro research easier to inspect, reproduce, and review.

This project is built for macro research workflow practice. It is not an automated trading system, not investment advice, and not a machine-learning forecasting system.

---

## Current MVP

The current MVP includes:

- Streamlit dashboard with `Overview`, `Chart`, `Data`, and `Provenance` tabs.
- Local CSV loader with schema and type validation.
- DuckDB time-series storage wrapper.
- Time-series transforms:
  - Month-over-month change
  - Year-over-year change
  - Rolling mean
  - Z-score
  - Percentile rank
- Conservative indicator evaluators for:
  - M2 money supply
  - Manufacturing PMI
  - Services PMI
  - University of Michigan Consumer Sentiment Index
  - Building permits
  - Yield curve
  - Real rates
  - Credit spreads
  - Cyclical commodities
- Macro bias combiner that returns:
  - `Risk-On`
  - `Neutral`
  - `Risk-Off`
  - `Insufficient Data`
- Refresh status panel showing:
  - Local snapshot path
  - Retrieved date
  - Observation end date
  - Stale status
  - Documented refresh action
- Fixture-only test suite with no live network dependency.

---

## Data Sources

Implemented dashboard data lives under `data/official/` as static local snapshots.

The app does **not** fetch live data at runtime. This makes the dashboard reproducible and easier to audit.

| Indicator | Source |
|---|---|
| M2 | FRED `M2SL`, Federal Reserve Board |
| Yield Curve | FRED `T10Y2Y`, Federal Reserve Bank of St. Louis |
| Real Rates | FRED `DFII10`, Board of Governors H.15 |
| Credit Spreads | FRED `BAMLH0A0HYM2`, `BAMLC0A0CM`, ICE BofA Indices |
| UMCSI | FRED `UMCSENT`, University of Michigan |
| Building Permits | FRED `PERMIT`, U.S. Census Bureau and HUD |
| ISM Manufacturing PMI | ISM release distributed by PRNewswire |
| ISM Services PMI | ISM release distributed by PRNewswire |
| Cyclical Commodities | World Bank Commodity Markets Pink Sheet |

Commodity snapshots use World Bank Commodity Markets Pink Sheet monthly data, including:

- Copper
- Iron ore
- Sawnwood Malaysia
- Gold
- Silver
- WTI crude oil

`SAWNWD_MYS` is used as a wood/lumber proxy. It is not a U.S. lumber futures price.

For source URLs, series IDs, retrieved dates, observation ranges, and rights notes, see:

- `source_registry.yaml`
- `SOURCE_PROVENANCE.md`

---

## What This Project Is Not

Macro Radar is intentionally scoped as a research dashboard.

It does **not** include:

- Broker integration
- Order execution
- Position sizing
- Portfolio management
- Strategy backtesting
- Investment advice
- Machine-learning prediction models

The dashboard shows macro evidence and conservative signal labels. It does not tell users what to buy, sell, or trade.

---

## Install

Create and activate a virtual environment:

                     .-""""""""""""-.
                  .-'                '-.
                .'      SOVIET RADAR    '.
               /        MACRO RADAR       \
              /                            \
             |        .------------.        |
             |       /  .--------.  \       |
             |      /  /          \  \      |
             |     |  |    CCCP    |  |     |
             |      \  \          /  /      |
             |       \  '--------'  /       |
             |        '------------'        |
              \                            /
               \                          /
                '.                      .'
                  '-.                .-'
                     '-............-'
                           ||
                           ||
                         __||__
                        /  ||  \
                       /   ||   \
                      /____||____\
                           ||
                           ||
                  _________||_________
                 /                    \
                /   SIGNAL SCAN NODE   \
               /________________________\
               |  [ ] [ ] [ ] [ ] [ ]  |
               |  MACRO RISK MONITOR   |
               |________________________|
                    /      ||      \
                   /       ||       \
                  /________||________\

        >>> SCANNING: LIQUIDITY | CREDIT | GROWTH | SENTIMENT <<<

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .



