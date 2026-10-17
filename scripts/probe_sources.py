#!/usr/bin/env python3
"""Temporary: list data-file links on candidate source pages (run in GitHub Actions; removed before merge)."""
import re
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "ja,en;q=0.8"}
PAGES = [
    "https://www.jnto.go.jp/statistics/data/visitors-statistics/",
    "https://www.jnto.go.jp/statistics/data/_files/",
    "https://www.moj.go.jp/isa/policies/statistics/toukei_ichiran_touroku.html",
    "https://www.moj.go.jp/isa/policies/statistics/toukei_ichiran_nyukan.html",
    "https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00250012&tstat=000001018034",
    "https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00250011",
    "https://www.jetro.go.jp/world/japan/stats/fdi.html",
    "https://www.mof.go.jp/policy/international_policy/reference/balance_of_payments/ebpfdi.htm",
    "https://www.mof.go.jp/policy/international_policy/reference/balance_of_payments/bpfdi.htm",
    "https://www.stat-search.boj.or.jp/api/v1/getMetadata?format=json&lang=jp&db=BP01",
]
PAT = re.compile(r"\.(xlsx?|csv|zip|pdf)(\?|$)|file-download|stat-search/files\?|statInfId|getData", re.I)

for url in PAGES:
    print("=" * 100)
    print("PAGE", url)
    try:
        r = requests.get(url, headers=UA, timeout=40)
        print("STATUS", r.status_code, "FINAL", r.url, "TYPE", r.headers.get("content-type"), "LEN", len(r.content))
        if "json" in (r.headers.get("content-type") or ""):
            print(r.text[:1500])
            continue
        soup = BeautifulSoup(r.content, "html.parser")
        print("TITLE", soup.title.get_text(strip=True) if soup.title else None)
        n = 0
        for a in soup.find_all("a", href=True):
            href = urljoin(r.url, a["href"])
            text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))[:120]
            if PAT.search(href) or any(k in text for k in ("国籍", "国・地域", "地域別", "国別", "在留外国人", "訪日外客", "直接投資", "年表", "統計表")):
                print("  LINK", text, "|", href)
                n += 1
                if n >= 80:
                    break
    except Exception as exc:  # noqa: BLE001
        print("ERROR", type(exc).__name__, exc)
sys.exit(0)
