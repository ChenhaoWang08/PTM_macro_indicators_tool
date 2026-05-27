from __future__ import annotations

import pandas as pd

from macro_radar.indicators.base import IndicatorResult


def evaluate_umcsi(df: pd.DataFrame) -> IndicatorResult:
    data = df.sort_values("date").reset_index(drop=True).copy()
    explanation = "UMCSI is evaluated using zone thresholds, not a 50 expansion boundary."
    if data.empty:
        return IndicatorResult(
            key="umcsi",
            name="University of Michigan Consumer Sentiment",
            status="implemented",
            latest_date=None,
            latest_value=None,
            zone="Insufficient Data",
            explanation=explanation,
            dataframe=data,
        )

    latest = data.iloc[-1]
    latest_value = float(latest["value"])
    if latest_value > 80:
        zone = "Risk-On"
    elif 70 <= latest_value <= 80:
        zone = "Neutral"
    else:
        zone = "Risk-Off"

    return IndicatorResult(
        key="umcsi",
        name="University of Michigan Consumer Sentiment",
        status="implemented",
        latest_date=latest["date"],
        latest_value=latest_value,
        zone=zone,
        explanation=explanation,
        dataframe=data,
    )

