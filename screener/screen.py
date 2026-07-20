"""Screening rules — the two lists.

List 1 (trend change): EMA36 computed on *closes* crossing EMA90 computed on
*opens*, within the most recent trading day (= 4 two-hour bars). An upward
cross is a "golden" cross, downward is a "death" cross.

List 2 (statistical extreme + regime confirmation): last close outside
Bollinger Bands BB(90, SMA, 3). A +/-3-sigma event is rare by construction,
so we require confirmation: current rolling Beta(300) vs the S&P 500 must be
above its own 252-bar mean for an upside break (the stock is in a
higher-sensitivity regime) or below it for a downside break.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import bollinger, ema, rolling_beta

EMA_FAST = 36        # on close
EMA_SLOW = 90        # on open
CROSS_LOOKBACK = 4   # 4 x 2h bars = 1 trading day
BB_WINDOW, BB_K = 90, 3.0
BETA_WINDOW = 300
BETA_MEAN_WINDOW = 252
MIN_BARS = 100


def detect_cross(bars: pd.DataFrame) -> dict | None:
    """Return the most recent EMA cross within the last CROSS_LOOKBACK bars."""
    e_fast = ema(bars["close"], EMA_FAST).to_numpy()
    e_slow = ema(bars["open"], EMA_SLOW).to_numpy()
    diff = e_fast - e_slow
    n = len(bars)
    found = None
    for i in range(max(EMA_SLOW, n - CROSS_LOOKBACK), n):
        d0, d1 = diff[i - 1], diff[i]
        if np.isnan(d0) or np.isnan(d1):
            continue
        kind = "golden" if (d0 <= 0 < d1) else "death" if (d0 >= 0 > d1) else None
        if kind:
            found = {
                "type": kind,
                "barTime": bars.index[i].isoformat()[:16],
                "ema36": round(float(e_fast[i]), 4),
                "ema90": round(float(e_slow[i]), 4),
                "close": round(float(bars["close"].iloc[i]), 4),
            }
    return found


def detect_bb_break(bars: pd.DataFrame, market: pd.DataFrame) -> dict | None:
    """Bollinger +/-3-sigma break with rolling-beta regime confirmation."""
    upper, _, lower = bollinger(bars["close"], BB_WINDOW, BB_K)
    c = float(bars["close"].iloc[-1])
    up, lo = float(upper.iloc[-1]), float(lower.iloc[-1])
    if np.isnan(up) or (lo < c < up):
        return None

    # Align stock and market bars on timestamps, then compute simple returns.
    joined = bars[["close"]].join(market[["close"]], how="inner",
                                  lsuffix="_s", rsuffix="_m").dropna()
    rets = joined.pct_change().dropna()
    if len(rets) < BETA_WINDOW + BETA_MEAN_WINDOW - 1:
        return None  # not enough history for the beta filter

    betas = rolling_beta(rets["close_s"].to_numpy(),
                         rets["close_m"].to_numpy(), BETA_WINDOW)
    cur = betas[-1]
    mean = np.nanmean(betas[-BETA_MEAN_WINDOW:])
    if np.isnan(cur) or np.isnan(mean):
        return None

    kind = None
    if c > up and cur > mean:
        kind = "above"
    elif c < lo and cur < mean:
        kind = "below"
    if not kind:
        return None
    return {
        "type": kind,
        "close": round(c, 4),
        "upper": round(up, 4),
        "lower": round(lo, 4),
        "beta": round(float(cur), 4),
        "betaMean": round(float(mean), 4),
    }


def screen_ticker(bars: pd.DataFrame, market: pd.DataFrame) -> dict:
    """Run both rules on one ticker's 2-hour bars. Raises if history is thin."""
    if len(bars) < MIN_BARS:
        raise ValueError(f"insufficient history: {len(bars)} bars < {MIN_BARS}")
    return {
        "cross": detect_cross(bars),
        "bb": detect_bb_break(bars, market),
    }
