from __future__ import annotations

import pandas as pd

from macro_radar.indicators.base import IndicatorResult


def evaluate_yield_curve(df: pd.DataFrame) -> IndicatorResult:
    data = df.sort_values("date").reset_index(drop=True).copy()
    explanation = (
        "The 10Y-2Y spread is yield-curve risk evidence. Inversion is treated as "
        "risk-off evidence, not a deterministic recession forecast."
    )
    if data.empty:
        return _insufficient("yield_curve", "10Y-2Y Yield Curve Spread", explanation, data)

    latest = data.iloc[-1]
    latest_value = float(latest["value"])
    if latest_value < 0:
        zone = "Risk-Off"
    elif latest_value >= 0.5:
        zone = "Risk-On"
    else:
        zone = "Neutral"

    return IndicatorResult(
        key="yield_curve",
        name="10Y-2Y Yield Curve Spread",
        status="implemented",
        latest_date=latest["date"],
        latest_value=latest_value,
        zone=zone,
        explanation=explanation,
        dataframe=data,
    )


def evaluate_real_rates(df: pd.DataFrame) -> IndicatorResult:
    data = df.sort_values("date").reset_index(drop=True).copy()
    explanation = (
        "The 10-year TIPS yield is a real-rate proxy. Higher real rates can tighten "
        "financial conditions, but this is contextual evidence rather than a trading signal."
    )
    if data.empty:
        return _insufficient("real_rates", "10-Year Real Interest Rate", explanation, data)

    latest = data.iloc[-1]
    latest_value = float(latest["value"])
    if latest_value < 1:
        zone = "Risk-On"
    elif latest_value <= 2:
        zone = "Neutral"
    else:
        zone = "Risk-Off"

    return IndicatorResult(
        key="real_rates",
        name="10-Year Real Interest Rate",
        status="implemented",
        latest_date=latest["date"],
        latest_value=latest_value,
        zone=zone,
        explanation=explanation,
        dataframe=data,
    )


def _insufficient(
    key: str, name: str, explanation: str, dataframe: pd.DataFrame
) -> IndicatorResult:
    return IndicatorResult(
        key=key,
        name=name,
        status="implemented",
        latest_date=None,
        latest_value=None,
        zone="Insufficient Data",
        explanation=explanation,
        dataframe=dataframe,
    )

