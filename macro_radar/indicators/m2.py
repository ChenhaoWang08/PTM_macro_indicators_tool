from __future__ import annotations

import pandas as pd

from macro_radar.indicators.base import IndicatorResult
from macro_radar.transforms.time_series import yoy_pct_change


def evaluate_m2(df: pd.DataFrame) -> IndicatorResult:
    data = yoy_pct_change(df.sort_values("date").reset_index(drop=True))
    explanation = (
        "M2 is used as a liquidity confirmation indicator. It is not a standalone "
        "predictor and should be interpreted with other macro evidence."
    )

    if len(data) < 12 or data.empty:
        return IndicatorResult(
            key="m2",
            name="M2 Money Supply",
            status="implemented",
            latest_date=None,
            latest_value=None,
            zone="Insufficient Data",
            explanation=explanation,
            dataframe=data,
        )

    latest = data.iloc[-1]
    latest_yoy = latest["yoy_pct"]
    if pd.isna(latest_yoy):
        zone = "Insufficient Data"
    elif latest_yoy > 6:
        zone = "Risk-On"
    elif latest_yoy >= 0:
        zone = "Neutral"
    else:
        zone = "Risk-Off"

    return IndicatorResult(
        key="m2",
        name="M2 Money Supply",
        status="implemented",
        latest_date=latest["date"],
        latest_value=None if pd.isna(latest_yoy) else float(latest_yoy),
        zone=zone,
        explanation=explanation,
        dataframe=data,
    )

