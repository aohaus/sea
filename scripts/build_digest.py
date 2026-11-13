#!/usr/bin/env python3
"""Build a small Japan-Malaysia digest from data already in this repository.

Reads
  basic/my/indicators.json       trend series (Japan's direct investment, FDI inflow, GDP growth, FX)
  signals/data/signals.json      news about Japanese companies in Malaysia
  basic/holidays/holidays.json   public holidays of Japan and Malaysia

Writes three JSON files into the directory given with --out (nothing in the repository changes):
  digest.json        {"generated_at", "trends": [{id, label, unit, change, source, as_of, series}],
                      "news": [{date, source, link, title, companies, topics}]}  (the three top stories)
  holidays-JP.json   {"generated_at", "through", "days": [{d, n, s}]}
  holidays-MY.json   the same, with "scope" on each day

They are shaped as single documents for a page or a tool that shows the day's essentials.

Usage:
  python scripts/build_digest.py --out /path/to/dir
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TZ = timezone(timedelta(hours=8))
NEWS_DAYS = 21

# id, indicator, label, unit, divisor, digits, how the page words the change ("pct" = % change, "pt" = difference)
TRENDS = [
    ("fdi_from_japan", "fdi_from_japan", "日本からマレーシアへの直接投資", "億円", 1e8, 0, "pct"),
    ("fdi_inflow", "fdi_inflow", "マレーシアの対内直接投資（全世界）", "億ドル", 1e8, 0, "pct"),
    ("gdp_growth", "gdp_growth_real", "実質GDP成長率", "%", 1, 1, "pt"),
    ("fx", "exchange_rate", "為替（1米ドル＝リンギ、年平均）", "RM", 1, 2, "pct"),
]


def trends() -> list[dict]:
    ind = json.loads((ROOT / "basic" / "my" / "indicators.json").read_text(encoding="utf-8"))["indicators"]
    out = []
    for tid, key, label, unit, div, digits, change in TRENDS:
        series = (ind.get(key) or {}).get("series") or []
        if not series or not series[0].get("observations"):
            continue
        s = series[0]
        obs = [[o["year"], round(o["value"] / div, digits)] for o in s["observations"] if o.get("value") is not None][-12:]
        out.append({"id": tid, "label": label, "unit": unit, "change": change, "series": obs,
                    "source": s.get("source_id", ""), "as_of": (s.get("retrieved_at") or "")[:10]})
    return out


def news() -> list[dict]:
    path = ROOT / "signals" / "data" / "signals.json"
    if not path.exists():
        return []
    items = json.loads(path.read_text(encoding="utf-8")).get("items", [])
    cutoff = (datetime.now(TZ) - timedelta(days=NEWS_DAYS)).isoformat()
    # The top stories name a watchlist company and a business topic; one story per company, newest first.
    picked, seen = [], set()
    for i in sorted(items, key=lambda i: i["date"], reverse=True):
        if i["date"] < cutoff or not i.get("companies") or not i.get("topics") or i["companies"][0] in seen:
            continue
        seen.add(i["companies"][0])
        picked.append({"date": i["date"][:10], "source": i["source"], "link": i["link"], "title": i["title_ja"] or i["title"],
                       "companies": i["companies"], "topics": i["topics"]})
        if len(picked) == 3:
            break
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(TZ).isoformat(timespec="seconds")

    digest = {"generated_at": now, "trends": trends(), "news": news()}
    (out / "digest.json").write_text(json.dumps(digest, ensure_ascii=False), encoding="utf-8")

    hol = ROOT / "basic" / "holidays" / "holidays.json"
    counts = {}
    if hol.exists():
        h = json.loads(hol.read_text(encoding="utf-8"))
        for c, days in h["countries"].items():
            doc = {"generated_at": h["generated_at"], "through": h["through"],
                   "days": [{"d": x["date"], "n": x["name"], "s": x["status"], **({"scope": x["scope"]} if "scope" in x else {})} for x in days]}
            (out / f"holidays-{c}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            counts[c] = len(days)
    print(json.dumps({"trends": len(digest["trends"]), "news": len(digest["news"]), "holidays": counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
