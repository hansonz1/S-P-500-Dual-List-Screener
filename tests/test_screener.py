"""Unit tests for resampling and indicator math (no network required)."""
import numpy as np
import pandas as pd
import pytest

from screener.data import to_2h
from screener.indicators import bollinger, ema, rolling_beta


def make_1h_frame():
    """Two trading days x 7 hourly bars (09:30..15:30), New York time."""
    times = []
    for day in ["2026-01-05", "2026-01-06"]:
        for hh, mm in [(9, 30), (10, 30), (11, 30), (12, 30),
                       (13, 30), (14, 30), (15, 30)]:
            times.append(pd.Timestamp(f"{day} {hh}:{mm}", tz="America/New_York"))
    n = len(times)
    base = np.arange(n, dtype=float) + 100.0
    return pd.DataFrame({"Open": base, "High": base + 1.0,
                         "Low": base - 1.0, "Close": base + 0.5},
                        index=pd.DatetimeIndex(times))


def test_to_2h_pairing():
    bars = to_2h(make_1h_frame())
    # 7 hourly bars/day -> 4 two-hour bars/day (last bar stands alone)
    assert len(bars) == 8
    # First 2h bar: open of 09:30 bar, close of 10:30 bar
    assert bars["open"].iloc[0] == 100.0
    assert bars["close"].iloc[0] == 101.5
    assert bars["high"].iloc[0] == 102.0   # max(101, 102)
    assert bars["low"].iloc[0] == 99.0     # min(99, 100)
    # 4th bar of day one is the lone 15:30 bar
    assert bars["open"].iloc[3] == 106.0
    assert bars["close"].iloc[3] == 106.5


def test_to_2h_never_pairs_across_days():
    df = make_1h_frame()
    bars = to_2h(df)
    # bar index 3 is day1 15:30 (lone); bar 4 must start day2 09:30
    assert bars.index[4].date().isoformat() == "2026-01-06"
    assert bars["open"].iloc[4] == 107.0


def test_ema_constant_series():
    s = pd.Series([5.0] * 50)
    assert np.allclose(ema(s, 10).to_numpy(), 5.0)


def test_bollinger_constant_series():
    s = pd.Series([10.0] * 120)
    upper, mid, lower = bollinger(s, window=90, k=3.0)
    assert upper.iloc[-1] == pytest.approx(10.0)
    assert mid.iloc[-1] == pytest.approx(10.0)
    assert lower.iloc[-1] == pytest.approx(10.0)


def test_rolling_beta_exact():
    rng = np.random.default_rng(42)
    x = rng.normal(0, 0.01, 800)
    y = 2.0 * x  # perfect beta of 2, no noise
    betas = rolling_beta(y, x, window=300)
    assert np.isnan(betas[298])           # not enough data yet
    assert betas[299] == pytest.approx(2.0)
    assert betas[-1] == pytest.approx(2.0)


def test_rolling_beta_matches_naive():
    rng = np.random.default_rng(7)
    x = rng.normal(0, 0.01, 500)
    y = 1.3 * x + rng.normal(0, 0.005, 500)
    betas = rolling_beta(y, x, window=300)
    # Compare last position against a naive OLS on the same window
    xa, ya = x[-300:], y[-300:]
    naive = np.cov(xa, ya, ddof=0)[0, 1] / np.var(xa)
    assert betas[-1] == pytest.approx(naive, rel=1e-9)
