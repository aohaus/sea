#!/usr/bin/env python3
"""Fetch recent USD/MYR/JPY exchange rates.

Source: Frankfurter (https://frankfurter.dev), a free API serving the European Central Bank's daily
reference rates. No key is needed. Rates are published on ECB working days, around 16:00 CET.

Writes
  basic/fx/latest.json  {"generated_at", "source", "date", "usd_myr", "usd_jpy", "myr_jpy",
                         "series": [[date, usd_myr, usd_jpy, myr_jpy], ...]}  (about 90 days)

A failed fetch leaves the previous file as it is and exits 0, so the workflow carries on.

Usage:
  python scripts/fetch_fx.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "basic" / "fx" / "latest.json"
BASES = ["https://api.frankfurter.dev/v1", "https://api.frankfurter.app"]
HEADERS = {"User-Agent": "sea-fx/0.1 (+https://github.com/aohaus/sea)"}
DAYS = 90


def main() -> int:
    now = datetime.now(timezone(timedelta(hours=8)))
    start = (now - timedelta(days=DAYS)).date().isoformat()
    rates, used, errors = None, None, []
    for base in BASES:
        try:
            r = requests.get(f"{base}/{start}..", params={"base": "USD", "symbols": "MYR,JPY"}, headers=HEADERS, timeout=(10, 20))
            r.raise_for_status()
            rates = r.json().get("rates") or {}
            if rates:
                used = base
                break
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{base}: {type(exc).__name__}: {exc}")
    if not rates:
        print(json.dumps({"kept_previous": True, "errors": errors}, ensure_ascii=False))
        return 0
    series = [[d, round(v["MYR"], 4), round(v["JPY"], 2), round(v["JPY"] / v["MYR"], 3)]
              for d, v in sorted(rates.items()) if v.get("MYR") and v.get("JPY")]
    last = series[-1]
    data = {"generated_at": now.isoformat(timespec="seconds"),
            "source": {"name": "Frankfurter (ECB reference rates)", "url": used},
            "date": last[0], "usd_myr": last[1], "usd_jpy": last[2], "myr_jpy": last[3], "series": series}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"date": last[0], "usd_myr": last[1], "usd_jpy": last[2], "myr_jpy": last[3], "days": len(series)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
