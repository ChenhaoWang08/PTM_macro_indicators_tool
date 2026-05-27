from __future__ import annotations

import pandas as pd

from macro_radar.indicators.base import IndicatorResult

EXPECTED_COMMODITIES = {
    "copper",
    "iron_ore",
    "lumber",
    "gold",
    "silver",
    "wti",
}


def evaluate_commodities(df: pd.DataFrame) -> IndicatorResult:
    data = df.sort_values(["commodity_key", "date"]).reset_index(drop=True).copy()
    explanation = (
        "Cyclical commodities are displayed as macro evidence from verified local "
        "snapshots. The zone uses broad six-month price momentum breadth across "
        "copper, iron ore, sawnwood, gold, silver, and WTI; it is not a trading signal."
    )

    required_columns = {"date", "commodity_key", "commodity", "value"}
    missing_columns = required_columns.difference(data.columns)
    if data.empty or missing_columns:
        return _insufficient(explanation, data)

    available = set(data["commodity_key"].dropna().astype(str).unique())
    if not EXPECTED_COMMODITIES.issubset(available):
        return _insufficient(
            f"{explanation} Missing commodity snapshots: "
            f"{', '.join(sorted(EXPECTED_COMMODITIES.difference(available)))}.",
            data,
        )

    data["six_month_pct"] = data.groupby("commodity_key")["value"].pct_change(6) * 100
    latest_rows = data.groupby("commodity_key", as_index=False).tail(1)
    if latest_rows["six_month_pct"].isna().any():
        return _insufficient(explanation, data)

    positive_breadth = int((latest_rows["six_month_pct"] > 0).sum())
    negative_breadth = int((latest_rows["six_month_pct"] < 0).sum())
    if positive_breadth >= 4 and negative_breadth <= 1:
        zone = "Risk-On"
    elif negative_breadth >= 4:
        zone = "Risk-Off"
    else:
        zone = "Neutral"

    average_momentum = float(latest_rows["six_month_pct"].mean())
    latest_date = latest_rows["date"].max()
    detail = (
        f" Latest average six-month momentum is {average_momentum:.2f}%; "
        f"{positive_breadth} of 6 series are positive and {negative_breadth} are negative."
    )
    return IndicatorResult(
        key="commodities",
        name="Cyclical Commodities",
        status="implemented",
        latest_date=latest_date,
        latest_value=average_momentum,
        zone=zone,
        explanation=explanation + detail,
        dataframe=data,
    )


def _insufficient(explanation: str, dataframe: pd.DataFrame) -> IndicatorResult:
    return IndicatorResult(
        key="commodities",
        name="Cyclical Commodities",
        status="implemented",
        latest_date=None,
        latest_value=None,
        zone="Insufficient Data",
        explanation=explanation,
        dataframe=dataframe,
    )
