#!/usr/bin/env python3
"""Collect JETRO "概況・基本統計" pages for ASEAN members into basic/<code>/.

For each country in basic/countries.json it:
  1. Fetches https://www.jetro.go.jp/world/asia/<jetro_code>/basic_01.html.
  2. Extracts every table on the page as plain text (label + cells), together
     with the page's "最終更新日" and the retrieval timestamp, and writes it to
     basic/<code>/jetro_basic.json. The page HTML itself is NOT stored
     (storage policy (a): extracted values + URL + retrieval date only).
  3. Rebuilds basic/<code>/profile.json, mapping table rows to the fields in
     basic/schema/fields.json. Every value keeps its source_id, URL, retrieval
     date and, when the cell names one, the original statistical source
     ("出所：...").

A run summary is written to basic/fetch_report.json. The script exits with
status 1 only when no country could be fetched at all.

Usage:
  python scripts/fetch_jetro_basic.py            # fetch + build
  python scripts/fetch_jetro_basic.py --build    # rebuild profiles from saved extracts only
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
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
BASIC_DIR = REPO_ROOT / "basic"
SOURCE_ID = "jetro_basic"
TIMEOUT_SECONDS = 20
DELAY_SECONDS = 3  # be polite to jetro.go.jp

HEADERS = {
    "User-Agent": "sea-basic-collector/0.1 (+https://github.com/aohaus/sea)",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.8",
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


def page_last_updated(soup: BeautifulSoup) -> str | None:
    m = re.search(r"最終更新日\s*[:：]?\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", clean(soup.get_text(" ")))
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    return f"{y:04d}-{mo:02d}-{d:02d}"


def fetch_country(country: dict, template: str, session: requests.Session) -> dict:
    url = template.format(jetro_code=country["jetro_code"])
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = {"source_id": SOURCE_ID, "url": url, "retrieved_at": retrieved_at}
    try:
        resp = session.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return {**result, "status": "error", "error": f"{type(exc).__name__}: {exc}"}
    result["http_status"] = resp.status_code
    result["final_url"] = resp.url
    if resp.status_code != 200:
        return {**result, "status": "error", "error": f"HTTP {resp.status_code}"}
    resp.encoding = resp.apparent_encoding if not resp.encoding else resp.encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.find("title")
    tables = extract_tables(soup)
    return {
        **result,
        "status": "ok" if tables else "no_tables",
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


def parse_original_source(text: str) -> str | None:
    m = re.search(r"出所\s*[:：]\s*([^）)]+)", text)
    return m.group(1).strip() if m else None


def norm_label(label: str) -> str:
    return re.sub(r"[\s・:：]", "", label)


def build_profile(country: dict, fields: list[dict], extract: dict | None) -> dict:
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
    if not extract or extract.get("status") != "ok":
        return profile

    provenance = {
        "source_id": extract["source_id"],
        "url": extract.get("final_url") or extract["url"],
        "retrieved_at": extract["retrieved_at"],
        "page_last_updated": extract.get("page_last_updated"),
    }

    def add(field: dict, text: str, label: str, note: str | None = None) -> None:
        values = profile["fields"][field["id"]]["values"]
        if any(v["value_text"] == text for v in values):
            return
        values.append({
            "value": parse_ja_number(text) if field["type"] == "number" else text,
            "value_text": text,
            "as_of": parse_as_of(text),
            "original_source": parse_original_source(text),
            "jetro_label": label,
            "note": note,
            **provenance,
        })

    for table in extract["tables"]:
        # Phase-2 indicator tables have one column per year; they are kept in the
        # extract and will be handled by the phase-2 builder.
        if len(table["header"]) > 2:
            continue
        for row in table["rows"]:
            if not row["cells"]:
                continue
            label = norm_label(row["label"])
            text = " ".join(row["cells"])
            for field in fields:
                if any(label.startswith(norm_label(j)) for j in field["jetro_labels"]):
                    add(field, text, row["label"])
                    break
            # "言語" rows often state the official language inline.
            if label.startswith("言語"):
                m = re.search(r"公用語(?:は|:|：)\s*([^、。,，()（）]+)", text)
                if m:
                    official = next(f for f in fields if f["id"] == "official_language")
                    add(official, m.group(1).strip(), row["label"],
                        note="「言語」欄の記述から抽出 / extracted from the Languages row")
    return profile


# --------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build", action="store_true", help="rebuild profiles only (no network)")
    args = parser.parse_args()

    countries = load_json(BASIC_DIR / "countries.json")["countries"]
    fields = load_json(BASIC_DIR / "schema" / "fields.json")["fields"]
    source = next(s for s in load_json(BASIC_DIR / "sources.json")["sources"] if s["id"] == SOURCE_ID)

    report = []
    session = requests.Session()
    for i, country in enumerate(countries):
        extract_path = BASIC_DIR / country["code"] / f"{SOURCE_ID}.json"
        if args.build:
            extract = load_json(extract_path) if extract_path.exists() else None
        else:
            if i:
                time.sleep(DELAY_SECONDS)
            extract = fetch_country(country, source["url_template"], session)
            previous = load_json(extract_path) if extract_path.exists() else None
            # Never overwrite a good extract with a failed fetch.
            if extract["status"] == "ok" or not (previous and previous.get("status") == "ok"):
                write_json(extract_path, extract)
            else:
                extract = previous
        profile = build_profile(country, fields, extract)
        write_json(BASIC_DIR / country["code"] / "profile.json", profile)
        filled = sorted(k for k, v in profile["fields"].items() if v["values"])
        report.append({
            "code": country["code"],
            "url": extract["url"] if extract else None,
            "status": extract["status"] if extract else "missing",
            "error": extract.get("error") if extract else None,
            "page_last_updated": extract.get("page_last_updated") if extract else None,
            "fields_filled": filled,
        })
        print(f"{country['code']:<3} {report[-1]['status']:<10} {', '.join(filled) or report[-1]['error'] or ''}")

    write_json(BASIC_DIR / "fetch_report.json", {
        "source_id": SOURCE_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "countries": report,
    })
    return 0 if any(r["status"] == "ok" for r in report) else 1


if __name__ == "__main__":
    sys.exit(main())
