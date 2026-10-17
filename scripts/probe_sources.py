#!/usr/bin/env python3
"""Temporary: inspect candidate source files (run in GitHub Actions; removed before merge)."""
import io
import re
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import openpyxl

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "ja,en;q=0.8"}


def get(url):
    r = requests.get(url, headers=UA, timeout=60)
    print("GET", url, "->", r.status_code, r.headers.get("content-type"), len(r.content))
    return r


def links(url, pat=None, text_pat=None, limit=60):
    r = get(url)
    soup = BeautifulSoup(r.content, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        href = urljoin(r.url, a["href"])
        text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))[:140]
        if (pat and re.search(pat, href)) or (text_pat and re.search(text_pat, text)):
            out.append((text, href))
    for t, h in out[:limit]:
        print("  LINK", t, "|", h)
    return out


def xlsx_summary(url, rows=25):
    r = get(url)
    try:
        wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        print("  not xlsx:", exc, r.content[:200]); return
    for ws in wb.worksheets[:4]:
        print("  SHEET", ws.title, ws.max_row, ws.max_column)
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= rows:
                break
            vals = [v for v in row if v is not None]
            if vals:
                print("   ", i, vals[:14])


def section(title):
    print("=" * 30, title, "=" * 30)


def xlsx_rows(url, sheet_index=0, match=None, limit=60, show_header=8):
    r = get(url)
    try:
        wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        print("  not xlsx:", exc, r.content[:120]); return
    print("  SHEETS", wb.sheetnames[:12], len(wb.sheetnames))
    ws = wb.worksheets[sheet_index]
    n = 0
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        vals = [v for v in row]
        text = " ".join(str(v) for v in vals if v is not None)
        if i < show_header or (match and re.search(match, text)):
            print("   ", i, [v for v in vals if v is not None][:32])
            n += 1
            if n > limit:
                break


section("JNTO 2025 sheet")
xlsx_rows("https://www.jnto.go.jp/statistics/data/_files/20260916_1615-5.xlsx", sheet_index=1,
          match=r"タイ|シンガポール|マレーシア|インドネシア|フィリピン|ベトナム|ミャンマー|カンボジア|ラオス|ブルネイ|東ティモール|計", show_header=5)

section("ISA zairyu newest lids")
found = links("https://www.moj.go.jp/isa/policies/statistics/toukei_ichiran_touroku.html", pat=r"lid=", limit=10)
for t, h in found[:1]:
    section("e-Stat datalist " + t)
    fl = links(h, pat=r"file-download", text_pat=r"国籍", limit=60)
    r = get(h)
    soup = BeautifulSoup(r.content, "html.parser")
    for li in soup.select("li, tr, article, div.stat-dataset_list-item")[:0]:
        pass
    # print title + EXCEL links in document order
    for a in soup.find_all("a", href=True):
        tx = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if "stat_infid" in a["href"] or "file-download" in a["href"]:
            print("   ORDER", tx[:80], "|", urljoin(r.url, a["href"])[-60:])

section("JETRO FDI retry")
xlsx_rows("https://www.jetro.go.jp/ext_images/world/japan/stats/fdi/data/country1_25cy.xlsx", show_header=70, limit=80)
sys.exit(0)
