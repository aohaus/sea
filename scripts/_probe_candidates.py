#!/usr/bin/env python3
"""TEMPORARY probe script (not part of the deliverable) to find working RSS
URLs for sources that failed the initial check. Tries several candidate URLs
per source on a real GitHub Actions runner and reports which ones parse as a
valid feed with entries.
"""
import sys
import feedparser
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.9, */*;q=0.7",
}

CANDIDATES = {
    "thestar": [
        "https://www.thestar.com.my/rss/editors-picks/news",
        "https://www.thestar.com.my/rss",
        "https://www.thestar.com.my/rss/news/nation",
        "https://www.thestar.com.my/news/nation/rss",
        "https://www.thestar.com.my/RSS",
    ],
    "malaysiakini": [
        "https://www.malaysiakini.com/en/news.rss",
        "https://www.malaysiakini.com/rss/en/news.rss",
        "https://www.malaysiakini.com/rss",
        "https://en.malaysiakini.com/rss/news.rss",
    ],
    "theedge": [
        "https://theedgemalaysia.com/rss/latest-news",
        "https://theedgemalaysia.com/rss.html",
        "https://theedgemalaysia.com/rss",
        "http://www.theedgemarkets.com/myrssmarkets",
        "http://feeds.theedgemarkets.com/theedgemarkets/mytopstories.rss",
    ],
    "astroawani": [
        "https://www.astroawani.com/rss/latest.xml",
        "https://www.astroawani.com/rss.xml",
        "http://english.astroawani.com/rss/national/public",
        "https://english.astroawani.com/rss.xml",
    ],
    "nst": [
        "https://www.nst.com.my/rss/flats/nation",
        "https://www.nst.com.my/feed",
        "https://www.nst.com.my/rss.xml",
    ],
    "sinchew": [
        "https://www.sinchew.com.my/feed/",
        "https://www.sinchew.com.my/rss",
        "https://www.sinchew.com.my/?feed=rss2",
    ],
    "borneopost": [
        "https://www.theborneopost.com/feed/",
        "https://www.theborneopost.com/rss",
        "https://www.theborneopost.com/feed",
    ],
}


def try_url(session, url):
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        feed = feedparser.parse(resp.content)
        return resp.status_code, feed.version, len(feed.entries)
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"


def main():
    ok = True
    with requests.Session() as session:
        for source_id, urls in CANDIDATES.items():
            print(f"\n=== {source_id} ===")
            found = False
            for url in urls:
                status, version, entries = try_url(session, url)
                mark = "OK" if status == 200 and version and isinstance(entries, int) and entries > 0 else "  "
                print(f"[{mark}] {status} version={version} entries={entries}  {url}")
                if mark == "OK" and not found:
                    found = True
            if not found:
                ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
