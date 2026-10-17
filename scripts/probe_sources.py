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



ASEAN = r"タイ|シンガポール|マレーシア|インドネシア|フィリピン|ベトナム|ミャンマー|カンボジア|ラオス|ブルネイ|東ティモール|総数|アジア"

section("ISA newest datalist")
found = links("https://www.moj.go.jp/isa/policies/statistics/toukei_ichiran_touroku.html", pat=r"lid=", limit=0)
for t, h in found[-6:]:
    print("  NEWEST", t, "|", h)
dec = [x for x in found if "12" in x[0].translate(str.maketrans("０１２３４５６７８９", "0123456789"))]
t, h = dec[-1]
section("datalist " + t)
r = get(h)
soup = BeautifulSoup(r.content, "html.parser")
target = None
seen = False
for a in soup.find_all("a", href=True):
    tx = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
    if "stat_infid" in a["href"] or "file-download" in a["href"]:
        print("   ORDER", tx[:80], "|", a["href"][-50:])
        if tx.startswith("国籍・地域別 在留資格（在留目的）別 在留外国人"):
            seen = True
        elif seen and "file-download" in a["href"] and target is None:
            target = urljoin(r.url, a["href"])
print("TARGET", target)
if target:
    xlsx_rows(target, match=ASEAN, show_header=12, limit=60)

section("MOF bpfdi")
fl = links("https://www.mof.go.jp/policy/international_policy/reference/balance_of_payments/bpfdi.htm",
           pat=r"\.(csv|xlsx?|htm)$", limit=80)

section("JETRO FDI via page")
s2 = requests.Session()
s2.headers.update(UA)
r = s2.get("https://www.jetro.go.jp/world/japan/stats/fdi.html", timeout=60)
print("page", r.status_code, len(r.content))
for a in BeautifulSoup(r.content, "html.parser").find_all("a", href=True):
    if re.search(r"\.xlsx?$", a["href"]):
        print("  X", re.sub(r"\s+", " ", a.get_text(" ", strip=True))[:60], "|", a["href"])
r = s2.get("https://www.jetro.go.jp/ext_images/world/japan/stats/fdi/data/country1_25cy.xlsx",
           headers={"Referer": "https://www.jetro.go.jp/world/japan/stats/fdi.html"}, timeout=60)
print("xlsx", r.status_code, r.headers.get("content-type"), len(r.content), r.content[:300])
sys.exit(0)
