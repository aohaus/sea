#!/usr/bin/env python3
"""Temporary feasibility probe for city / regional data sources (removed before merge).

Fetches each candidate URL and writes basic/cities/_probe/report.md with the
HTTP status, content type, size and a short structural summary (JSON keys,
links to data files on HTML pages, first text of PDFs/CSVs). Nothing here is
stored as data; it only tells us which sources can be read automatically.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parent.parent / "basic" / "cities" / "_probe" / "report.md"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en,ja;q=0.8",
}

CANDIDATES = [
    # Malaysia (DOSM / data.gov.my)
    ("MY state GDP real (API)", "https://api.data.gov.my/data-catalogue?id=gdp_state_real_supply&limit=3"),
    ("MY catalogue page", "https://open.dosm.gov.my/data-catalogue"),
    ("MY archive per-capita by state", "https://archive.data.gov.my/data/dataset/gross-domestic-product-gdp-per-capita-by-state-at-current-prices"),
    # Philippines (PSA OpenSTAT PXWeb)
    ("PH per capita GDP prov/HUC (API meta)", "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2A/PPA/0092A5GPPA8.px"),
    ("PH API root", "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2A/PPA"),
    # Thailand (NSO yearbook, chapter 10)
    ("TH NSO T10.1 2025", "https://www.nso.go.th/public/e-book/Statistical-Yearbook/SYB-2025_webPage/File%20SYB/2025/10/T%2010.1%202025.pdf"),
    ("TH NSO T10.14 2025", "https://www.nso.go.th/public/e-book/Statistical-Yearbook/SYB-2025_webPage/File%20SYB/2025/10/T%2010.14%202025.pdf"),
    ("TH NESDC GRP page", "https://www.nesdc.go.th/main.php?filename=gross_regional"),
    # Vietnam (GSO / NSO)
    ("VN GSO EN home", "https://www.gso.gov.vn/en/"),
    ("VN NSO EN home", "https://www.nso.gov.vn/en/"),
    ("VN PX-Web", "https://pxweb.gso.gov.vn/pxweb/en/"),
    # Indonesia (BPS)
    ("ID BPS PDRB per kapita table search", "https://www.bps.go.id/en/statistics-table?subject=528"),
    # UN World Urbanization Prospects 2025
    ("UN WUP downloads (cities)", "https://population.un.org/wup/downloads?tab=Cities"),
    ("UN WUP home", "https://population.un.org/wup/"),
]

DATA_LINK = re.compile(r"\.(xlsx?|csv|zip|pdf|px|json)(\?|$)|/api/|download", re.I)


def summarize(resp: requests.Response) -> str:
    ctype = resp.headers.get("content-type", "")
    body = resp.content
    lines = [f"- content-type: `{ctype}` · {len(body):,} bytes · final URL: {resp.url}"]
    if "json" in ctype or body[:1] in (b"{", b"["):
        try:
            data = resp.json()
            text = json.dumps(data, ensure_ascii=False)[:1500]
            lines.append(f"- JSON (first 1500 chars):\n\n```\n{text}\n```")
            return "\n".join(lines)
        except ValueError:
            pass
    if "pdf" in ctype or body[:4] == b"%PDF":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(body))
            text = (reader.pages[0].extract_text() or "")[:1500]
            lines.append(f"- PDF, {len(reader.pages)} pages; page 1 text (first 1500 chars):\n\n```\n{text}\n```")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"- PDF (text extraction failed: {exc})")
        return "\n".join(lines)
    if "html" in ctype:
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if DATA_LINK.search(href):
                links.append(f"{a.get_text(' ', strip=True)[:60]} → {href}")
        lines.append(f"- HTML title: {title}")
        lines.append(f"- data-like links ({len(links)}):")
        lines += [f"  - {l}" for l in links[:60]]
        if not links:
            lines.append(f"- body text (first 800 chars): {soup.get_text(' ', strip=True)[:800]}")
        return "\n".join(lines)
    lines.append(f"- text (first 800 chars):\n\n```\n{resp.text[:800]}\n```")
    return "\n".join(lines)


def main() -> None:
    parts = ["# City data source probe\n"]
    session = requests.Session()
    for name, url in CANDIDATES:
        parts.append(f"## {name}\n\n{url}\n")
        try:
            resp = session.get(url, headers=HEADERS, timeout=60)
            parts.append(f"- HTTP {resp.status_code}")
            if resp.ok:
                parts.append(summarize(resp))
        except Exception as exc:  # noqa: BLE001
            parts.append(f"- error: {type(exc).__name__}: {exc}")
        parts.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(OUT.read_text(encoding="utf-8")[:3000])


if __name__ == "__main__":
    main()
