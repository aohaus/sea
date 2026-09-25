#!/usr/bin/env python3
"""Health checker for the Malaysian news RSS feeds listed in config/sources.json.

For each source it verifies that:
  1. The HTTP request succeeds with status code 200 (timeout: 10 seconds).
  2. The response body parses as an RSS/Atom XML feed.

A summary table is printed to the terminal. If any source fails, the script
exits with status 1 so that CI/CD marks the run as failed.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import feedparser
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "sources.json"
TIMEOUT_SECONDS = 10

# Browser-like headers so that WAF / bot protection does not reject the request.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, application/atom+xml, application/xml;q=0.9, "
        "text/xml;q=0.9, text/html;q=0.8, */*;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9,ms;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}


@dataclass
class CheckResult:
    id: str
    name: str
    language: str
    url: str
    ok: bool
    status_code: int | None = None
    entries: int = 0
    elapsed_ms: int = 0
    error: str = ""


def load_sources(path: Path = CONFIG_PATH) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)["sources"]


def check_source(session: requests.Session, source: dict) -> CheckResult:
    result = CheckResult(
        id=source["id"],
        name=source["name"],
        language=source["language"],
        url=source["rss_url"],
        ok=False,
    )
    start = time.monotonic()
    try:
        resp = session.get(result.url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
        result.status_code = resp.status_code
        if resp.status_code != 200:
            result.error = f"HTTP {resp.status_code}"
            return result

        # The body must parse as XML and be recognised as an RSS/Atom feed.
        # feedparser tolerates minor well-formedness glitches common in
        # real-world feeds, so only fail when no feed structure is found.
        feed = feedparser.parse(resp.content)
        if not feed.version:
            reason = feed.get("bozo_exception") or "unknown format"
            result.error = f"XML parse failed / not an RSS/Atom feed: {reason}"
            return result

        result.entries = len(feed.entries)
        if result.entries == 0:
            result.error = "Feed parsed but contains no items"
            return result

        result.ok = True
    except requests.exceptions.Timeout:
        result.error = f"Timeout (>{TIMEOUT_SECONDS}s)"
    except requests.exceptions.RequestException as e:
        result.error = f"{type(e).__name__}: {e}"
    finally:
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
    return result


def _truncate(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def print_summary(results: list[CheckResult]) -> None:
    header = f"{'STATUS':<8}{'ID':<14}{'NAME':<22}{'LANG':<6}{'HTTP':<6}{'ITEMS':>6}{'TIME':>9}  DETAIL"
    line = "=" * len(header)
    print(line)
    print("Malaysia News RSS Health Check")
    print(line)
    print(header)
    print("-" * len(header))
    for r in results:
        status = "OK" if r.ok else "FAIL"
        http = str(r.status_code) if r.status_code is not None else "-"
        print(
            f"{status:<8}{r.id:<14}{r.name:<22}{r.language:<6}{http:<6}"
            f"{r.entries:>6}{r.elapsed_ms:>7}ms  {_truncate(r.error)}"
        )
    print("-" * len(header))
    passed = sum(r.ok for r in results)
    print(f"Result: {passed}/{len(results)} passed, {len(results) - passed} failed")

    failed = [r for r in results if not r.ok]
    if failed:
        print("\nFailed sources:")
        for r in failed:
            print(f"  - {r.name} ({r.url}): {r.error}")
    print(line)


def main() -> int:
    sources = load_sources()
    with requests.Session() as session:
        results = [check_source(session, s) for s in sources]
    print_summary(results)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
