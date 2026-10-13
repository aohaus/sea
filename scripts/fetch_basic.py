#!/usr/bin/env python3
"""Collect basic country data (with provenance) into basic/<code>/.

Sources are listed in basic/sources.json. A source applies to a country when the
country has a value for the source's `country_key` in basic/countries.json
(e.g. jetro_code, mofa_code). For each (country, source) pair it:
  1. Fetches the page (url_template filled with that code).
  2. Extracts labelled rows as plain text -- from tables ("tables" parser, JETRO)
     or from headings and the text under them ("headings" parser, MOFA) -- together
     with the page date and the retrieval timestamp, and writes them to
     basic/<code>/<source_id>.json. The page HTML itself is NOT stored
     (storage policy (a): extracted values + URL + retrieval date only).
     If the extracted rows did not change, the file is left untouched.
  3. Rebuilds basic/<code>/profile.json from all extracts of that country,
     mapping rows to the fields in basic/schema/fields.json. Every value keeps its
     source_id, URL, retrieval date and, when the text names one, the original
     statistical source ("出所:..." / "出典:...").

A run summary is written to basic/fetch_report.json: for each country and
source, `status` is the data in use (a cached or manually imported extract can
be "ok") and `fetch_status`/`fetch_error` are what this run's request returned.
The script exits with status 1 when no request in this run succeeded, so an
outage is not hidden behind cached data.

Usage:
  python scripts/fetch_basic.py                    # fetch all sources + build
  python scripts/fetch_basic.py --source mofa_basic
  python scripts/fetch_basic.py --build            # rebuild profiles from saved extracts only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString

REPO_ROOT = Path(__file__).resolve().parent.parent
BASIC_DIR = REPO_ROOT / "basic"
TIMEOUT_SECONDS = 20
DELAY_SECONDS = 3  # be polite to the source sites

HEADERS = {
    "default": {
        "User-Agent": "sea-basic-collector/0.1 (+https://github.com/aohaus/sea)",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en;q=0.8",
    },
    # For sites that reject non-browser clients (selected per source in sources.json).
    "browser": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #

def nearest_heading(node) -> str | None:
    heading = node.find_previous(["h1", "h2", "h3", "h4"])
    return clean(heading.get_text(" ")) if heading else None


def extract_tables(soup: BeautifulSoup) -> list[dict]:
    tables = []
    for table in soup.find_all("table"):
        header: list[str] = []
        rows = []
        for tr in table.find_all("tr"):
            cells = [clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
            if not any(cells):
                continue
            # A row made only of <th> is a column header (e.g. years).
            if tr.find("td") is None:
                header = cells
                continue
            rows.append({"label": cells[0], "cells": cells[1:]})
        if rows:
            tables.append({"section": nearest_heading(table), "header": header, "rows": rows})
    # Some pages use definition lists instead of tables.
    for dl in soup.find_all("dl"):
        rows = [
            {"label": clean(dt.get_text(" ")), "cells": [clean(dd.get_text(" "))]}
            for dt in dl.find_all("dt")
            if (dd := dt.find_next_sibling("dd")) is not None
        ]
        if rows:
            tables.append({"section": nearest_heading(dl), "header": [], "rows": rows})
    return tables


HEADING_TAGS = ["h2", "h3", "h4", "h5"]


def strip_numbering(label: str) -> str:
    """'1 面積' / '(1)面積' / '1.面積' -> '面積'."""
    return re.sub(r"^\s*(?:\(?\d+[).．、]?|[①-⑳])\s*", "", label).strip()


def extract_sections(soup: BeautifulSoup) -> list[dict]:
    """Rows from headings and the text that follows each of them (MOFA 基礎データ style)."""
    root = soup.find("main") or soup.find(id="maincontents") or soup.body or soup
    tables = []
    current = {"section": None, "header": [], "rows": []}
    for heading in root.find_all(HEADING_TAGS):
        parts = []
        for el in heading.next_elements:
            if getattr(el, "name", None) in HEADING_TAGS:
                break
            if isinstance(el, NavigableString) and heading not in el.parents \
                    and el.parent.name not in ("script", "style"):
                parts.append(str(el))
        text = clean(" ".join(parts))
        label = clean(heading.get_text(" "))
        if heading.name == "h2" or not text:
            # A section heading: start a new group of rows.
            if current["rows"]:
                tables.append(current)
            current = {"section": label, "header": [], "rows": []}
            if not text:
                continue
        current["rows"].append({"label": strip_numbering(label), "cells": [text]})
    if current["rows"]:
        tables.append(current)
    return tables


_ERA_BASE = {"令和": 2018, "平成": 1988}


def find_date(text: str) -> str | None:
    """First date in text, Western ('2026年8月19日') or Japanese era ('令和8年6月23日')."""
    m = re.search(r"(令和|平成)?\s*(\d{1,4}|元)年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if not m:
        return None
    era, y, mo, d = m.groups()
    year = 1 if y == "元" else int(y)
    if era:
        year += _ERA_BASE[era]
    elif year < 1900:
        return None
    return f"{year:04d}-{int(mo):02d}-{int(d):02d}"


def page_last_updated(soup: BeautifulSoup) -> str | None:
    text = clean(soup.get_text(" "))
    m = re.search(r"最終更新日\s*[:：]?\s*(.{0,20})", text)
    if m:
        return find_date(m.group(1))
    # MOFA pages print the revision date (in the Japanese era) near the top.
    root = soup.find("main") or soup.find(id="maincontents") or soup.body or soup
    return find_date(clean(root.get_text(" "))[:300])


PARSERS = {"tables": extract_tables, "headings": extract_sections}


def fetch(country: dict, source: dict, session: requests.Session) -> dict:
    key = source["country_key"]
    url = source["url_template"].format(**{key: country[key]})
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = {"source_id": source["id"], "url": url, "retrieved_at": retrieved_at}
    try:
        resp = session.get(url, headers=HEADERS[source.get("headers", "default")], timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return {**result, "status": "error", "error": f"{type(exc).__name__}: {exc}"}
    result["http_status"] = resp.status_code
    result["final_url"] = resp.url
    if resp.status_code != 200:
        return {**result, "status": "error", "error": f"HTTP {resp.status_code}"}
    resp.encoding = resp.apparent_encoding if not resp.encoding else resp.encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.find("title")
    tables = PARSERS[source["parser"]](soup)
    return {
        **result,
        "status": "ok" if tables else "no_rows",
        "page_title": clean(title.get_text()) if title else None,
        "page_last_updated": page_last_updated(soup),
        "tables": tables,
    }


# --------------------------------------------------------------------------- #
# Profile building
# --------------------------------------------------------------------------- #

_NUM = r"\d[\d,]*(?:\.\d+)?"
_JA_NUMBER = re.compile(rf"(?:({_NUM})億)?(?:({_NUM})万)?({_NUM})?")


def parse_ja_number(text: str) -> float | None:
    """Parse the first number in text, honouring 億/万 (e.g. 33万855 -> 330855)."""
    for m in _JA_NUMBER.finditer(text):
        oku, man, rest = m.groups()
        if not any((oku, man, rest)):
            continue
        to_f = lambda s: float(s.replace(",", "")) if s else 0.0  # noqa: E731
        value = to_f(oku) * 1e8 + to_f(man) * 1e4 + to_f(rest)
        return int(value) if value.is_integer() else value
    return None


def parse_as_of(text: str) -> str | None:
    m = re.search(r"[（(][^）)]*?(\d{4})年(?:(\d{1,2})月(?:(\d{1,2})日)?)?", text)
    if not m:
        return None
    y, mo, d = m.groups()
    return y + (f"-{int(mo):02d}" if mo else "") + (f"-{int(d):02d}" if d else "")


_OPEN, _CLOSE = "(（〔[［", ")）〕]］"


def parse_original_source(text: str) -> str | None:
    """Return the text after "出所:"/"出典:" up to the bracket that encloses it, or 、/。."""
    m = re.search(r"(?:出所|出典)\s*[:：]\s*", text)
    if not m:
        return None
    depth, out = 0, []
    for ch in text[m.end():]:
        if ch in _OPEN:
            depth += 1
        elif ch in _CLOSE:
            if depth == 0:
                break
            depth -= 1
        elif ch in "、。" and depth == 0:
            break
        out.append(ch)
    return "".join(out).strip() or None


def leading_name(text: str) -> str:
    """'クアラルンプール 人口207万人(...)' -> 'クアラルンプール'."""
    return re.split(r"\s*(?:人口|[(（〔])", text, maxsplit=1)[0].strip()


def norm_label(label: str) -> str:
    """Normalise a table label for exact matching (drop spaces and a trailing note in brackets)."""
    label = re.sub(r"[(（][^()（）]*[)）]$", "", label)
    return re.sub(r"[\s・:：]", "", label)


def build_profile(country: dict, fields: list[dict], extracts: list[dict]) -> dict:
    profile = {
        "code": country["code"],
        "iso3": country.get("iso3"),
        "name_ja": country["name_ja"],
        "name_en": country["name_en"],
        "fields": {},
    }
    for f in fields:
        profile["fields"][f["id"]] = {
            "label_ja": f["label_ja"],
            "label_en": f["label_en"],
            "unit": f["unit"],
            "phase": f["phase"],
            "values": [],
        }
    by_label = {norm_label(j): f for f in fields for j in f["labels"]}
    official = next(f for f in fields if f["id"] == "official_language")

    for extract in extracts:
        if extract.get("status") != "ok":
            continue
        provenance = {
            "source_id": extract["source_id"],
            "url": extract.get("final_url") or extract["url"],
            "retrieved_at": extract["retrieved_at"],
            "page_last_updated": extract.get("page_last_updated"),
            "retrieval_method": extract.get("retrieval_method", "auto"),
        }

        def add(field: dict, value, text: str, label: str, original_source: str | None,
                note: str | None = None) -> None:
            values = profile["fields"][field["id"]]["values"]
            if any(v["value"] == value and v["source_id"] == provenance["source_id"] for v in values):
                return
            derive = field.get("derive_provenance", True)
            values.append({
                "value": value,
                "value_text": text,
                "as_of": parse_as_of(text) if derive else None,
                "original_source": original_source if derive else None,
                "source_label": label,
                "note": note,
                **provenance,
            })

        for table in extract["tables"]:
            # Phase-2 indicator tables have one column per year; they are kept in the
            # extract and will be handled by the phase-2 builder.
            if len(table["header"]) > 2:
                continue
            last_source = None
            for row in table["rows"]:
                if not row["cells"]:
                    continue
                text = " ".join(row["cells"])
                source = parse_original_source(text)
                note = None
                if source == "同上":
                    source = last_source
                    note = "出所「同上」を直前の行の出所に置き換え / 'ditto' resolved to the previous row's source"
                if source:
                    last_source = source
                label = norm_label(row["label"])
                field = by_label.get(label)
                if field:
                    if field["type"] == "number":
                        value = parse_ja_number(text)
                    elif field.get("value_rule") == "leading_name":
                        value = leading_name(text)
                    else:
                        value = text
                    add(field, value, text, row["label"], source, note)
                # "言語" rows often state the official language inline:
                # "公用語はマレー語" or "ラオス語(公用語)".
                if label == "言語":
                    names = re.findall(r"公用語(?:は|:|：)[、\s]*([^、。,，()（）]+)", text)
                    names += re.findall(r"([^、。,，()（）\s]+)\s*[(（]公用語[)）]", text)
                    for name in names:
                        name = re.sub(r"と(?:定め|され|する).*$", "", name.strip())
                        add(official, name, text, row["label"], source,
                            note="「言語」欄の記述から抽出 / extracted from the Languages row")
    return profile


# --------------------------------------------------------------------------- #

def same_content(a: dict | None, b: dict) -> bool:
    """True when two extracts differ only in their retrieval timestamp."""
    if not a:
        return False
    strip = lambda d: {k: v for k, v in d.items() if k != "retrieved_at"}  # noqa: E731
    return strip(a) == strip(b)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build", action="store_true", help="rebuild profiles only (no network)")
    parser.add_argument("--source", action="append", help="only fetch these source ids")
    args = parser.parse_args()

    countries = load_json(BASIC_DIR / "countries.json")["countries"]
    # Static (phase 1) fields only; time series are built by fetch_indicators.py.
    fields = [f for f in load_json(BASIC_DIR / "schema" / "fields.json")["fields"] if f["phase"] == 1]
    sources = [s for s in load_json(BASIC_DIR / "sources.json")["sources"] if s.get("parser")]

    report = []
    session = requests.Session()
    first_request = True
    for country in countries:
        extracts = []
        for source in sources:
            if not country.get(source["country_key"]):
                continue
            extract_path = BASIC_DIR / country["code"] / f"{source['id']}.json"
            previous = load_json(extract_path) if extract_path.exists() else None
            extract = previous
            fetched = None
            if not args.build and (not args.source or source["id"] in args.source):
                if not first_request:
                    time.sleep(DELAY_SECONDS)
                first_request = False
                fetched = fetch(country, source, session)
                if fetched["status"] == "ok" or not (previous and previous.get("status") == "ok"):
                    # Keep the old file (and its retrieved_at) when nothing changed.
                    if not same_content(previous, fetched):
                        write_json(extract_path, fetched)
                        extract = fetched
                # else: never overwrite a good extract with a failed fetch.
            if extract:
                extracts.append(extract)
                report.append({
                    "code": country["code"],
                    "source_id": source["id"],
                    "url": extract["url"],
                    "status": extract["status"],
                    "error": extract.get("error"),
                    "page_last_updated": extract.get("page_last_updated"),
                    "retrieval_method": extract.get("retrieval_method", "auto"),
                    # This run's request, separate from the data in use (which may be cached).
                    "fetch_status": fetched["status"] if fetched else "not_run",
                    "fetch_error": fetched.get("error") if fetched else None,
                })
        profile = build_profile(country, fields, extracts)
        write_json(BASIC_DIR / country["code"] / "profile.json", profile)
        filled = sorted(k for k, v in profile["fields"].items() if v["values"])
        for r in report:
            if r["code"] == country["code"]:
                r["fields_filled"] = sorted(
                    k for k, v in profile["fields"].items()
                    if any(x["source_id"] == r["source_id"] for x in v["values"])
                )
        print(f"{country['code']:<3} {', '.join(filled) or '(no data)'}")

    write_json(BASIC_DIR / "fetch_report.json", {"results": report})
    if args.build:
        return 0
    failed = [f"{r['code']}/{r['source_id']}: {r['fetch_error']}" for r in report if r["fetch_status"] not in ("ok", "not_run")]
    for line in failed:
        print(f"FETCH FAILED {line}", file=sys.stderr)
    return 0 if any(r["fetch_status"] == "ok" for r in report) else 1


if __name__ == "__main__":
    sys.exit(main())
