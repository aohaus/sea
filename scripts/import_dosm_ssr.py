#!/usr/bin/env python3
"""Import state GDP per capita from DOSM's "State Socioeconomic Report" press release (PDF).

The release states nominal GDP per capita in its text, e.g. "...above the
national level (RM59,186), namely W.P. Kuala Lumpur (RM144,827), ...". This
script reads the PDF's text layer, takes the national figure and every
"<state> (RM<value>)" in that sentence, and writes
basic/cities/raw/dosm_ssr.json with each value's quoted sentence, the report
year and the publication date, as retrieval_method "manual_pdf". Run
`python scripts/fetch_cities.py --build` afterwards.

Only the states the text names are captured (the release lists those above the
national level); other states need their own state releases.

Requires PyMuPDF (pip install pymupdf).

Usage:
  python scripts/import_dosm_ssr.py <StateSocioeconomicReport.pdf>
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone

import pymupdf

from fetch_basic import BASIC_DIR, write_json

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
     "November", "December"], 1)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf")
    args = parser.parse_args()

    doc = pymupdf.open(args.pdf)
    text = re.sub(r"\s+", " ", " ".join(page.get_text() for page in doc))
    year = int(re.search(r"STATE SOCIOECONOMIC REPORT,? (\d{4})", text).group(1))
    published = None
    m = re.search(r"(\d{1,2}) (" + "|".join(MONTHS) + r") (\d{4})", text)
    if m:
        published = f"{m.group(3)}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"

    # The sentence ends at ")." -- "W.P." inside it contains periods.
    sentence = re.search(r"In terms of GDP per capita,.*?\)\.", text)
    if not sentence:
        raise SystemExit("no 'In terms of GDP per capita' sentence found")
    quote = sentence.group(0)
    national = re.search(r"national level \(RM([\d,]+)\)", quote)
    rows = [{"unit": "Malaysia", "year": year, "value": int(national.group(1).replace(",", "")), "quote": quote}]
    for name, value in re.findall(r"((?:W\.P\. )?[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)?) \(RM([\d,]+)\)", quote):
        rows.append({"unit": name.strip(), "year": year, "value": int(value.replace(",", "")), "quote": quote})

    created = doc.metadata.get("creationDate") or ""
    # PDF date, e.g. "D:20261014222314+08'00'" -> 2026-10-14T22:23:14+08:00
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?:([+-])(\d{2})'?(\d{2})?)?", created)
    retrieved_at = (f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:{m.group(6)}"
                    + (f"{m.group(7)}{m.group(8)}:{m.group(9) or '00'}" if m.group(7) else "+00:00")
                    if m else datetime.now(timezone.utc).isoformat(timespec="seconds"))
    out = {
        "source_id": "dosm_ssr",
        "url": None,
        "url_note": "ユーザーが PDF で提供。公開ページの URL は未記録 / Provided by the user as a PDF; page URL not recorded.",
        "retrieved_at": retrieved_at,
        "retrieval_method": "manual_pdf",
        "publication": f"State Socioeconomic Report, {year}",
        "published": published,
        "currency": "MYR",
        "basis": "current",
        "rows": rows,
    }
    write_json(BASIC_DIR / "cities" / "raw" / "dosm_ssr.json", out)
    for r in rows:
        print(f"{r['unit']:<20} {r['year']} RM{r['value']:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
