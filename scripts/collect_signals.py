#!/usr/bin/env python3
"""Collect business news about Japanese companies in Malaysia for the signals page (signals/index.html).

The articles come from Campur.ai (https://campur.ai.studio), which archives the news of Malaysian and
Japanese outlets and adds Japanese titles and summaries. Its archive search is read here, server-side
(the site sends no CORS headers), the same way scripts/collect_haze_news.py reads it.

An article is kept when
  - its headline names a company on the watchlist (config/signals_watchlist.json), or
  - its summary names one and it is about a business topic (investment, plants, AI, ...), or
  - its headline is about Japan (Japan, 日系, JETRO, ...) and it is about a business topic.
Each kept article is tagged with the companies, their sectors and the topics it touches, so the page
can answer "what happened this week at the companies and topics I follow?".

Writes
  signals/data/signals.json   {"generated_at", "checked_at", "source", "status", "items": [{id, date,
                               source, link, title_ja, title, summary_ja, lang, companies, sectors,
                               topics}]}, newest first

The workflow calls this every run; it only fetches when signals.json is older than MIN_AGE. A failed
fetch keeps the previous items and records the error.

Usage:
  python scripts/collect_signals.py [--force]
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "signals" / "data" / "signals.json"
WATCHLIST = ROOT / "config" / "signals_watchlist.json"
TZ = timezone(timedelta(hours=8))
BASE = "https://campur.ai.studio/api/archive/articles"
HEADERS = {"User-Agent": "sea-signals-collector/0.1 (+https://github.com/aohaus/sea)"}
MIN_AGE = timedelta(minutes=350)
KEEP_DAYS = 120
MAX_ITEMS = 1500
SUMMARY_CHARS = 160
PAUSE = 0.4  # seconds between searches, to go easy on the archive

JAPAN = re.compile(r"\bJapan(ese)?\b|\bJepun\b|日本|日系|\bJETRO\b|\bJACTIM\b|\bJICA\b|\bJBIC\b|\bMETI\b|ジェトロ", re.I)
MALAYSIA = re.compile(
    r"malaysia|マレーシア|\bm'sia\b|kuala lumpur|クアラルンプール|\bKL\b|selangor|セランゴール|penang|ペナン|johor|ジョホール"
    r"|kedah|kulim|クリム|perak|melaka|malacca|sabah|sarawak|サバ|サラワク|negeri sembilan|pahang|putrajaya|cyberjaya"
    r"|bursa|ringgit|リンギ|\bMIDA\b|\bMITI\b|\bBNM\b|\bLHDN\b|ASEAN|\bBhd\b|\bBerhad\b|\(M\)|shah alam|bangi|pasir gudang|batu kawan|bayan lepas|ipoh|kuantan|kuching|kota kinabalu", re.I)
# Business topics. A story can have several; one that names no watchlist company needs at least one.
TOPICS = [
    ("investment", re.compile(r"invest|expan[ds]|new plant|new factory|groundbreak|capex|\bFDI\b|open(s|ed|ing) (a |its )?(new )?(plant|factory|office|hub|centre|center|store|outlet|mall)|投資|進出|新工場|増産|拡張|開設|開業|出店|pelaburan|kilang baharu", re.I)),
    ("ai_digital", re.compile(r"\bAI\b|artificial intelligence|generative|data cent(re|er)|cloud|digital|automation|robot|cyber|5G|smart factory|人工知能|生成AI|データセンター|クラウド|デジタル|自動化|ロボット|サイバー|スマート工場|pusat data|kecerdasan buatan", re.I)),
    ("supply_chain", re.compile(r"supply chain|semiconductor|chip|tariff|export|import|reshor|relocat|china ?\+ ?1|trade deal|logistic|\bports?\b|サプライチェーン|半導体|関税|輸出|輸入|移管|物流|rantaian bekalan|tarif|eksport", re.I)),
    ("people_cost", re.compile(r"minimum wage|foreign worker|labou?r shortage|levy|retrench|layoff|lay off|job cuts?|jobs (affected|lost)|workers affected|wage|salary|talent|\bEPF\b|\bTVET\b|upskill|最低賃金|外国人労働者|人手不足|解雇|賃金|人材|gaji minimum|pekerja asing", re.I)),
    ("tax_regulation", re.compile(r"e-?invoic|\bSST\b|sales and service tax|global minimum tax|tax incentive|\bLHDN\b|\bPDPA\b|data protection|regulat|complian|licen[cs]e|subsid|budget 20\d\d|電子インボイス|税|規制|補助金|優遇|予算案|cukai|peraturan|belanjawan", re.I)),
    ("deal_restructure", re.compile(r"acqui|merger|\bM&A\b|stake|joint venture|\bJV\b|partnership|\bMoU\b|divest|sell(s|ing)? (its|unit|business)|clos(e|es|ed|ing|ure)\b.{0,40}\b(plant|factory|store|outlet|operation|business)|shut ?down|withdraw|exit(s|ing)? |restructur|買収|合併|出資|合弁|提携|覚書|売却|閉鎖|撤退|再編|pengambilalihan|usaha sama", re.I)),
    ("energy_esg", re.compile(r"renewable|solar|hydrogen|ammonia|\bLNG\b|carbon|net zero|\bESG\b|sustainab|\bEV\b|electric vehicle|battery|再生可能|太陽光|水素|アンモニア|炭素|脱炭素|電気自動車|電池|tenaga boleh baharu|karbon", re.I)),
    ("results", re.compile(r"net profit|revenue|earnings|quarter(ly)? results?|\bQ[1-4]\b|dividend|profit (rise|fall|jump|drop)|純利益|売上|決算|増益|減益|配当|untung bersih|pendapatan", re.I)),
]


def load_watchlist() -> tuple[list[dict], list[str]]:
    cfg = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    companies = []
    for c in cfg["companies"]:
        flags = 0 if c.get("case_sensitive") else re.I
        en = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(a) for a in c["aliases"]) + r")(?![A-Za-z0-9])", flags)
        companies.append({**c, "rx": en})
    queries = list(cfg["queries"]) + [c["aliases"][0] for c in cfg["companies"]]
    return companies, queries


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


def to_item(a: dict, companies: list[dict]) -> dict | None:
    title, title_ja = (a.get("title") or "").strip(), (a.get("titleJa") or "").strip()
    summary = a.get("summaryJa") or a.get("snippet") or ""
    text = " ".join([title, title_ja, summary, a.get("snippet") or ""])
    if not a.get("link") or not (title or title_ja):
        return None
    headline = title + " " + title_ja

    def named(c: dict, where: str) -> bool:
        return bool(c["rx"].search(where)) or (bool(c["ja"]) and not c["ja"].isascii() and c["ja"] in where)

    hits = [c for c in companies if named(c, text)]
    topics = [name for name, rx in TOPICS if rx.search(text)]
    # A company named only in the summary (the car in a crash report, an advertiser) needs a business
    # topic; a story with no company needs Japan in its headline as well as a topic.
    in_headline = any(named(c, headline) for c in hits)
    if not in_headline and not (hits and topics) and not (JAPAN.search(headline) and topics):
        return None
    # Outlets in Japanese (週刊MTOWN, NNA) write about Malaysia already; others must name the country,
    # so that a company's news from elsewhere in the world is left out.
    if a.get("language") != "ja" and not MALAYSIA.search(text):
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
        "companies": [c["name"] for c in hits],
        "sectors": sorted({c["sector"] for c in hits}),
        "topics": topics,
    }


def main() -> int:
    now = datetime.now(TZ)
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items": []}
    if "--force" not in sys.argv and old.get("generated_at"):
        age = now - datetime.fromisoformat(old["generated_at"])
        if age < MIN_AGE:
            print(f"signals.json is {age} old; next fetch after {MIN_AGE}")
            return 0

    companies, queries = load_watchlist()
    found, errors, ok = {}, [], 0
    for q in queries:
        try:
            for a in fetch(q):
                item = to_item(a, companies)
                if item:
                    found[item["link"]] = item
            ok += 1
        except RuntimeError as exc:
            errors.append(str(exc))
            if ok == 0 and len(errors) >= 5:  # the archive is unreachable; stop instead of trying every name
                break
        time.sleep(PAUSE)

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

    fetched = bool(ok)
    status = {"searches": ok, "matched": len(found), "errors": errors[:10]}
    if not fetched:
        status["kept_previous"] = True
    # After a failed fetch the previous time is kept, so the next run tries again.
    data = {
        "generated_at": now.isoformat(timespec="seconds") if fetched else old.get("generated_at"),
        "checked_at": now.isoformat(timespec="seconds"),
        "source": {"name": "Campur.ai", "url": "https://campur.ai.studio/"},
        "status": status,
        "items": items if fetched else old.get("items", []),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"items": len(data["items"]), **status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
