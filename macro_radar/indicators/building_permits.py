from __future__ import annotations

import pandas as pd

from macro_radar.indicators.base import IndicatorResult


def evaluate_building_permits(df: pd.DataFrame) -> IndicatorResult:
    data = df.sort_values("date").reset_index(drop=True).copy()
    explanation = "Building permits are treated as a leading indicator for the housing market."
    if data.empty:
        return IndicatorResult(
            key="building_permits",
            name="Building Permits",
            status="implemented",
            latest_date=None,
            latest_value=None,
            zone="Insufficient Data",
            explanation=explanation,
            dataframe=data,
        )

    latest = data.iloc[-1]
    latest_value = float(latest["value"])
    if latest_value >= 1400:
        zone = "Risk-On"
    elif latest_value >= 800:
        zone = "Neutral"
    else:
        zone = "Risk-Off"

    return IndicatorResult(
        key="building_permits",
        name="Building Permits",
        status="implemented",
        latest_date=latest["date"],
        latest_value=latest_value,
        zone=zone,
        explanation=explanation,
        dataframe=data,
    )

