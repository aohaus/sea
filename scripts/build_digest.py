#!/usr/bin/env python3
"""Build a small Japan-Malaysia digest from data already in this repository.

Reads
  basic/my/indicators.json       trend series (Japan's direct investment, FDI inflow, GDP growth)
  basic/fx/latest.json           recent USD/MYR/JPY rates (annual averages are used when it is missing)
  signals/data/signals.json      news about Japanese companies in Malaysia
  basic/holidays/holidays.json   public holidays of Japan and Malaysia

Writes three JSON files into the directory given with --out (nothing in the repository changes):
  digest.json        {"generated_at", "trends": [{id, label, unit, change, source, as_of, series}],
                      "fx": {kind, date, usd_myr, usd_jpy, myr_jpy, prev, series, source},
                      "news": [{date, source, link, title, companies, topics}]}  (the three top stories)
  signals.json       {"generated_at", "items": [...]}  the newest 250 stories, trimmed
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


def fx() -> dict | None:
    """USD, MYR and JPY side by side: recent daily rates when basic/fx/latest.json exists, else annual averages."""
    latest = ROOT / "basic" / "fx" / "latest.json"
    if latest.exists():
        d = json.loads(latest.read_text(encoding="utf-8"))
        s = d.get("series") or []
        return {"kind": "daily", "date": d["date"], "usd_myr": d["usd_myr"], "usd_jpy": d["usd_jpy"], "myr_jpy": d["myr_jpy"],
                "prev": {"date": s[0][0], "usd_myr": s[0][1], "usd_jpy": s[0][2], "myr_jpy": s[0][3]} if len(s) > 1 else None,
                "series": [[x[0], x[3]] for x in s], "source": (d.get("source") or {}).get("name", "")}

    def annual(code: str) -> dict[int, float]:
        ind = json.loads((ROOT / "basic" / code / "indicators.json").read_text(encoding="utf-8"))["indicators"]
        series = (ind.get("exchange_rate") or {}).get("series") or []
        return {o["year"]: o["value"] for o in series[0]["observations"] if o.get("value")} if series else {}

    my, jp = annual("my"), annual("jp")
    years = sorted(set(my) & set(jp))
    if not years:
        return None

    def at(y: int) -> dict:
        return {"date": str(y), "usd_myr": round(my[y], 2), "usd_jpy": round(jp[y], 1), "myr_jpy": round(jp[y] / my[y], 2)}

    return {"kind": "annual", **at(years[-1]), "prev": at(years[-2]) if len(years) > 1 else None,
            "series": [[str(y), round(jp[y] / my[y], 2)] for y in years[-12:]], "source": "World Bank WDI (annual average)"}


def signals(limit: int = 250) -> dict:
    path = ROOT / "signals" / "data" / "signals.json"
    if not path.exists():
        return {"generated_at": None, "items": []}
    d = json.loads(path.read_text(encoding="utf-8"))
    keep = ("date", "source", "link", "title_ja", "title", "summary_ja", "companies", "topics")
    return {"generated_at": d.get("generated_at"), "items": [{k: i.get(k) for k in keep} for i in d.get("items", [])[:limit]]}


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

    digest = {"generated_at": now, "trends": trends(), "fx": fx(), "news": news()}
    (out / "digest.json").write_text(json.dumps(digest, ensure_ascii=False), encoding="utf-8")
    sig = signals()
    (out / "signals.json").write_text(json.dumps(sig, ensure_ascii=False), encoding="utf-8")

    hol = ROOT / "basic" / "holidays" / "holidays.json"
    counts = {}
    if hol.exists():
        h = json.loads(hol.read_text(encoding="utf-8"))
        for c, days in h["countries"].items():
            doc = {"generated_at": h["generated_at"], "through": h["through"],
                   "days": [{"d": x["date"], "n": x["name"], "s": x["status"], **({"scope": x["scope"]} if "scope" in x else {})} for x in days]}
            (out / f"holidays-{c}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            counts[c] = len(days)
    print(json.dumps({"trends": len(digest["trends"]), "fx": (digest["fx"] or {}).get("kind"), "news": len(digest["news"]), "signals": len(sig["items"]), "holidays": counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
