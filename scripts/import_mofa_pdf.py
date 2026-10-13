#!/usr/bin/env python3
"""Import a MOFA "基礎データ" page saved as PDF into basic/<code>/mofa_basic.json.

MOFA rejects automated requests from GitHub Actions (HTTP 403), so pages are
saved from a browser as PDF and imported with this script. It reads the PDF's
text layer, takes the 一般事情 section (items up to 略史) and 政体 / 元首 from
政治体制・内政, and writes an extract in the same format as fetch_basic.py, with
retrieval_method "manual_pdf". Run `python scripts/fetch_basic.py --build`
afterwards to rebuild profile.json.

Requires PyMuPDF (pip install pymupdf); it is not needed for the automatic fetch.

Usage:
  python scripts/import_mofa_pdf.py <saved.pdf> <country code>   # e.g. brunei.pdf bn
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone

import pymupdf

from fetch_basic import BASIC_DIR, clean, find_date, load_json, strip_numbering, write_json

ITEM = re.compile(r"^\d+　")  # "1　面積"


def section(lines: list[str], start: str, stops: tuple[str, ...]) -> list[str]:
    i = lines.index(start)
    j = next((k for k in range(i + 1, len(lines)) if lines[k] in stops), len(lines))
    return lines[i + 1:j]


def rows_from(lines: list[str]) -> list[dict]:
    rows: list[dict] = []
    for line in lines:
        if ITEM.match(line):
            rows.append({"label": strip_numbering(clean(line)), "cells": []})
        elif rows and line.strip():
            rows[-1]["cells"].append(clean(line))
    return [{"label": r["label"], "cells": [" ".join(r["cells"])]} for r in rows]


def breadcrumb_title(lines: list[str]) -> str | None:
    # "トップページ > 国・地域 > アジア > ... > ブルネイ基礎データ" -> "ブルネイ基礎データ"
    crumb = next((l for l in lines if l.startswith("トップページ >")), None)
    return clean(crumb.split(">")[-1]) if crumb else None


def pdf_created_at(doc) -> str:
    # PDF date "D:20261013011700Z" -> ISO 8601; fall back to now.
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", doc.metadata.get("creationDate") or "")
    if not m:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    y, mo, d, h, mi, s = m.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}+00:00"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf")
    parser.add_argument("code", help="country code in basic/countries.json, e.g. bn")
    args = parser.parse_args()

    country = next(c for c in load_json(BASIC_DIR / "countries.json")["countries"] if c["code"] == args.code)
    source = next(s for s in load_json(BASIC_DIR / "sources.json")["sources"] if s["id"] == "mofa_basic")
    url = source["url_template"].format(mofa_code=country["mofa_code"])

    doc = pymupdf.open(args.pdf)
    lines = [line.rstrip() for page in doc for line in page.get_text().splitlines()]
    head = lines.index("基礎データ")
    general = section(lines, "一般事情", ("政治体制・内政",))
    general = general[:next((k for k, l in enumerate(general) if re.match(r"^\d+　略史", l)), len(general))]
    political = [r for r in rows_from(section(lines, "政治体制・内政", ("外交・国防", "経済")))
                 if r["label"] in ("政体", "元首")]
    created = pdf_created_at(doc)

    extract = {
        "source_id": "mofa_basic",
        "url": url,
        "retrieved_at": created,
        "retrieval_method": "manual_pdf",
        "retrieval_note": (
            f"自動取得が HTTP 403 のため、ブラウザで保存した PDF（{created} 作成）のテキストから抽出"
            " / Extracted from a browser-saved PDF of the page, because automatic fetching returned HTTP 403"
        ),
        "status": "ok",
        "page_title": breadcrumb_title(lines),
        "page_last_updated": find_date(lines[head + 1]),
        "tables": [
            {"section": clean(lines[head - 2]), "header": [],
             "rows": [{"label": "国・地域名", "cells": [clean(lines[head - 1])]}]},
            {"section": "一般事情", "header": [], "rows": rows_from(general)},
            {"section": "政治体制・内政", "header": [], "rows": political},
        ],
    }
    write_json(BASIC_DIR / args.code / "mofa_basic.json", extract)
    print(f"{args.code}: {extract['page_last_updated']} "
          + ", ".join(r["label"] for t in extract["tables"] for r in t["rows"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
