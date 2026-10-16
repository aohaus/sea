#!/usr/bin/env python3
"""Collect phase-2 economic indicators (time series, with provenance) into basic/<code>/.

Sources (registered in basic/sources.json):
  worldbank_wdi  World Bank World Development Indicators API (CC BY 4.0)
  imf_weo        IMF World Economic Outlook via the DataMapper API -- auto_fetch is
                 off until permission is obtained (IMF terms restrict automated
                 bulk download and commercial reuse)
  jetro_basic    the "基礎的経済指標" table already saved by fetch_basic.py
  mofa_basic     single population figure already saved (manual import)

Indicator codes per field are in basic/schema/fields.json (phase 2). For every
country it writes:
  basic/<code>/worldbank_wdi.json, basic/<code>/imf_weo.json
      raw observations as returned by the API (no reshaping), with URL and
      retrieval timestamp; left untouched when the observations did not change.
  basic/<code>/indicators.json
      one entry per field; each source is a separate series, values converted to
      the field's base unit (USD, persons, %). Sources are never merged into one
      number, so differences between them stay visible.

Usage:
  python scripts/fetch_indicators.py            # fetch APIs + build
  python scripts/fetch_indicators.py --build    # rebuild indicators.json from saved extracts only
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timezone

import requests

from fetch_basic import BASIC_DIR, HEADERS, load_json, parse_as_of, \
    parse_ja_number, parse_original_source, norm_label, write_json

FIRST_YEAR = 2000
DELAY_SECONDS = 1


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_json(session: requests.Session, url: str, attempts: int = 3):
    for attempt in range(1, attempts + 1):
        try:
            resp = session.get(url, headers=HEADERS["default"], timeout=60)
            resp.raise_for_status()
            return resp.json()
        except (requests.Timeout, requests.ConnectionError):
            if attempt == attempts:
                raise
            time.sleep(5 * attempt)


# --------------------------------------------------------------------------- #
# API fetchers: one request per indicator for all countries
# --------------------------------------------------------------------------- #

def fetch_worldbank(session, countries, fields, last_year) -> dict[str, dict]:
    iso3 = ";".join(c["iso3"] for c in countries)
    out = {c["iso3"]: {"series": {}, "urls": {}, "source_last_updated": {}} for c in countries}
    errors = []
    for f in fields:
        code = f.get("worldbank")
        if not code:
            continue
        url = (f"https://api.worldbank.org/v2/country/{iso3}/indicator/{code}"
               f"?format=json&per_page=20000&date={f.get('first_year', FIRST_YEAR)}:{last_year}")
        try:
            meta, rows = get_json(session, url)
        except Exception as exc:  # noqa: BLE001 - record and continue with other indicators
            errors.append(f"{code}: {type(exc).__name__}: {exc}")
            continue
        for row in rows or []:
            c = out.get(row["countryiso3code"])
            if c is None or row["value"] is None:
                continue
            c["series"].setdefault(code, []).append({"year": int(row["date"]), "value": row["value"]})
            c["urls"][code] = url
            c["source_last_updated"][code] = meta.get("lastupdated")
        time.sleep(DELAY_SECONDS)
    for c in out.values():
        for obs in c["series"].values():
            obs.sort(key=lambda o: o["year"])
    return out, errors


def fetch_imf(session, countries, fields, last_year) -> dict[str, dict]:
    iso3 = "/".join(c["iso3"] for c in countries)
    out = {c["iso3"]: {"series": {}, "urls": {}} for c in countries}
    errors = []
    for f in fields:
        imf = f.get("imf")
        if not imf:
            continue
        code = imf["code"]
        url = f"https://www.imf.org/external/datamapper/api/v1/{code}/{iso3}"
        try:
            data = get_json(session, url)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{code}: {type(exc).__name__}: {exc}")
            continue
        for country_code, by_year in (data.get("values", {}).get(code) or {}).items():
            c = out.get(country_code)
            if c is None:
                continue
            c["series"][code] = sorted(
                ({"year": int(y), "value": v} for y, v in by_year.items()
                 if v is not None and FIRST_YEAR <= int(y) <= last_year),
                key=lambda o: o["year"],
            )
            c["urls"][code] = url
        time.sleep(DELAY_SECONDS)
    return out, errors


# --------------------------------------------------------------------------- #
# Building indicators.json
# --------------------------------------------------------------------------- #

def jetro_unit_scale(unit: str, target: str) -> float | None:
    """Scale for a JETRO unit cell such as '(100万米ドル)' / '(%)'; None when not convertible."""
    if target == "%":
        return 1.0 if re.fullmatch(r"\(\s*%\s*\)", unit) else None
    if target == "USD":
        m = re.fullmatch(r"\((\d*)(億|万)?米ドル\)", unit.replace(",", ""))
        if not m:
            return None
        base = float(m.group(1) or 1)
        return base * {"億": 1e8, "万": 1e4, None: 1}[m.group(2)]
    if target == "LCU/USD":
        return 1.0 if RATE_UNIT.fullmatch(unit) else None
    return None


# '(1米ドルにつき、バーツ、期中平均)' -> currency 'バーツ', basis '期中平均' (also 期末平均, 公定レート).
RATE_UNIT = re.compile(r"\(1米ドルにつき、(?P<currency>[^、]+)、(?P<basis>[^)]+)\)")


def unit_note(unit: str, target: str) -> str | None:
    """A note when a JETRO exchange rate is not the annual average the World Bank series uses."""
    m = RATE_UNIT.fullmatch(unit) if target == "LCU/USD" else None
    if m and m["basis"] != "期中平均":
        return f"JETRO の表記：{m['basis']} / JETRO basis: {m['basis']}"
    return None


def period_year(header: str) -> tuple[int, str | None]:
    """'2024年' -> (2024, None); '2024/25年度' -> (2024, 'fiscal year 2024/25')."""
    m = re.match(r"(\d{4})(?:/(\d{2}))?年(度)?", header)
    year = int(m.group(1))
    note = f"年度 {m.group(1)}/{m.group(2)} / fiscal year" if m.group(2) or m.group(3) else None
    return year, note


def jetro_series(extract: dict, field: dict) -> list[dict]:
    labels = {norm_label(j) for j in field.get("labels", [])}
    for table in extract.get("tables", []):
        header = table["header"]
        if len(header) <= 2 or "単位" not in header:
            continue
        years = [period_year(h) for h in header[2:]]
        for row in table["rows"]:
            if norm_label(row["label"]) not in labels:
                continue
            unit, *cells = row["cells"]
            scale = jetro_unit_scale(unit, field["unit"])
            if scale is None:
                return []
            basis = unit_note(unit, field["unit"])
            obs = []
            for (year, note), cell in zip(years, cells):
                note = "; ".join(n for n in (note, basis) if n) or None
                value = parse_ja_number(cell.replace("△", "-").replace("▲", "-"))
                if value is None:
                    continue
                if cell.strip().startswith(("-", "△", "▲")) and value > 0:
                    value = -value
                obs.append({"year": year, "value": value * scale if scale != 1 else value,
                            **({"note": note} if note else {})})
            return obs
    return []


def single_value(extract: dict, field: dict) -> list[dict]:
    """Population-style single figures from the overview pages ('3,423万人(2025年、出所:...)')."""
    labels = {norm_label(j) for j in field.get("labels", [])}
    for table in extract.get("tables", []):
        if len(table["header"]) > 2:
            continue
        for row in table["rows"]:
            if norm_label(row["label"]) in labels and row["cells"]:
                text = " ".join(row["cells"])
                value, as_of = parse_ja_number(text), parse_as_of(text)
                if value is None or not as_of:
                    return []
                return [{"year": int(as_of[:4]), "value": value, "value_text": text,
                         "original_source": parse_original_source(text)}]
    return []


def build_indicators(country: dict, fields: list[dict], extracts: dict[str, dict]) -> dict:
    result = {"code": country["code"], "iso3": country["iso3"], "name_ja": country["name_ja"],
              "name_en": country["name_en"], "indicators": {}}
    for f in fields:
        series = []
        wb = extracts.get("worldbank_wdi")
        if wb and f.get("worldbank") in wb["series"]:
            series.append({
                "source_id": "worldbank_wdi", "indicator_code": f["worldbank"],
                "url": wb["urls"][f["worldbank"]], "retrieved_at": wb["retrieved_at"],
                "source_last_updated": wb["source_last_updated"].get(f["worldbank"]),
                "observations": wb["series"][f["worldbank"]],
            })
        imf = extracts.get("imf_weo")
        if imf and f.get("imf") and f["imf"]["code"] in imf["series"]:
            code, scale = f["imf"]["code"], f["imf"]["scale"]
            this_year = int(imf["retrieved_at"][:4])
            series.append({
                "source_id": "imf_weo", "indicator_code": code,
                "url": imf["urls"][code], "retrieved_at": imf["retrieved_at"],
                "observations": [
                    {"year": o["year"], "value": o["value"] * scale if scale != 1 else o["value"],
                     **({"note": "IMF 予測値 / IMF projection"} if o["year"] >= this_year else {})}
                    for o in imf["series"][code]
                ],
            })
        for source_id in ("jetro_basic", "mofa_basic"):
            ex = extracts.get(source_id)
            if not ex or ex.get("status") != "ok":
                continue
            obs = jetro_series(ex, f) or single_value(ex, f)
            if obs:
                series.append({
                    "source_id": source_id, "source_label": f["labels"][0],
                    "url": ex.get("final_url") or ex["url"], "retrieved_at": ex["retrieved_at"],
                    "page_last_updated": ex.get("page_last_updated"),
                    "retrieval_method": ex.get("retrieval_method", "auto"),
                    "observations": obs,
                })
        result["indicators"][f["id"]] = {
            "label_ja": f["label_ja"], "label_en": f["label_en"], "unit": f["unit"], "series": series,
        }
    return result


# --------------------------------------------------------------------------- #

def save_extract(code: str, source_id: str, new: dict) -> dict:
    """Write basic/<code>/<source_id>.json unless only retrieved_at would change."""
    path = BASIC_DIR / code / f"{source_id}.json"
    old = load_json(path) if path.exists() else None
    strip = lambda d: {k: v for k, v in d.items() if k != "retrieved_at"}  # noqa: E731
    if old and strip(old) == strip(new):
        return old
    if old:
        # An indicator that failed this run keeps its previous observations.
        missing = set(old.get("series", {})) - set(new["series"])
        for key in ("series", "urls", "source_last_updated"):
            if key in new:
                new[key] = {**{k: v for k, v in old.get(key, {}).items() if k in missing}, **new[key]}
        if strip(old) == strip(new):
            return old
    write_json(path, new)
    return new


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build", action="store_true", help="rebuild indicators.json only (no network)")
    args = parser.parse_args()

    master = load_json(BASIC_DIR / "countries.json")
    # Benchmarks (e.g. Japan) get the API indicators too, for comparison.
    countries = master["countries"] + master.get("benchmarks", [])
    fields = [f for f in load_json(BASIC_DIR / "schema" / "fields.json")["fields"] if f["phase"] == 2]
    last_year = datetime.now(timezone.utc).year + 5  # include IMF projections

    # Sources with auto_fetch false in sources.json (e.g. IMF, whose terms require
    # permission for automated bulk download) are skipped.
    enabled = {s["id"] for s in load_json(BASIC_DIR / "sources.json")["sources"] if s.get("auto_fetch")}
    fetchers = {"worldbank_wdi": fetch_worldbank, "imf_weo": fetch_imf}
    errors: dict[str, list[str]] = {}
    if not args.build:
        session = requests.Session()
        retrieved_at = now()
        for source_id, fetcher in fetchers.items():
            if source_id not in enabled:
                continue
            data, errors[source_id] = fetcher(session, countries, fields, last_year)
            for c in countries:
                save_extract(c["code"], source_id, {"source_id": source_id, "retrieved_at": retrieved_at,
                                                    **data[c["iso3"]]})

    report = []
    for c in countries:
        extracts = {}
        for source_id in ("worldbank_wdi", "imf_weo", "jetro_basic", "mofa_basic"):
            path = BASIC_DIR / c["code"] / f"{source_id}.json"
            if path.exists():
                extracts[source_id] = load_json(path)
        result = build_indicators(c, fields, extracts)
        write_json(BASIC_DIR / c["code"] / "indicators.json", result)
        coverage = {k: [s["source_id"] for s in v["series"]] for k, v in result["indicators"].items()}
        report.append({"code": c["code"], "coverage": coverage})
        print(f"{c['code']:<3} " + "  ".join(f"{k}:{len(v)}" for k, v in coverage.items()))

    write_json(BASIC_DIR / "indicators_report.json", {"errors": errors, "countries": report})
    for source_id, errs in errors.items():
        for e in errs:
            print(f"ERROR {source_id} {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
