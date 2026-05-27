from __future__ import annotations

import pandas as pd


def mom_pct_change(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with month-over-month percentage change in `mom_pct`."""
    result = df.copy()
    result["mom_pct"] = result["value"].pct_change(1) * 100
    return result


def yoy_pct_change(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with year-over-year percentage change in `yoy_pct`."""
    result = df.copy()
    result["yoy_pct"] = result["value"].pct_change(12) * 100
    return result


def rolling_mean(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Return a copy with a rolling mean in `rolling_mean`."""
    if window < 1:
        raise ValueError("window must be at least 1")
    result = df.copy()
    result["rolling_mean"] = result["value"].rolling(window).mean()
    return result

