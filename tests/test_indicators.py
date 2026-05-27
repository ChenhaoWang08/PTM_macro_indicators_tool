from __future__ import annotations

import pandas as pd

from macro_radar.indicators.building_permits import evaluate_building_permits
from macro_radar.indicators.commodities import evaluate_commodities
from macro_radar.indicators.credit_spreads import evaluate_credit_spreads
from macro_radar.indicators.ism import evaluate_ism_manufacturing
from macro_radar.indicators.m2 import evaluate_m2
from macro_radar.indicators.rates import evaluate_real_rates, evaluate_yield_curve
from macro_radar.indicators.umcsi import evaluate_umcsi


def _df(values):
    return pd.DataFrame(
        {"date": pd.date_range("2024-01-01", periods=len(values), freq="MS"), "value": values}
    )


def test_ism_above_50_is_risk_on():
    result = evaluate_ism_manufacturing(_df([49, 51]))

    assert result.zone == "Risk-On"


def test_ism_below_50_is_risk_off():
    result = evaluate_ism_manufacturing(_df([51, 49]))

    assert result.zone == "Risk-Off"


def test_umcsi_zone_thresholds():
    assert evaluate_umcsi(_df([82])).zone == "Risk-On"
    assert evaluate_umcsi(_df([75])).zone == "Neutral"
    assert evaluate_umcsi(_df([68])).zone == "Risk-Off"
    assert evaluate_umcsi(_df([54])).zone == "Risk-Off"


def test_building_permits_thresholds():
    assert evaluate_building_permits(_df([1400])).zone == "Risk-On"
    assert evaluate_building_permits(_df([1000])).zone == "Neutral"
    assert evaluate_building_permits(_df([799])).zone == "Risk-Off"


def test_m2_less_than_12_rows_is_insufficient_data():
    result = evaluate_m2(_df(range(11)))

    assert result.zone == "Insufficient Data"


def test_yield_curve_thresholds():
    assert evaluate_yield_curve(_df([-0.1])).zone == "Risk-Off"
    assert evaluate_yield_curve(_df([0.25])).zone == "Neutral"
    assert evaluate_yield_curve(_df([0.5])).zone == "Risk-On"


def test_real_rates_thresholds():
    assert evaluate_real_rates(_df([0.9])).zone == "Risk-On"
    assert evaluate_real_rates(_df([1.5])).zone == "Neutral"
    assert evaluate_real_rates(_df([2.1])).zone == "Risk-Off"


def test_credit_spreads_thresholds():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="D"),
            "high_yield_oas": [3.0, 4.0, 5.2],
            "investment_grade_oas": [0.8, 1.0, 1.1],
        }
    )

    assert evaluate_credit_spreads(df.iloc[[0]]).zone == "Risk-On"
    assert evaluate_credit_spreads(df.iloc[[1]]).zone == "Neutral"
    assert evaluate_credit_spreads(df.iloc[[2]]).zone == "Risk-Off"


def test_commodities_uses_six_month_breadth():
    rows = []
    for commodity in ("copper", "iron_ore", "lumber", "gold", "silver", "wti"):
        for index, date in enumerate(pd.date_range("2024-01-01", periods=7, freq="MS")):
            rows.append(
                {
                    "date": date,
                    "commodity_key": commodity,
                    "commodity": commodity,
                    "value": 100 + index,
                }
            )
    result = evaluate_commodities(pd.DataFrame(rows))

    assert result.zone == "Risk-On"
    assert result.latest_value is not None
    assert "six-month price momentum breadth" in result.explanation


def test_commodities_requires_all_six_snapshots():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=7, freq="MS"),
            "commodity_key": ["copper"] * 7,
            "commodity": ["Copper"] * 7,
            "value": range(7),
        }
    )

    assert evaluate_commodities(df).zone == "Insufficient Data"
