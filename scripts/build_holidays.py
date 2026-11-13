#!/usr/bin/env python3
"""Build the public-holiday table for Japan and Malaysia, this year through END_YEAR.

Sources
  Japan     Cabinet Office "国民の祝日" CSV (official, but it only reaches next year). Later years are
            computed from the holiday law by the `holidays` library (vacanza/holidays); the equinox
            days there are astronomical predictions until the government announces them each February.
  Malaysia  No official machine-readable source exists: the Prime Minister's Department publishes the
            list for the coming year as a PDF. Dates come from the `holidays` library: nationwide
            holidays plus those of the Federal Territory of Kuala Lumpur. Holidays that follow the
            Islamic, Chinese or Hindu calendars can move by a day; the library marks dates beyond its
            confirmed tables as estimated.

Writes
  basic/holidays/holidays.json  {"generated_at", "through", "sources", "countries": {"JP": [...],
                                 "MY": [...]}}; each day is {date, name, status[, scope]}.
                                 status: official | computed | estimated.  scope (MY): national | KUL.

A workflow runs this once a month, so each February's official Japanese list and each library update
replace the computed dates. If the Cabinet Office file cannot be read, the computed dates are kept and
the failure is recorded under "sources".

Usage:
  python scripts/build_holidays.py
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import holidays
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "basic" / "holidays" / "holidays.json"
END_YEAR = 2032
CAO_CSV = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"
HEADERS = {"User-Agent": "sea-holidays/0.1 (+https://github.com/aohaus/sea)"}
KL = "14"  # Wilayah Persekutuan Kuala Lumpur

MY_JA = {
    "New Year's Day": "元日", "Thaipusam": "タイプーサム", "Federal Territory Day": "連邦直轄領の日",
    "Chinese New Year": "春節（旧正月）", "Nuzul Al-Quran Day": "ヌズル・コーラン",
    "Eid al-Fitr": "ハリラヤ・プアサ（断食明け）", "Labor Day": "メーデー", "Eid al-Adha": "ハリラヤ・ハジ（犠牲祭）",
    "Vesak Day": "ウェサック・デー", "Islamic New Year": "イスラム暦新年", "Birthday of HM Yang di-Pertuan Agong": "国王誕生日",
    "Prophet Muhammad's Birthday": "ムハンマド生誕祭", "National Day": "独立記念日", "Malaysia Day": "マレーシア・デー",
    "Diwali": "ディパバリ", "Christmas Day": "クリスマス",
}


def japan_official() -> tuple[dict[str, str], str | None]:
    try:
        r = requests.get(CAO_CSV, headers=HEADERS, timeout=(10, 30))
        r.raise_for_status()
        rows = list(csv.reader(io.StringIO(r.content.decode("cp932"))))
    except (requests.RequestException, UnicodeDecodeError) as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    out = {}
    for row in rows[1:]:
        if len(row) >= 2 and re.fullmatch(r"\d{4}/\d{1,2}/\d{1,2}", row[0].strip()):
            y, m, d = map(int, row[0].strip().split("/"))
            out[date(y, m, d).isoformat()] = row[1].strip()
    return (out, None) if out else ({}, "no rows parsed")


def my_name(raw: str) -> tuple[str, bool]:
    """One library name ("Eid al-Fitr (Second Day) (estimated)") -> Japanese name, estimated?"""
    notes = re.findall(r"\(([^)]*)\)", raw)
    base = re.sub(r"\s*\([^)]*\)", "", raw).strip()
    flags = {w.strip().lower() for n in notes for w in n.split(",")}
    name = MY_JA.get(base, base)
    if "second day" in flags:
        name += " 2日目"
    if "observed" in flags or "in lieu" in flags:
        name += "（振替）"
    return f"{name} / {base}", "estimated" in flags


def main() -> int:
    now = datetime.now(timezone(timedelta(hours=8)))
    years = list(range(now.year, END_YEAR + 1))

    official, error = japan_official()
    official_years = {d[:4] for d in official}
    jp = {d: {"date": d, "name": n, "status": "official"} for d, n in official.items() if int(d[:4]) in years}
    for d, n in holidays.Japan(years=years, language="ja").items():
        if str(d.year) not in official_years:  # a year in the official file is taken from it whole
            jp[d.isoformat()] = {"date": d.isoformat(), "name": n, "status": "computed"}

    national = holidays.Malaysia(years=years, language="en_US")
    my = []
    for d, raw in sorted(holidays.Malaysia(years=years, subdiv=KL, language="en_US").items()):
        scope = "national" if d in national else "KUL"
        for part in raw.split("; "):
            name, estimated = my_name(part)
            my.append({"date": d.isoformat(), "name": name, "status": "estimated" if estimated else "computed", "scope": scope})

    data = {
        "generated_at": now.isoformat(timespec="seconds"),
        "through": END_YEAR,
        "sources": {
            "JP": {"official": CAO_CSV, "official_years": sorted(official_years), "official_error": error,
                   "computed": f"holidays {holidays.__version__} (https://github.com/vacanza/holidays)"},
            "MY": {"computed": f"holidays {holidays.__version__} (https://github.com/vacanza/holidays)",
                   "note": "Nationwide plus Kuala Lumpur. Check the yearly list of the Prime Minister's Department (Bahagian Kabinet, Perlembagaan dan Perhubungan Antara Kerajaan) for the gazetted dates."},
        },
        "countries": {"JP": sorted(jp.values(), key=lambda x: x["date"]), "MY": my},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"JP": len(data["countries"]["JP"]), "MY": len(my), "official_years": sorted(official_years), "official_error": error}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
