from __future__ import annotations

from macro_radar.indicators.base import IndicatorResult


def not_implemented_indicator(key: str, name: str) -> IndicatorResult:
    return IndicatorResult(
        key=key,
        name=name,
        status="not_implemented",
        latest_date=None,
        latest_value=None,
        zone="Not Implemented",
        explanation="Not implemented yet.",
        dataframe=None,
    )

