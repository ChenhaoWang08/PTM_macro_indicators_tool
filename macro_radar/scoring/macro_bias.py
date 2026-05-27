from __future__ import annotations

from macro_radar.indicators.base import IndicatorResult

ZONE_SCORES = {
    "Risk-On": 1,
    "Neutral": 0,
    "Risk-Off": -1,
    "Insufficient Data": 0,
    "Not Implemented": 0,
}


def combine_indicator_results(results: list[IndicatorResult]) -> dict[str, int | str]:
    score = sum(ZONE_SCORES[result.zone] for result in results)
    risk_on_count = sum(result.zone == "Risk-On" for result in results)
    neutral_count = sum(result.zone == "Neutral" for result in results)
    risk_off_count = sum(result.zone == "Risk-Off" for result in results)
    insufficient_count = sum(result.zone == "Insufficient Data" for result in results)
    not_implemented_count = sum(result.zone == "Not Implemented" for result in results)

    implemented_count = risk_on_count + neutral_count + risk_off_count
    if implemented_count == 0:
        bias = "Insufficient Data"
    elif score >= 2:
        bias = "Risk-On"
    elif score <= -2:
        bias = "Risk-Off"
    else:
        bias = "Neutral"

    return {
        "score": score,
        "bias": bias,
        "risk_on_count": risk_on_count,
        "neutral_count": neutral_count,
        "risk_off_count": risk_off_count,
        "insufficient_count": insufficient_count,
        "not_implemented_count": not_implemented_count,
    }

