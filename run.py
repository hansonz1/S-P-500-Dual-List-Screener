"""Entry point: run the full daily screen and write JSON + PDF to output/.

Usage:  python run.py
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

from screener import commentary
from screener.data import fetch_1h, get_sp500_constituents, to_2h
from screener.report import build_pdf
from screener.screen import screen_ticker

CHUNK = 100  # tickers per download request
OUT_DIR = pathlib.Path(__file__).parent / "output"


def main() -> int:
    today = dt.date.today().isoformat()
    OUT_DIR.mkdir(exist_ok=True)

    print("Fetching S&P 500 constituent list...")
    tickers, names = get_sp500_constituents()
    print(f"  {len(tickers)} tickers")

    print("Fetching market benchmark (^GSPC)...")
    mkt_raw = fetch_1h(["^GSPC"])
    market = to_2h(mkt_raw["^GSPC"] if "^GSPC" in mkt_raw.columns.get_level_values(0)
                   else mkt_raw)
    print(f"  {len(market)} 2h bars")

    results_cross, results_bb, failed = [], [], []
    ok = 0
    for start in range(0, len(tickers), CHUNK):
        chunk = tickers[start:start + CHUNK]
        print(f"Downloading {start + 1}-{start + len(chunk)} of {len(tickers)}...")
        raw = fetch_1h(chunk)
        for sym in chunk:
            try:
                sub = raw[sym].dropna(how="all")
                bars = to_2h(sub)
                res = screen_ticker(bars, market)
                ok += 1
                if res["cross"]:
                    results_cross.append({"ticker": sym, "name": names.get(sym, ""),
                                          **res["cross"]})
                if res["bb"]:
                    results_bb.append({"ticker": sym, "name": names.get(sym, ""),
                                       **res["bb"]})
            except Exception as e:  # noqa: BLE001 — one bad ticker must not kill the run
                failed.append(sym)
                print(f"  skip {sym}: {e}")

    results_cross.sort(key=lambda x: x["ticker"])
    results_bb.sort(key=lambda x: x["ticker"])
    data = {
        "date": today,
        "stats": {"total": len(tickers), "ok": ok, "failed": failed},
        "cross": results_cross,
        "bb": results_bb,
    }

    json_path = OUT_DIR / f"screen_results_{today}.json"
    json_path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    pdf_path = OUT_DIR / f"screen_report_{today}.pdf"
    build_pdf(data, str(pdf_path))

    text = None
    try:
        text = commentary.generate(data)
    except Exception as e:  # noqa: BLE001 — commentary is optional
        print(f"Commentary skipped: {e}")
    if text:
        (OUT_DIR / f"commentary_{today}.md").write_text(
            f"# Market commentary — {today}\n\n{text}\n", encoding="utf-8")

    g = sum(1 for c in results_cross if c["type"] == "golden")
    d = len(results_cross) - g
    print(f"Done. List1: {g} golden / {d} death. "
          f"List2: {len(results_bb)} breakouts. "
          f"OK {ok}/{len(tickers)}, failed: {failed or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
