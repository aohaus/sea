#!/usr/bin/env python3
"""Temporary probe for Japanese city data sources (removed before merge)."""
import io, json, re
from pathlib import Path
import requests
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parent.parent / "basic" / "cities" / "_probe" / "japan.md"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
parts = ["# Japan probe\n"]
s = requests.Session()

def page_links(url, pat=r"\.(xlsx?|csv|zip)$"):
    r = s.get(url, headers=H, timeout=60)
    parts.append(f"## {url}\n- HTTP {r.status_code}, {r.headers.get('content-type')}")
    if r.ok and "html" in r.headers.get("content-type", ""):
        soup = BeautifulSoup(r.content, "html.parser")
        parts.append(f"- title: {soup.title.get_text(strip=True) if soup.title else ''}")
        for a in soup.find_all("a", href=True):
            if re.search(pat, a["href"], re.I):
                parts.append(f"  - {a.get_text(' ', strip=True)[:70]} → {requests.compat.urljoin(r.url, a['href'])}")
    parts.append("")

for u in ["https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/files_kenmin.html",
          "https://www.esri.cao.go.jp/jp/sna/sonota/kenmin/kenmin_top.html",
          "https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/main_2022.html",
          "https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/main_2021.html"]:
    try:
        page_links(u)
    except Exception as e:
        parts.append(f"## {u}\n- error {e}\n")

for u in ["https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList?searchWord=%E5%B8%82%E7%94%BA%E6%9D%91",
          "https://www.e-stat.go.jp/"]:
    try:
        r = s.get(u, headers=H, timeout=60)
        parts.append(f"## {u}\n- HTTP {r.status_code}\n- {r.text[:400]}\n")
    except Exception as e:
        parts.append(f"## {u}\n- error {e}\n")

# UN WUP 2025: Japanese cities
try:
    import openpyxl
    body = s.get("https://population.un.org/wup/assets/Download/Cities/WUP2025-F21-DEGURBA-Cities_Pop.xlsx", headers=H, timeout=120).content
    ws = openpyxl.load_workbook(io.BytesIO(body), read_only=True)["Data"]
    header, rows = None, []
    for r in ws.iter_rows(values_only=True):
        if header is None:
            if r and r[0] == "Index":
                header = list(r)
            continue
        d = dict(zip(header, r))
        if d.get("ISO3_Code") == "JPN" and (d.get(2025) or 0) >= 300:
            rows.append((d["City_Name"], d.get(2025)))
    parts.append("## UN WUP 2025 Japanese cities >= 300k (2025, thousand)")
    parts += [f"- {n}: {v:,.0f}" for n, v in sorted(rows, key=lambda t: -t[1])]
except Exception as e:
    parts.append(f"## UN error {e}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(parts), encoding="utf-8")
print("\n".join(parts)[:4000])
