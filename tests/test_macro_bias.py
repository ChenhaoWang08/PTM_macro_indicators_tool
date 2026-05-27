from __future__ import annotations

from macro_radar.indicators.base import IndicatorResult
from macro_radar.scoring.macro_bias import combine_indicator_results


def _result(zone: str) -> IndicatorResult:
    return IndicatorResult(
        key=zone.lower().replace(" ", "_"),
        name=zone,
        status="implemented",
        latest_date=None,
        latest_value=None,
        zone=zone,
        explanation="test",
        dataframe=None,
    )


def test_multiple_risk_on_results_combine_to_risk_on():
    summary = combine_indicator_results([_result("Risk-On"), _result("Risk-On")])

    assert summary["bias"] == "Risk-On"
    assert summary["score"] == 2


def test_multiple_risk_off_results_combine_to_risk_off():
    summary = combine_indicator_results([_result("Risk-Off"), _result("Risk-Off")])

    assert summary["bias"] == "Risk-Off"
    assert summary["score"] == -2


def test_mixed_results_combine_to_neutral():
    summary = combine_indicator_results(
        [_result("Risk-On"), _result("Risk-Off"), _result("Neutral")]
    )

    assert summary["bias"] == "Neutral"
    assert summary["score"] == 0


def test_all_not_implemented_is_insufficient_data():
    summary = combine_indicator_results([_result("Not Implemented"), _result("Not Implemented")])

    assert summary["bias"] == "Insufficient Data"
    assert summary["not_implemented_count"] == 2

