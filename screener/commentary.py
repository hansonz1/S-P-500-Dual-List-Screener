"""Optional LLM market commentary.

If the ANTHROPIC_API_KEY environment variable is set, the daily screen
results are sent to Claude, which writes a short plain-English commentary
(sector clustering, notable names, what the signals suggest). If the key is
absent, this module is skipped silently — the pipeline never depends on it.
"""
from __future__ import annotations

import json
import os

import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"

PROMPT = """You are a market analyst. Below is today's mechanical screen of
S&P 500 stocks on 2-hour bars (EMA crossovers and 3-sigma Bollinger breaks
with beta confirmation), as JSON. Write a concise commentary (150-250 words):
group the names by sector/theme, note anything unusual (clusters, well-known
tickers, one-sided golden/death balance), and state plainly what the signal
mix suggests about short-term breadth. Do NOT give buy/sell advice.

{data}"""


def generate(data: dict) -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    resp = requests.post(
        API_URL,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": 600,
              "messages": [{"role": "user",
                            "content": PROMPT.format(data=json.dumps(data))}]},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]
