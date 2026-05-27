from __future__ import annotations

import pandas as pd
import pytest

from macro_radar.transforms.statistics import percentile_rank, z_score
from macro_radar.transforms.time_series import mom_pct_change, rolling_mean, yoy_pct_change


def test_mom_pct_change_is_correct():
    df = pd.DataFrame(
        {"date": pd.date_range("2024-01-01", periods=2, freq="MS"), "value": [100, 110]}
    )

    result = mom_pct_change(df)

    assert pd.isna(result.loc[0, "mom_pct"])
    assert result.loc[1, "mom_pct"] == pytest.approx(10)
    assert "mom_pct" not in df.columns


def test_yoy_pct_change_starts_on_thirteenth_row():
    df = pd.DataFrame(
        {"date": pd.date_range("2024-01-01", periods=13, freq="MS"), "value": range(1, 14)}
    )

    result = yoy_pct_change(df)

    assert result.loc[:11, "yoy_pct"].isna().all()
    assert pd.notna(result.loc[12, "yoy_pct"])


def test_rolling_mean_is_correct():
    df = pd.DataFrame(
        {"date": pd.date_range("2024-01-01", periods=3, freq="MS"), "value": [1, 2, 3]}
    )

    result = rolling_mean(df, window=3)

    assert pd.isna(result.loc[1, "rolling_mean"])
    assert result.loc[2, "rolling_mean"] == 2


def test_z_score_zero_standard_deviation_returns_zero():
    df = pd.DataFrame(
        {"date": pd.date_range("2024-01-01", periods=3, freq="MS"), "value": [5, 5, 5]}
    )

    result = z_score(df)

    assert result["z_score"].tolist() == [0, 0, 0]


def test_percentile_rank_is_scaled_zero_to_one_hundred():
    df = pd.DataFrame(
        {"date": pd.date_range("2024-01-01", periods=3, freq="MS"), "value": [1, 2, 3]}
    )

    result = percentile_rank(df)

    assert result["percentile_rank"].between(0, 100).all()
    assert result.loc[2, "percentile_rank"] == 100
