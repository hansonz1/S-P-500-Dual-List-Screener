"""Technical indicators: EMA, Bollinger Bands, rolling OLS beta.

The rolling beta uses prefix (cumulative) sums so that computing a beta for
*every* window position costs O(n) total, instead of O(n * window) with a
naive loop. Across ~500 tickers x ~1000 bars this is the difference between
milliseconds and minutes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, n: int) -> pd.Series:
    """Exponential moving average with smoothing factor 2 / (n + 1)."""
    return series.ewm(span=n, adjust=False).mean()


def bollinger(close: pd.Series, window: int = 90, k: float = 3.0):
    """Bollinger Bands: SMA(window) +/- k * population std(window).

    Returns (upper, middle, lower) as Series aligned with `close`.
    """
    mid = close.rolling(window).mean()
    sd = close.rolling(window).std(ddof=0)
    return mid + k * sd, mid, mid - k * sd


def rolling_beta(stock_ret: np.ndarray, mkt_ret: np.ndarray,
                 window: int = 300) -> np.ndarray:
    """Rolling OLS beta of stock returns vs market returns.

    beta = Cov(mkt, stock) / Var(mkt) over each trailing `window`.
    Implemented with cumulative sums: for any window we can recover
    sum(x), sum(y), sum(x^2), sum(x*y) in O(1), giving O(n) overall.

    Returns an array the same length as the inputs; positions with fewer
    than `window` observations are NaN.
    """
    x = np.asarray(mkt_ret, dtype=float)
    y = np.asarray(stock_ret, dtype=float)
    n = len(x)
    out = np.full(n, np.nan)
    if n < window:
        return out

    cx = np.concatenate([[0.0], np.cumsum(x)])
    cy = np.concatenate([[0.0], np.cumsum(y)])
    cxx = np.concatenate([[0.0], np.cumsum(x * x)])
    cxy = np.concatenate([[0.0], np.cumsum(x * y)])

    j = np.arange(window - 1, n)   # window end positions
    a = j + 1 - window             # window start positions
    sx = cx[j + 1] - cx[a]
    sy = cy[j + 1] - cy[a]
    sxx = cxx[j + 1] - cxx[a]
    sxy = cxy[j + 1] - cxy[a]
    den = window * sxx - sx * sx
    with np.errstate(divide="ignore", invalid="ignore"):
        out[j] = np.where(den == 0, np.nan, (window * sxy - sx * sy) / den)
    return out
