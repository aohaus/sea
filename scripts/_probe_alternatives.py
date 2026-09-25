#!/usr/bin/env python3
"""TEMPORARY probe (not part of the deliverable): try non-RSS-endpoint
alternatives for the 4 sources without a working RSS URL.

1. robots.txt -> declared sitemaps
2. Common sitemap / news-sitemap paths
3. Google News RSS search restricted to the site
"""
import re
from urllib.parse import quote
from xml.etree import ElementTree

import feedparser
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml, text/xml, application/rss+xml, */*;q=0.8",
}

SITES = {
    "thestar": ("https://www.thestar.com.my", "thestar.com.my", "en-MY", "MY:en"),
    "theedge": ("https://theedgemalaysia.com", "theedgemalaysia.com", "en-MY", "MY:en"),
    "sinchew": ("https://www.sinchew.com.my", "sinchew.com.my", "zh-CN", "MY:zh-Hans"),
    "borneopost": ("https://www.theborneopost.com", "theborneopost.com", "en-MY", "MY:en"),
}

SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/news-sitemap.xml",
    "/sitemap-news.xml",
    "/news_sitemap.xml",
    "/sitemap/news.xml",
    "/googlenews.xml",
]


def get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.status_code, r.content
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode()


def describe_sitemap(body):
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as e:
        return f"not XML ({e})"
    tag = root.tag.split("}")[-1]
    urls = [el for el in root.iter() if el.tag.endswith("}loc") or el.tag == "loc"]
    news = sum(1 for el in root.iter() if "sitemap-news" in el.tag)
    sample = urls[0].text.strip() if urls and urls[0].text else ""
    return f"<{tag}> locs={len(urls)} news_tags={news} first={sample[:100]}"


def main():
    for sid, (base, domain, hl, ceid) in SITES.items():
        print(f"\n==================== {sid} ====================")

        status, body = get(base + "/robots.txt")
        declared = []
        if status == 200:
            declared = re.findall(rb"(?im)^\s*sitemap:\s*(\S+)", body)
            declared = [d.decode() for d in declared]
        print(f"[robots.txt] {status} declared_sitemaps={declared}")

        for url in dict.fromkeys(declared + [base + p for p in SITEMAP_PATHS]):
            status, body = get(url)
            detail = describe_sitemap(body) if status == 200 else ""
            print(f"[sitemap] {status} {url}  {detail}")

        query = quote(f"site:{domain} when:1d")
        gn = f"https://news.google.com/rss/search?q={query}&hl={hl}&gl=MY&ceid={ceid}"
        status, body = get(gn)
        if status == 200:
            feed = feedparser.parse(body)
            first = feed.entries[0].title[:80] if feed.entries else ""
            print(f"[google-news] {status} version={feed.version} entries={len(feed.entries)} first={first!r}")
        else:
            print(f"[google-news] {status}")
        print(f"              {gn}")


if __name__ == "__main__":
    main()
