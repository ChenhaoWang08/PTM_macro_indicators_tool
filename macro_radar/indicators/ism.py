from __future__ import annotations

import pandas as pd

from macro_radar.indicators.base import IndicatorResult


def evaluate_ism_manufacturing(df: pd.DataFrame) -> IndicatorResult:
    return _evaluate_ism(
        df=df,
        key="ism_manufacturing",
        name="ISM Manufacturing PMI",
    )


def evaluate_ism_services(df: pd.DataFrame) -> IndicatorResult:
    return _evaluate_ism(
        df=df,
        key="ism_services",
        name="ISM Services PMI",
    )


def _evaluate_ism(df: pd.DataFrame, key: str, name: str) -> IndicatorResult:
    data = df.sort_values("date").reset_index(drop=True).copy()
    explanation = "PMI readings above 50 indicate expansion; readings below 50 indicate contraction."
    if data.empty:
        return IndicatorResult(
            key=key,
            name=name,
            status="implemented",
            latest_date=None,
            latest_value=None,
            zone="Insufficient Data",
            explanation=explanation,
            dataframe=data,
        )

    latest = data.iloc[-1]
    latest_value = float(latest["value"])
    if latest_value > 50:
        zone = "Risk-On"
    elif latest_value == 50:
        zone = "Neutral"
    else:
        zone = "Risk-Off"

    return IndicatorResult(
        key=key,
        name=name,
        status="implemented",
        latest_date=latest["date"],
        latest_value=latest_value,
        zone=zone,
        explanation=explanation,
        dataframe=data,
    )

