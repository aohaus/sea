#!/usr/bin/env python3
"""Backfill signals/data/signals.json from the whole Campur.ai archive for the last N days.

The regular collector (collect_signals.py) only searches for watchlist names and keywords, and the
archive search returns a limited window per term. This script instead pages through every archived
article, newest first, until it reaches articles older than --days, and keeps the ones that
collect_signals.to_item() accepts. The result is merged into the existing signals.json with the same
rules as a regular run (deduplicated, at most KEEP_DAYS old, at most MAX_ITEMS items).

Usage:
  python scripts/backfill_signals.py [--days 92] [--page 1000]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect_signals as cs  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=92)
    ap.add_argument("--page", type=int, default=1000)
    args = ap.parse_args()

    now = datetime.now(cs.TZ)
    since = now - timedelta(days=args.days)
    companies, _ = cs.load_watchlist()
    found, scanned, offset, oldest = {}, 0, 0, None
    while True:
        for attempt in range(3):
            try:
                r = requests.get(cs.BASE, params={"limit": str(args.page), "offset": str(offset)}, headers=cs.HEADERS, timeout=(10, 60))
                r.raise_for_status()
                batch = r.json().get("articles", [])
                break
            except (requests.RequestException, ValueError) as exc:
                if attempt == 2:
                    print(f"stopped at offset {offset}: {type(exc).__name__}: {exc}", file=sys.stderr)
                    return 1
                time.sleep(3)
        if not batch:
            break
        scanned += len(batch)
        for a in batch:
            item = cs.to_item(a, companies)
            if item and item["date"] >= since.isoformat():
                found[item["link"]] = item
        dates = [a.get("isoDate") or "" for a in batch if a.get("isoDate")]
        oldest = min(dates) if dates else oldest
        offset += len(batch)
        if oldest and datetime.fromisoformat(oldest.replace("Z", "+00:00")) < since:
            break
        time.sleep(cs.PAUSE)

    old = json.loads(cs.OUT.read_text(encoding="utf-8")) if cs.OUT.exists() else {"items": []}
    cutoff = (now - timedelta(days=cs.KEEP_DAYS)).isoformat()
    merged = {i["link"]: i for i in old.get("items", [])}
    merged.update(found)
    seen, items = set(), []
    for i in sorted(merged.values(), key=lambda i: i["date"], reverse=True):
        key = (i["source"], i["title_ja"])
        if i["date"] < cutoff or key in seen:
            continue
        seen.add(key)
        items.append(i)
    items = items[: cs.MAX_ITEMS]

    data = {
        "generated_at": now.isoformat(timespec="seconds"),
        "checked_at": now.isoformat(timespec="seconds"),
        "source": {"name": "Campur.ai", "url": "https://campur.ai.studio/"},
        "status": {"backfill": {"days": args.days, "scanned": scanned, "matched": len(found), "oldest_scanned": oldest}, "errors": []},
        "items": items,
    }
    cs.OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"scanned": scanned, "matched": len(found), "items": len(items), "oldest_scanned": oldest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
