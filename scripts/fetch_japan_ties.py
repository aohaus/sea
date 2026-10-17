#!/usr/bin/env python3
"""Fetch people and money flows between Japan and each country, from Japanese official statistics.

Three series, one value per country and calendar year:

  jnto_visitors   visitor arrivals to Japan by nationality (日本政府観光局 JNTO「訪日外客統計」).
                  The workbook "国籍/月別 訪日外客数" has one sheet per year; the annual total is
                  the "累計" column. Only complete years (December filled in) are kept.
  isa_residents   foreign residents of Japan by nationality at the end of each year
                  (出入国在留管理庁「在留外国人統計」, published on e-Stat). The ISA page lists
                  one e-Stat data list per survey date; the table "国籍・地域別 在留資格別
                  在留外国人" is read for each year-end (2012 onwards).
  mof_fdi         Japan's direct investment to the country, net flow per calendar year
                  (財務省「国際収支状況」対外直接投資の地域別内訳, table 6d-2, 億円 → yen).

The file links are found from the publishers' pages by their link text, so a renamed
file (JNTO stamps the date into the name, e-Stat ids change every survey) is still found.

Writes basic/ties/<source_id>.json:
  {"source_id", "retrieved_at", "url", "series": {country code: [{year, value, note?, url?}]}}
and basic/ties/fetch_report.json (read by scripts/check_health.py). A source that fails
keeps its saved file; a file is rewritten only when its values change.
fetch_indicators.py turns these into indicator series (fields with "ties_source").

Usage:
  python scripts/fetch_japan_ties.py
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from fetch_basic import BASIC_DIR, HEADERS, load_json, write_json

OUT_DIR = BASIC_DIR / "ties"
TIMEOUT = (15, 90)
DELAY_SECONDS = 1

JNTO_PAGE = "https://www.jnto.go.jp/statistics/data/visitors-statistics/"
ISA_PAGE = "https://www.moj.go.jp/isa/policies/statistics/toukei_ichiran_touroku.html"
ISA_FIRST_YEAR = 2012  # 在留外国人統計 (the earlier 外国人登録者統計 counts a different population)
MOF_CSV = "https://www.mof.go.jp/policy/international_policy/reference/balance_of_payments/bp_trend/bpfdi/fdi/6d-2.csv"
MOF_PAGE = "https://www.mof.go.jp/policy/international_policy/reference/balance_of_payments/bpfdi.htm"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def norm(text) -> str:
    """Full-width digits to ASCII, spaces (including ideographic ones) removed."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(text or "")))


def get(session: requests.Session, url: str) -> requests.Response:
    for attempt in range(2):
        try:
            resp = session.get(url, headers=HEADERS["browser"], timeout=TIMEOUT)
            resp.raise_for_status()
            time.sleep(DELAY_SECONDS)
            return resp
        except (requests.Timeout, requests.ConnectionError):
            if attempt:
                raise
            time.sleep(10)
    raise AssertionError


def page_links(session: requests.Session, url: str) -> list[tuple[str, str]]:
    resp = get(session, url)
    soup = BeautifulSoup(resp.content, "html.parser")
    return [(norm(a.get_text(" ", strip=True)), urljoin(resp.url, a["href"])) for a in soup.find_all("a", href=True)]


def workbook(body: bytes):
    import openpyxl
    return openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)


def number(v) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    s = norm(v).replace(",", "")
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else None


# --------------------------------------------------------------------------- #
# JNTO: visitor arrivals

def fetch_jnto(session, places: dict[str, str]) -> tuple[str, dict]:
    url = next((h for t, h in page_links(session, JNTO_PAGE)
                if "国籍/月別" in t and "訪日外客数" in t and re.search(r"\.xlsx?$", h)), None)
    if not url:
        raise RuntimeError(f"no link '国籍/月別 訪日外客数' on {JNTO_PAGE}")
    wb = workbook(get(session, url).content)
    series: dict[str, list] = {}
    for ws in wb.worksheets:
        if not re.fullmatch(r"\d{4}", ws.title.strip()):
            continue
        year = int(ws.title)
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        header = next((r for r in rows if any(norm(v) == "12月" for v in r)), None)
        if header is None:
            continue
        cols = {norm(v): i for i, v in enumerate(header) if v is not None}
        months = [cols[f"{m}月"] for m in range(1, 13) if f"{m}月" in cols]
        if len(months) != 12:
            continue
        total_col = next((cols[k] for k in ("累計", "年計", "合計", "計") if k in cols), None)
        provisional = any("暫定" in norm(v) or "推計値" in norm(v) for r in rows[:6] for v in r if isinstance(v, str))
        for r in rows:
            label = next((norm(v) for v in r if isinstance(v, str) and v.strip()), "")
            label = re.sub(r"[※＊*]+\d*$", "", label)
            code = places.get(label)
            if not code:
                continue
            if number(r[months[-1]]) is None:  # year not complete yet
                break
            value = number(r[total_col]) if total_col is not None else None
            if value is None:
                value = sum(number(r[i]) or 0 for i in months)
            series.setdefault(code, []).append({"year": year, "value": round(value),
                                                **({"note": "暫定値を含む"} if provisional else {})})
    return url, series


# --------------------------------------------------------------------------- #
# ISA / e-Stat: foreign residents by nationality

def isa_table(rows: list[list], places: dict[str, str]) -> dict[str, float]:
    """Total residents per nationality, from either layout of the table:
    wide (older): one row per nationality, the 総数 column first;
    long (newer): columns 時点 / 州 / 国籍・地域 / 在留資格 / 在留外国人数, total where 在留資格 = 総数."""
    for i, r in enumerate(rows):
        cells = [norm(v) for v in r]
        if "国籍・地域" not in cells:
            continue
        nat = cells.index("国籍・地域")
        out = {}
        if "在留資格" in cells:
            kind = cells.index("在留資格")
            val = next(j for j, c in enumerate(cells) if j > kind and c)
            for row in rows[i + 1:]:
                c = [norm(v) for v in row]
                if len(c) > val and c[kind] == "総数" and c[nat] in places:
                    out.setdefault(places[c[nat]], number(row[val]))
        else:
            total = next(j for j, c in enumerate(cells) if c == "総数")
            for row in rows[i + 1:]:
                label = norm(row[nat]) if len(row) > nat else ""
                if label in places and len(row) > total:
                    out.setdefault(places[label], number(row[total]))
        return {k: v for k, v in out.items() if v is not None}
    raise RuntimeError("header '国籍・地域' not found")


def fetch_isa(session, places: dict[str, str], saved: dict) -> tuple[str, dict, list[str]]:
    """Year-end tables, 2012 onwards. Years already saved are not downloaded again, except the
    latest two (to pick up corrections)."""
    year_ends = {}
    for text, href in page_links(session, ISA_PAGE):
        m = re.fullmatch(r"(\d{4})年12月末", text)
        if m and "lid=" in href and int(m.group(1)) >= ISA_FIRST_YEAR:
            year_ends[int(m.group(1))] = href
    if not year_ends:
        raise RuntimeError(f"no year-end ('YYYY年12月末') links on {ISA_PAGE}")
    have = {o["year"] for obs in saved.get("series", {}).values() for o in obs}
    recent = sorted(year_ends)[-2:]
    series = {code: [o for o in obs if o["year"] not in recent and o["year"] in have] for code, obs in saved.get("series", {}).items()}
    errors = []
    for year, lid_url in sorted(year_ends.items()):
        if year in have and year not in recent:
            continue
        try:
            resp = get(session, lid_url)
            soup = BeautifulSoup(resp.content, "html.parser")
            target, seen = None, False
            for a in soup.find_all("a", href=True):
                text = norm(a.get_text(" ", strip=True))
                if "stat_infid" in a["href"] and re.fullmatch(r"国籍・地域別在留資格.*別在留外国人", text):
                    seen = True
                elif seen and "file-download" in a["href"] and "fileKind=0" in a["href"]:
                    target = urljoin(resp.url, a["href"])
                    break
            if not target:
                raise RuntimeError("table '国籍・地域別 在留資格別 在留外国人' not found")
            ws = workbook(get(session, target).content).worksheets[0]
            values = isa_table([list(r) for r in ws.iter_rows(values_only=True)], places)
            if not values:
                raise RuntimeError("no target nationality in the table")
            for code, v in values.items():
                series.setdefault(code, []).append({"year": year, "value": round(v), "url": target})
        except Exception as exc:  # noqa: BLE001 - keep the other years
            errors.append(f"{year}年12月末 ({lid_url}): {type(exc).__name__}: {exc}")
            for code, obs in saved.get("series", {}).items():  # keep what was saved for that year
                series.setdefault(code, []).extend(o for o in obs if o["year"] == year)
    for obs in series.values():
        obs.sort(key=lambda o: o["year"])
    return ISA_PAGE, series, errors


# --------------------------------------------------------------------------- #
# MOF: direct investment abroad by country (net flow, calendar year)

def fetch_mof(session, places: dict[str, str]) -> tuple[str, dict]:
    raw = get(session, MOF_CSV).content
    rows = list(csv.reader(io.StringIO(raw.decode("cp932"))))
    unit = next((norm(c) for r in rows[:12] for c in r if "単位" in c), "")
    if "億円" not in unit:
        raise RuntimeError(f"unexpected unit: {unit!r}")
    # Country names sit above a row of 実行 / 回収 / ネット; the net flow is the third column of each name.
    head = next(i for i, r in enumerate(rows) if norm(r[4] if len(r) > 4 else "") == "実行")
    cols = {}
    for r in rows[max(0, head - 4):head]:
        for j, c in enumerate(r):
            if norm(c) in places and norm(rows[head][j + 2]) == "ネット":
                cols[places[norm(c)]] = j + 2
    if not cols:
        raise RuntimeError("no target country in the header")
    series: dict[str, list] = {}
    annual = False
    for r in rows[head + 1:]:
        first = norm(r[0]) if r else ""
        if first.startswith("(暦年)"):
            annual = True
            continue
        if first.startswith("(月次)"):
            break
        m = re.fullmatch(r"(\d{4})C\.Y\.(\(P\))?", norm(r[2]) if len(r) > 2 else "")
        if not annual or not m:
            continue
        for code, j in cols.items():
            v = number(r[j])
            if v is not None:
                series.setdefault(code, []).append({"year": int(m.group(1)), "value": v * 1e8,
                                                    **({"note": "速報値"} if m.group(2) or "(P)" in first else {})})
    if not series:
        raise RuntimeError("no annual rows")
    return MOF_CSV, series


# --------------------------------------------------------------------------- #

def save(source_id: str, url: str, series: dict) -> bool:
    path = OUT_DIR / f"{source_id}.json"
    old = load_json(path) if path.exists() else {}
    new = {"source_id": source_id, "retrieved_at": now(), "url": url, "series": dict(sorted(series.items()))}
    if old and {k: v for k, v in old.items() if k != "retrieved_at"} == {k: v for k, v in new.items() if k != "retrieved_at"}:
        return False
    write_json(path, new)
    return True


def main() -> int:
    master = load_json(BASIC_DIR / "countries.json")
    places = {norm(c["name_ja"]): c["code"] for c in master["countries"]}
    # Names the publishers use that differ from countries.json.
    places.update({"東ティモール民主共和国": "tl", "ブルネイ・ダルサラーム": "bn", "ヴィエトナム": "vn"})
    session = requests.Session()
    report = {}

    def run(source_id, fn):
        try:
            url, series, *errs = fn()
            errors = errs[0] if errs else []
            changed = save(source_id, url, series)
            report[source_id] = {"fetch_status": "ok" if not errors else "partial", "fetch_error": "; ".join(errors) or None,
                                 "url": url, "countries": sorted(series),
                                 "years": [min(o["year"] for s in series.values() for o in s),
                                           max(o["year"] for s in series.values() for o in s)] if series else None}
            print(f"{source_id}: {len(series)} countries {report[source_id]['years']}" + ("" if changed else " (unchanged)"))
            for e in errors:
                print(f"  ERROR {e}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - keep the saved file and report the error
            report[source_id] = {"fetch_status": "error", "fetch_error": f"{type(exc).__name__}: {exc}"}
            print(f"{source_id}: {report[source_id]['fetch_error']} (kept the saved file)", file=sys.stderr)

    saved_isa = load_json(OUT_DIR / "isa_residents.json") if (OUT_DIR / "isa_residents.json").exists() else {}
    run("jnto_visitors", lambda: fetch_jnto(session, places))
    run("isa_residents", lambda: fetch_isa(session, places, saved_isa))
    run("mof_fdi", lambda: fetch_mof(session, places))
    write_json(OUT_DIR / "fetch_report.json", report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
