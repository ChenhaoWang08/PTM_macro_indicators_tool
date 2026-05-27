from __future__ import annotations

import pandas as pd

from macro_radar.indicators.base import IndicatorResult


def evaluate_credit_spreads(df: pd.DataFrame) -> IndicatorResult:
    data = df.sort_values("date").reset_index(drop=True).copy()
    explanation = (
        "Credit spreads are market-priced risk evidence. Wider high-yield or "
        "investment-grade OAS points to tighter credit conditions, but this is not "
        "a standalone investment signal."
    )
    if data.empty or "high_yield_oas" not in data.columns or "investment_grade_oas" not in data.columns:
        return IndicatorResult(
            key="credit_spreads",
            name="Credit Spreads",
            status="implemented",
            latest_date=None,
            latest_value=None,
            zone="Insufficient Data",
            explanation=explanation,
            dataframe=data,
        )

    latest = data.iloc[-1]
    high_yield_oas = float(latest["high_yield_oas"])
    investment_grade_oas = float(latest["investment_grade_oas"])

    if high_yield_oas >= 5 or investment_grade_oas >= 1.5:
        zone = "Risk-Off"
    elif high_yield_oas <= 3.5 and investment_grade_oas <= 1.2:
        zone = "Risk-On"
    else:
        zone = "Neutral"

    data["value"] = data["high_yield_oas"]
    return IndicatorResult(
        key="credit_spreads",
        name="Credit Spreads",
        status="implemented",
        latest_date=latest["date"],
        latest_value=high_yield_oas,
        zone=zone,
        explanation=(
            f"{explanation} Latest HY OAS is {high_yield_oas:.2f}%; "
            f"latest IG OAS is {investment_grade_oas:.2f}%."
        ),
        dataframe=data,
    )

