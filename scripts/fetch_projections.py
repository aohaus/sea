#!/usr/bin/env python3
"""Fetch UN World Population Prospects (estimates and projections to 2100) for the target countries.

The site looks ahead to about 2060. The UN's World Population Prospects (WPP) gives,
for every country, estimates up to the edition's base year and medium-variant
projections to 2100. This downloads the "Demographic Indicators (Medium)" CSV, keeps
the target countries and a few indicators, and writes:

  basic/data/projections.{json,csv}   one row per country, indicator and year, with
                                      kind = estimate / projection, the edition, URL
                                      and retrieval date
  basic/projections_report.json       fetch result (read by scripts/check_health.py)

Only the extracted values are kept, not the CSV. The output is rewritten only when
the values change. If the download fails, the saved table is kept and the error is
recorded in the report (the run still succeeds, so other sources are not held back).

The edition, its last estimate year and the download URL(s) are in
basic/sources.json (id "un_wpp"); update them when a new edition comes out.

Usage:
  python scripts/fetch_projections.py
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import sys
import time
from datetime import datetime, timezone

import requests

from fetch_basic import BASIC_DIR, load_json, write_json

SOURCE_ID = "un_wpp"
FIRST_YEAR, LAST_YEAR = 1950, 2100
# WPP column → (indicator id, Japanese label, English label, unit, scale to the unit)
INDICATORS = {
    "TPopulation1July": ("population", "総人口（7月1日）", "Total population (1 July)", "persons", 1000),
    "MedianAgePop": ("median_age", "年齢の中央値", "Median age", "years", 1),
    "TFR": ("fertility_rate", "合計特殊出生率", "Total fertility rate", "births", 1),
    "LEx": ("life_expectancy", "平均寿命（出生時の平均余命）", "Life expectancy at birth", "years", 1),
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; sea-basic-data/1.0; +https://github.com/aohaus/sea)"}
OUT_JSON = BASIC_DIR / "data" / "projections.json"
OUT_CSV = BASIC_DIR / "data" / "projections.csv"
REPORT = BASIC_DIR / "projections_report.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def download(urls: list[str]) -> tuple[str, bytes]:
    errors = []
    for url in urls:
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=300)
                resp.raise_for_status()
                return url, resp.content
            except requests.HTTPError as exc:
                errors.append(f"{url}: HTTP {exc.response.status_code}")
                break
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == 2:
                    errors.append(f"{url}: {type(exc).__name__}")
                else:
                    time.sleep(10 * (attempt + 1))
    raise RuntimeError("; ".join(errors))


def extract(raw: bytes, places: dict[str, dict], source: dict, url: str, retrieved_at: str) -> list[dict]:
    text = gzip.decompress(raw).decode("utf-8-sig") if raw[:2] == b"\x1f\x8b" else raw.decode("utf-8-sig")
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        place = places.get(r.get("ISO3_code") or "")
        if not place or not r.get("Time"):
            continue
        year = int(float(r["Time"]))
        if not FIRST_YEAR <= year <= LAST_YEAR:
            continue
        for col, (ind, ja, en, unit, scale) in INDICATORS.items():
            v = r.get(col)
            if v in (None, ""):
                continue
            value = float(v) * scale
            rows.append({
                "country_code": place["code"], "country_ja": place["name_ja"], "country_en": place["name_en"],
                "group": place["group"], "indicator_id": ind, "indicator_ja": ja, "indicator_en": en, "unit": unit,
                "year": year, "value": round(value) if unit == "persons" else round(value, 3),
                "kind": "estimate" if year <= source["estimates_until"] else "projection",
                "variant": "estimates" if year <= source["estimates_until"] else "medium",
                "edition": source["edition"], "source_id": SOURCE_ID,
                "source_publisher_ja": source["publisher_ja"], "source_title_ja": source["title_ja"],
                "license": source.get("license"), "url": url, "retrieved_at": retrieved_at,
            })
    rows.sort(key=lambda r: (r["country_code"], r["indicator_id"], r["year"]))
    return rows


def main() -> int:
    master = load_json(BASIC_DIR / "countries.json")
    places = {c["iso3"]: {**c, "group": "asean"} for c in master["countries"]}
    places.update({c["iso3"]: {**c, "group": "benchmark"} for c in master.get("benchmarks", [])})
    source = next(s for s in load_json(BASIC_DIR / "sources.json")["sources"] if s["id"] == SOURCE_ID)
    report = {"source_id": SOURCE_ID, "edition": source["edition"]}
    try:
        url, raw = download(source["url_candidates"])
        rows = extract(raw, places, source, url, now())
        missing = sorted({p["code"] for p in places.values()} - {r["country_code"] for r in rows})
        if not rows or missing:
            raise RuntimeError(f"no rows for {missing or 'any country'}")
    except Exception as exc:  # noqa: BLE001 - keep the saved table and report the error
        report.update({"fetch_status": "error", "fetch_error": f"{type(exc).__name__}: {exc}"})
        write_json(REPORT, report)
        print(f"un_wpp: {report['fetch_error']} (kept the saved table)")
        return 0

    old = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else []
    strip = lambda rs: [{k: v for k, v in r.items() if k != "retrieved_at"} for r in rs]  # noqa: E731
    changed = strip(old) != strip(rows)
    if changed:
        OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    report.update({"fetch_status": "ok", "fetch_error": None, "url": url, "rows": len(rows),
                   "years": [min(r["year"] for r in rows), max(r["year"] for r in rows)]})
    write_json(REPORT, report)
    print(f"un_wpp {source['edition']}: {len(rows)} rows from {url}" + ("" if changed else " (unchanged)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
