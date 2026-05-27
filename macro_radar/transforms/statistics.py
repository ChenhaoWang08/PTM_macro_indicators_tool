from __future__ import annotations

import pandas as pd


def z_score(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with population z-score in `z_score`."""
    result = df.copy()
    mean = result["value"].mean()
    std = result["value"].std(ddof=0)
    if std == 0:
        result["z_score"] = 0.0
    else:
        result["z_score"] = (result["value"] - mean) / std
    return result


def percentile_rank(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with percentile rank in `percentile_rank`, scaled 0-100."""
    result = df.copy()
    result["percentile_rank"] = result["value"].rank(pct=True) * 100
    return result

