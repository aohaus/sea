#!/usr/bin/env python3
"""Collect haze-related news for the Haze Monitor's "アクションする" page (haze/actions.html).

The articles come from Campur.ai (https://campur.ai.studio), which archives the news of 15 Malaysian
and Japanese outlets and adds Japanese titles and summaries. Its archive search is read here,
server-side: the site sends no CORS headers, so the page cannot read it from the browser.

Writes
  haze/data/news.json   {"generated_at", "source", "status", "items": [{id, date, source, link,
                         title_ja, title, summary_ja, lang, tags}]}, newest first

Each item keeps the outlet's link, the original title and Campur.ai's Japanese title and summary (the
summary shortened), so the page shows the headline and sends readers to the outlet for the article.

The hourly workflow calls this every run; it only fetches when news.json is older than MIN_AGE, so
Campur.ai is read about every 3 hours. A failed fetch keeps the previous items and records the error.

Usage:
  python scripts/collect_haze_news.py [--force]
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "haze" / "data" / "news.json"
TZ = timezone(timedelta(hours=8))
BASE = "https://campur.ai.studio/api/archive/articles"
HEADERS = {"User-Agent": "sea-haze-collector/0.1 (+https://github.com/aohaus/sea)"}
MIN_AGE = timedelta(minutes=170)
KEEP_DAYS = 90
MAX_ITEMS = 400
SUMMARY_CHARS = 140

# Search words (English, Malay, Japanese). Campur.ai matches them against titles and summaries.
QUERIES = ["haze", "jerebu", "ヘイズ", "煙霧", "open burning", "peatland", "forest fire"]
# An article is kept only if its title or summary is about haze, fires or air quality, since a broad
# word such as "forest fire" also finds fires elsewhere in the world.
RELEVANT = re.compile(
    r"haze|jerebu|ヘイズ|煙霧|スモッグ|smog|hotspot|ホットスポット|titik panas|open burning|pembakaran terbuka|野焼き"
    r"|peat|泥炭|gambut|air pollutant index|air quality|大気|空気の質|\bAPI\b|\bAQI\b|\bPSI\b", re.I)
REGION = re.compile(
    r"malaysia|マレーシア|singapore|シンガポール|indonesia|インドネシア|sumatra|スマトラ|kalimantan|カリマンタン"
    r"|borneo|ボルネオ|sarawak|サラワク|johor|ジョホール|selangor|セランゴール|kuala lumpur|クアラルンプール|penang|ペナン"
    r"|riau|リアウ|jambi|ジャンビ|asean|ASEAN|DOE|NEA|m'sia|msia", re.I)
# Tags for the page's filter. A story can have several.
TAGS = [
    ("fire", re.compile(r"fire|hotspot|burn|blaze|火災|火事|ホットスポット|焼|kebakaran|titik panas|peat|泥炭|gambut", re.I)),
    ("health", re.compile(r"school|health|hospital|mask|asthma|respirat|学校|休校|健康|病院|マスク|喘息|呼吸|sekolah|kesihatan|pernafasan|outdoor|屋外", re.I)),
    ("policy", re.compile(r"law|act\b|bill|asean|minister|government|parliament|notice|treaty|agreement|diplomat|法|政府|大臣|議会|協定|通告|外交|首相|kerajaan|menteri|undang", re.I)),
    ("business", re.compile(r"company|companies|firm|plantation|palm|pulp|paper|sgx|bursa|hotel|tourism|airline|flight|economy|企業|会社|プランテーション|パーム|製紙|ホテル|観光|航空|便|経済|株|syarikat", re.I)),
    ("air", re.compile(r"api\b|aqi|psi|air quality|air pollutant|forecast|rain|monsoon|wind|大気|空気|予報|雨|モンスーン|風|udara|cuaca", re.I)),
]


def fetch(query: str) -> list[dict]:
    last = None
    for _ in range(2):
        try:
            r = requests.get(BASE, params={"q": query, "limit": "500"}, headers=HEADERS, timeout=(10, 20))
            r.raise_for_status()
            return r.json().get("articles", [])
        except (requests.RequestException, ValueError) as exc:
            last = exc
    raise RuntimeError(f"{query}: {type(last).__name__}: {last}")


def shorten(text: str, n: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def to_item(a: dict) -> dict | None:
    title, title_ja = (a.get("title") or "").strip(), (a.get("titleJa") or "").strip()
    summary = a.get("summaryJa") or a.get("snippet") or ""
    text = " ".join([title, title_ja, summary, a.get("snippet") or ""])
    if not a.get("link") or not (title or title_ja) or not RELEVANT.search(text):
        return None
    # Japanese outlets (週刊MTOWN, NNA) are about Malaysia already; others must name the region.
    if a.get("language") != "ja" and not REGION.search(text):
        return None
    when = a.get("isoDate") or a.get("pubDate")
    try:
        date = datetime.fromisoformat(str(when).replace("Z", "+00:00")).astimezone(TZ)
    except ValueError:
        return None
    return {
        "id": a.get("id") or a["link"],
        "date": date.isoformat(timespec="minutes"),
        "source": a.get("sourceName") or a.get("sourceId") or "",
        "link": a["link"],
        "title_ja": title_ja or title,
        "title": title if title and title != title_ja else "",
        "summary_ja": shorten(summary, SUMMARY_CHARS),
        "lang": a.get("language") or "",
        "tags": [name for name, rx in TAGS if rx.search(text)],
    }


def main() -> int:
    now = datetime.now(TZ)
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items": []}
    if "--force" not in sys.argv and old.get("generated_at"):
        age = now - datetime.fromisoformat(old["generated_at"])
        if age < MIN_AGE:
            print(f"news.json is {age} old; next fetch after {MIN_AGE}")
            return 0

    found, errors = {}, []
    for q in QUERIES:
        try:
            for a in fetch(q):
                item = to_item(a)
                if item:
                    found[item["link"]] = item
        except RuntimeError as exc:
            errors.append(str(exc))

    # Keep earlier items too (the archive search returns a limited window), then cut to the last
    # KEEP_DAYS days. Items with the same Japanese title from the same outlet are one story.
    cutoff = (now - timedelta(days=KEEP_DAYS)).isoformat()
    merged = {i["link"]: i for i in old.get("items", [])}
    merged.update(found)
    seen, items = set(), []
    for i in sorted(merged.values(), key=lambda i: i["date"], reverse=True):
        key = (i["source"], i["title_ja"])
        if i["date"] < cutoff or key in seen:
            continue
        seen.add(key)
        items.append(i)
    items = items[:MAX_ITEMS]

    status = {"fetched": len(found), "errors": errors} if found or not errors else {"fetched": 0, "errors": errors, "kept_previous": True}
    # After a failed fetch the previous time is kept, so the next hourly run tries again.
    data = {
        "generated_at": now.isoformat(timespec="seconds") if found else old.get("generated_at"),
        "checked_at": now.isoformat(timespec="seconds"),
        "source": {"name": "Campur.ai", "url": "https://campur.ai.studio/"},
        "status": status,
        "items": items if found else old.get("items", []),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"items": len(data["items"]), **status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
