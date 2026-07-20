"""Data acquisition and time-series resampling.

Responsibilities:
1. Get the current list of S&P 500 constituents from Wikipedia.
2. Download 1-hour OHLC bars (regular trading session only) from Yahoo Finance.
3. Resample 1-hour bars into 2-hour bars.
"""
from __future__ import annotations

from io import StringIO

import pandas as pd
import requests

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
UA = {"User-Agent": "Mozilla/5.0 (compatible; sp500-dual-screener/1.0; educational project)"}


def get_sp500_constituents() -> tuple[list[str], dict[str, str]]:
    """Return (tickers, {ticker: company_name}) scraped from Wikipedia.

    Wikipedia rejects requests without a User-Agent header (HTTP 403 from
    datacenter IPs), so we fetch the HTML explicitly with `requests` and a
    proper UA, then let pandas parse the tables from the raw HTML.
    Dots in class-share tickers (BRK.B) are normalized to Yahoo's dashes (BRK-B).
    """
    resp = requests.get(WIKI_URL, headers=UA, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text))
    df = tables[0]
    tickers = [str(t).replace(".", "-") for t in df["Symbol"]]
    names = dict(zip(tickers, df["Security"].astype(str)))
    return tickers, names


def fetch_1h(tickers: list[str], period: str = "1y") -> pd.DataFrame:
    """Download 1-hour bars for a list of tickers (regular session only).

    Imported lazily so unit tests don't require yfinance/network.
    """
    import yfinance as yf

    return yf.download(
        tickers=" ".join(tickers),
        period=period,
        interval="1h",
        group_by="ticker",
        auto_adjust=False,
        prepost=False,   # regular trading hours only
        threads=True,
        progress=False,
    )


def to_2h(df: pd.DataFrame) -> pd.DataFrame:
    """Combine consecutive 1-hour bars within each trading day into 2-hour bars.

    A regular US session has 7 hourly bars (09:30 ... 15:30). Pairing
    consecutive bars *within one day* yields 4 bars per day:
    (09:30+10:30) (11:30+12:30) (13:30+14:30) (15:30 alone).

    Synthesis rule: open = first bar's open, close = second bar's close,
    high = max of highs, low = min of lows. Pairing never crosses a day
    boundary, so a short holiday session still resamples correctly.
    """
    df = df.dropna(subset=["Open", "Close"])
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close"])

    dates = [ts.date() for ts in df.index]
    o = df["Open"].to_numpy()
    h = df["High"].to_numpy()
    l = df["Low"].to_numpy()
    c = df["Close"].to_numpy()
    idx = df.index

    rows, times = [], []
    i, n = 0, len(df)
    while i < n:
        if i + 1 < n and dates[i + 1] == dates[i]:
            rows.append((o[i], max(h[i], h[i + 1]), min(l[i], l[i + 1]), c[i + 1]))
            times.append(idx[i])
            i += 2
        else:
            rows.append((o[i], h[i], l[i], c[i]))
            times.append(idx[i])
            i += 1

    return pd.DataFrame(rows, columns=["open", "high", "low", "close"],
                        index=pd.DatetimeIndex(times, name="time"))
