# Source Provenance

This file records the verified source queue for implemented Macro Radar MVP
dashboard data. The app reads local snapshot CSV files; it does not fetch live
data at runtime.

## Implemented Indicators

| key | local snapshot | source | provenance status |
| --- | --- | --- | --- |
| m2 | `data/official/m2.csv` | FRED `M2SL`, Federal Reserve Board | verified_official_snapshot |
| yield_curve | `data/official/yield_curve.csv` | FRED `T10Y2Y`, Federal Reserve Bank of St. Louis | verified_official_snapshot |
| real_rates | `data/official/real_rates.csv` | FRED `DFII10`, Board of Governors H.15 | verified_official_snapshot |
| credit_spreads | `data/official/credit_spreads_hy.csv` and `data/official/credit_spreads_ig.csv` | FRED `BAMLH0A0HYM2` and `BAMLC0A0CM`, ICE BofA Indices | verified_official_snapshot |
| umcsi | `data/official/umcsi.csv` | FRED `UMCSENT`, University of Michigan | verified_official_snapshot |
| building_permits | `data/official/building_permits.csv` | FRED `PERMIT`, Census Bureau and HUD | verified_official_snapshot |
| ism_manufacturing | `data/official/ism_manufacturing.csv` | ISM December 2024 release via PRNewswire | verified_official_release_snapshot |
| ism_services | `data/official/ism_services.csv` | ISM December 2024 release via PRNewswire | verified_official_release_snapshot |
| commodities | `data/official/commodity_*.csv` | World Bank Pink Sheet `COPPER`, `IRON_ORE`, `SAWNWD_MYS`, `GOLD`, `SILVER`, `CRUDE_WTI` | verified_official_snapshot |

## Rules

- Do not mark an indicator as implemented without a real source URL.
- Do not use metadata-only placeholders as observations.
- Keep tests network-free; use temporary synthetic fixtures only in tests.
- Use `FRED_API_KEY` only from the environment; never commit real API keys.
- For ISM data, use manual snapshots from official releases unless licensing
  and automation rights are explicitly reviewed.
- For commodities, refresh from the World Bank Pink Sheet workbook and keep the
  local CSVs as `date,value` snapshots. `SAWNWD_MYS` is a wood/lumber proxy,
  not a U.S. lumber futures price.

## PR-A3 FRED Snapshot Queue

| key | series ID | FRED URL | notes |
| --- | --- | --- | --- |
| m2 | `M2SL` | https://fred.stlouisfed.org/series/M2SL | Monthly M2 Money Stock. |
| yield_curve | `T10Y2Y` | https://fred.stlouisfed.org/series/T10Y2Y | Daily 10-year minus 2-year Treasury spread. |
| real_rates | `DFII10` | https://fred.stlouisfed.org/series/DFII10 | Daily 10-year inflation-indexed Treasury constant maturity yield. |
| credit_spreads_hy | `BAMLH0A0HYM2` | https://fred.stlouisfed.org/series/BAMLH0A0HYM2 | Daily high-yield OAS; copyright restrictions apply. |
| credit_spreads_ig | `BAMLC0A0CM` | https://fred.stlouisfed.org/series/BAMLC0A0CM | Daily investment-grade OAS; copyright restrictions apply. |

Refresh command:

```bash
python -m macro_radar.commands.refresh_fred_snapshots --transport graph-csv --series yield_curve real_rates credit_spreads --start 2024-01-01
```

The refresh command writes the CSV snapshot and updates `source_registry.yaml`
with the refresh date and latest observation end date for the refreshed FRED
series.

## Commodity Snapshot Queue

| key | World Bank Pink Sheet code | local snapshot | unit |
| --- | --- | --- | --- |
| copper | `COPPER` | `data/official/commodity_copper.csv` | USD per metric ton |
| iron_ore | `IRON_ORE` | `data/official/commodity_iron_ore.csv` | USD per dry metric ton unit |
| lumber | `SAWNWD_MYS` | `data/official/commodity_lumber.csv` | USD per cubic meter |
| gold | `GOLD` | `data/official/commodity_gold.csv` | USD per troy ounce |
| silver | `SILVER` | `data/official/commodity_silver.csv` | USD per troy ounce |
| wti | `CRUDE_WTI` | `data/official/commodity_wti.csv` | USD per barrel |

Manual refresh source:

```text
https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx
```
