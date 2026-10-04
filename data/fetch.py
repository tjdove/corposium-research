"""Fetch the datasets used by docs/calibration/SOURCES.md (Story 2.3). Stdlib only, no keys.

1. USDC/USD hourly candles, Bitstamp public REST API (limit 1000 >= rows per window):
       https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=3600&limit=1000&start=<unix>&end=<unix>
   -> data/usdcusd_1h_calm_2023-02-27_2023-03-03.csv
      data/usdcusd_1h_stress_2023-03-10_2023-03-13.csv          (UTC, end exclusive)
2. USDC total circulating supply, daily, DefiLlama stablecoins API (USDC = id 2):
       https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2
   -> data/usdc_supply_defillama_2023-03-01_2023-03-20.csv      (UTC days, inclusive)

Usage (from the repo root):  python data/fetch.py
"""

import csv
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

URL = "https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=3600&limit=1000&start={start}&end={end}"
WINDOWS = {
    "usdcusd_1h_calm_2023-02-27_2023-03-03.csv": ("2023-02-27", "2023-03-04"),
    "usdcusd_1h_stress_2023-03-10_2023-03-13.csv": ("2023-03-10", "2023-03-14"),
}


def unix(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp())


def fetch(start: int, end: int) -> list[dict]:
    rows = get_json(URL.format(start=start, end=end))["data"]["ohlc"]
    # end is exclusive: keep candles opening before it
    return [r for r in rows if start <= int(r["timestamp"]) < end]


SUPPLY_URL = "https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2"
SUPPLY_FILE = "usdc_supply_defillama_2023-03-01_2023-03-20.csv"


def get_json(url: str):
    req = urllib.request.Request(url, headers={"user-agent": "corposium-research"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def fetch_supply(out_dir: Path) -> None:
    first, last = unix("2023-03-01"), unix("2023-03-20")
    rows = [r for r in get_json(SUPPLY_URL) if first <= int(r["date"]) <= last]
    with open(out_dir / SUPPLY_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date_utc", "unix", "total_circulating_pegged_usd"])
        for r in rows:
            day = datetime.fromtimestamp(int(r["date"]), UTC).strftime("%Y-%m-%d")
            w.writerow([day, r["date"], r["totalCirculating"]["peggedUSD"]])
    print(f"{SUPPLY_FILE}: {len(rows)} rows")


def main() -> None:
    out_dir = Path(__file__).parent
    for name, (first, stop) in WINDOWS.items():
        rows = fetch(unix(first), unix(stop))
        with open(out_dir / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["timestamp_utc", "unix", "open", "high", "low", "close", "volume"])
            for r in rows:
                t = datetime.fromtimestamp(int(r["timestamp"]), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                w.writerow(
                    [t, r["timestamp"], r["open"], r["high"], r["low"], r["close"], r["volume"]]
                )
        print(f"{name}: {len(rows)} rows")
    fetch_supply(out_dir)


if __name__ == "__main__":
    main()
