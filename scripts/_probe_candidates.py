#!/usr/bin/env python3
"""TEMPORARY probe script (not part of the deliverable) to find working RSS
URLs for sources that failed the initial check. Tries several candidate URLs
per source on a real GitHub Actions runner and reports which ones parse as a
valid feed with entries.
"""
import sys
import feedparser
import requests

HEADER_SETS = {
    "chrome": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.9, */*;q=0.7",
    },
    "googlebot": {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Accept": "*/*",
    },
    "feedly": {
        "User-Agent": "Feedly/1.0 (+http://www.feedly.com/fetcher.html; like FeedFetcher-Google)",
        "Accept": "*/*",
    },
}

# Only sources that still need a working URL after the first probe round.
CANDIDATES = {
    "thestar": [
        "https://www.thestar.com.my/rss/News",
        "https://www.thestar.com.my/rss/Nation",
        "https://www.thestar.com.my/rss/Business",
        "https://www.thestar.com.my/news/nation/rss.xml",
        "https://www.thestar.com.my/rss/editors-picks",
        "https://www.thestar.com.my/rss/editors-picks/news.xml",
        "https://www.thestar.com.my/aseanplus/rss",
        "https://www.thestar.com.my/rssfeed.aspx",
        "https://www.thestar.com.my/rssfeed.ashx",
        "https://www.thestar.com.my/rss/nation",
    ],
    "theedge": [
        "https://theedgemalaysia.com/rss/article",
        "https://theedgemalaysia.com/rss/news",
        "https://theedgemalaysia.com/rssfeed",
        "https://theedgemalaysia.com/sitemap-rss.xml",
        "https://theedgemalaysia.com/api/rss",
        "https://www.theedgemarkets.com/rss",
        "https://www.theedgemarkets.com/rss.html",
        "https://www.theedgemarkets.com/myrssmarkets",
        "https://feeds.theedgemarkets.com/theedgemarkets/mytopstories.rss",
    ],
    "sinchew": [
        "https://www.sinchew.com.my/feed/",
        "https://www.sinchew.com.my/feed",
        "https://www.sinchew.com.my/rss",
        "https://www.sinchew.com.my/?feed=rss2",
        "https://www.sinchew.com.my/category/nation/feed/",
    ],
    "borneopost": [
        "https://www.theborneopost.com/feed/",
        "https://www.theborneopost.com/feed",
        "https://www.theborneopost.com/rss",
        "https://www.theborneopost.com/category/news/feed/",
    ],
}


def try_url(url, header_label, headers):
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        feed = feedparser.parse(resp.content)
        return resp.status_code, feed.version, len(feed.entries)
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"


def main():
    ok = True
    for source_id, urls in CANDIDATES.items():
        print(f"\n=== {source_id} ===")
        found = False
        for url in urls:
            for header_label, headers in HEADER_SETS.items():
                status, version, entries = try_url(url, header_label, headers)
                mark = "OK" if status == 200 and version and isinstance(entries, int) and entries > 0 else "  "
                print(f"[{mark}] {status} version={version} entries={entries}  [{header_label}]  {url}")
                if mark == "OK":
                    found = True
        if not found:
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
