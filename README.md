S&P 500 Dual-List Screener

An automated quantitative screening pipeline that scans all ~503 S&P 500
constituents daily on 2-hour bars, detects EMA crossovers and ±3σ Bollinger
Band breakouts with rolling-beta regime confirmation, and publishes a daily
PDF report — fully unattended, via GitHub Actions.


⚠️ This is a mechanical screening tool built as a data-engineering project.
Its output is not investment advice.



What it does

Every trading day after the US market close, the pipeline:


Scrapes the current S&P 500 constituent list from Wikipedia (so the
universe never goes stale).
Downloads one year of 1-hour OHLC bars for every constituent plus the
^GSPC benchmark from Yahoo Finance.
Resamples 1-hour bars into 2-hour bars (7 hourly bars per session → 4
two-hour bars, never pairing across a day boundary).
Screens every stock against two independent signal sets (below).
Renders a PDF report + machine-readable JSON, optionally adds an
LLM-written market commentary, and commits everything back to output/ —
so the repo itself is a growing, timestamped signal archive.


The two lists

List 1 — trend change (EMA cross). EMA36 computed on closes crossing
EMA90 computed on opens, within the most recent trading day (4 × 2h bars).
Upward = golden cross, downward = death cross. Using different price fields
for the two averages makes the pair slightly asymmetric and less prone to
oscillating around each other in flat markets.

List 2 — statistical extreme + regime confirmation. Last close outside
Bollinger Bands BB(90, SMA, 3). A ±3σ event is rare by construction, so a
second, independent condition must confirm it: the stock's rolling
Beta(300) versus the S&P 500 must be above its own 252-bar mean for an
upside break, or below it for a downside break. The idea: only flag a
breakout when the stock is simultaneously in an unusual price state and an
unusual market-sensitivity state pointing the same way. An empty List 2 on
most days is expected behavior, not a bug.

Architecture

![Uploading image.png…]()


ModuleResponsibilityscreener/data.pyConstituent scraping, 1h download, 2h resamplingscreener/indicators.pyEMA, Bollinger Bands, O(n) rolling betascreener/screen.pyThe two signal rulesscreener/report.pyPDF rendering (reportlab)screener/commentary.pyOptional LLM commentary (skipped without key)run.pyOrchestration, chunked downloads, error isolation

Engineering notes


O(n) rolling beta. Computing a 300-bar OLS beta at every one of ~1,000
bar positions for ~500 tickers is ~150M multiply-adds done naively. Using
prefix sums, each window's Σx, Σy, Σx², Σxy is recovered in O(1), making
the whole rolling series O(n) per ticker. Verified against naive OLS in
the test suite to 1e-9 relative tolerance.
Real-data hygiene. Ticker normalization (BRK.B → BRK-B), missing
bars, half-day sessions, and newly listed stocks with insufficient history
are all handled explicitly; one bad ticker can never kill the run.
Timestamp-aligned beta. Stock and benchmark returns are inner-joined
on bar timestamps before regression, so gaps in either series can't shift
the alignment.
Tested math. Resampling boundaries, EMA/BB behavior, and the
prefix-sum beta are unit-tested; tests run in CI before every screen.
Zero-cost operations. The entire system runs on GitHub Actions' free
tier with no server, no database, and no paid data feed.


Running it yourself

bashpip install -r requirements.txt
python -m pytest        # verify the math
python run.py           # full scan, ~2-3 minutes; writes to output/

To enable the LLM commentary, set ANTHROPIC_API_KEY (locally as an
environment variable, or in GitHub under Settings → Secrets and variables →
Actions). Everything else works without it.

The scheduled workflow (.github/workflows/daily.yml) runs at 21:35 UTC on
weekdays and commits results back to the repo. Enable it under Settings →
Actions → General → Workflow permissions → Read and write permissions.

Sample output

See output/ for daily JSON + PDF archives. A typical day yields
roughly 15–30 EMA crosses and zero to a few Bollinger breakouts.

Limitations (known and accepted)


Yahoo Finance intraday data is unofficial and occasionally gappy; the
pipeline tolerates but does not repair vendor data errors.
2h bars are synthesized from 1h bars, so the first bar of a half-day
session may aggregate fewer than 2 hours.
The signals are descriptive screens, not a backtested strategy. A
backtesting module measuring historical hit rates is the natural next step.
