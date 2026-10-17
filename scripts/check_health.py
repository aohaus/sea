#!/usr/bin/env python3
"""Check whether the data is still being refreshed, and report what needs attention.

Over decades, sources change their URLs and APIs, pages disappear and series stop.
This reads the reports the fetch scripts leave behind and the built tables, and
lists:

  error    a source that failed in this run (automatic sources), or a failed workflow run
  warning  a manually imported source whose import is older than MANUAL_MAX_DAYS
           (time to save the page/PDF again), or a series (per country or city) whose
           latest observed year is more than STALE_YEARS behind the current year
  info     such a series that is listed in basic/health_acknowledged.json (a known stop);
           shown in the report but does not keep the issue open

Writes a JSON summary and a Markdown body (for a GitHub issue). Exits 0 either
way; the workflow decides what to do with the result.

Usage:
  python scripts/check_health.py --json health.json --markdown health.md [--job-status failure]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone

from fetch_basic import BASIC_DIR, load_json

MANUAL_MAX_DAYS = 400   # a manual import older than this is due for a refresh
STALE_YEARS = 4         # latest data year older than (this year − STALE_YEARS) is reported; regional
                        # accounts (e.g. ESRI) are normally published about three years after the year


def age_days(iso: str | None, now: datetime) -> int | None:
    if not iso:
        return None
    t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (now - t).days


def load_acknowledged() -> list[dict]:
    """Series known to have stopped, with the reason (basic/health_acknowledged.json)."""
    path = BASIC_DIR / "health_acknowledged.json"
    return load_json(path).get("stopped_series", []) if path.exists() else []


def check(now: datetime, job_status: str | None) -> list[dict]:
    issues = []
    add = lambda level, source, what, detail: issues.append(  # noqa: E731
        {"level": level, "source_id": source, "what": what, "detail": detail})

    if job_status and job_status != "success":
        add("error", None, "ワークフローの実行が失敗しました", f"job status: {job_status}（ログを確認してください）")

    # Country pages (JETRO / MOFA)
    report = BASIC_DIR / "fetch_report.json"
    for r in (load_json(report)["results"] if report.exists() else []):
        extract = BASIC_DIR / r["code"] / f"{r['source_id']}.json"
        retrieved = load_json(extract).get("retrieved_at") if extract.exists() else None
        days = age_days(retrieved, now)
        if r.get("retrieval_method") == "manual_pdf":
            if days is not None and days > MANUAL_MAX_DAYS:
                add("warning", r["source_id"], f"{r['code']}：手動取り込みから{days}日経過",
                    f"{r['url']} をブラウザで PDF 保存し、scripts/import_mofa_pdf.py で取り込み直してください（前回 {retrieved[:10]}）")
        elif r.get("fetch_status") != "ok":
            add("error", r["source_id"], f"{r['code']}：取得に失敗", f"{r['url']}：{r.get('fetch_error') or r.get('error')}"
                + (f"（保存済みのデータは {retrieved[:10]} 取得）" if retrieved else ""))

    # Economic indicators (APIs)
    report = BASIC_DIR / "indicators_report.json"
    if report.exists():
        for source_id, errors in load_json(report).get("errors", {}).items():
            for e in errors:
                add("error", source_id, "指標の取得に失敗", e)

    # Major cities
    report = BASIC_DIR / "cities" / "fetch_report.json"
    if report.exists():
        for source_id, r in load_json(report).items():
            if isinstance(r, dict) and "fetch_status" in r and r["fetch_status"] != "ok":
                add("error", source_id, "都市データの取得に失敗", str(r.get("error") or r.get("fetch_error") or r["fetch_status"]))
    # Ties with Japan (JNTO / ISA / MOF): "partial" means some years failed and kept their saved values.
    report = BASIC_DIR / "ties" / "fetch_report.json"
    if report.exists():
        for source_id, r in load_json(report).items():
            if r.get("fetch_status") != "ok":
                add("error", source_id, "日本とのつながりデータの取得に失敗", str(r.get("fetch_error")))
    # Population projections (UN WPP): fetch result, and an edition that is getting old.
    report = BASIC_DIR / "projections_report.json"
    if report.exists():
        r = load_json(report)
        if r.get("fetch_status") != "ok":
            add("error", r.get("source_id"), "将来推計の取得に失敗", str(r.get("fetch_error")))
        edition_year = int(re.sub(r"\D", "", r.get("edition") or "") or 0)
        if edition_year and edition_year < now.year - 3:
            add("warning", r.get("source_id"), f"{r['edition']} より新しい版が出ていないか確認",
                "国連の世界人口推計は通常2年ごとに改訂されます。新しい版があれば basic/sources.json（un_wpp）の edition・estimates_until・url_candidates を更新してください")

    for raw in sorted((BASIC_DIR / "cities" / "raw").glob("*.json")):
        d = load_json(raw)
        if d.get("retrieval_method") == "manual_pdf":
            days = age_days(d.get("retrieved_at"), now)
            if days is not None and days > MANUAL_MAX_DAYS:
                add("warning", d.get("source_id"), f"手動取り込みから{days}日経過",
                    f"{d.get('publication') or raw.name}：新しい版を取り込んでください（前回 {d['retrieved_at'][:10]}）")

    # Series that stopped: the latest observed year per source, indicator and place. Years after the
    # current one are projections (e.g. UN city population to 2050) and do not count as fresh data.
    acknowledged = {(a["source_id"], a["indicator_id"], a["place"]): a for a in load_acknowledged()}
    for table, place_key in (("observations", "country_code"), ("city_observations", "city_id")):
        path = BASIC_DIR / "data" / f"{table}.json"
        if not path.exists():
            continue
        latest: dict[tuple, int] = {}
        for r in load_json(path):
            year = int(r["year"])
            if year > now.year:
                continue
            k = (r["source_id"], r["indicator_id"], r[place_key])
            latest[k] = max(latest.get(k, 0), year)
        for (source_id, ind, place), year in sorted(latest.items()):
            if year >= now.year - STALE_YEARS:
                continue
            ack = acknowledged.get((source_id, ind, place))
            if ack:
                add("info", source_id, f"{place} {ind}：最新年が{year}年（確認済み）", ack.get("reason", ""))
            else:
                add("warning", source_id, f"{place} {ind}：最新年が{year}年",
                    f"{now.year - STALE_YEARS}年より古いデータしかありません。出所の更新停止や URL の変更がないか確認し、"
                    "意図したものなら basic/health_acknowledged.json に理由を記録してください")
    return issues


def markdown(issues: list[dict], now: datetime) -> str:
    level_ja = {"error": "エラー", "warning": "要確認", "info": "確認済み"}
    lines = [f"データの自動チェック（{now.date().isoformat()}）", ""]
    if not any(i["level"] != "info" for i in issues):
        lines.append("問題は見つかりませんでした。")
        if issues:
            lines += ["", "確認済みの停止系列：" + "、".join(i["what"] for i in issues)]
        return "\n".join(lines) + "\n"
    lines += ["| 区分 | 出所 | 内容 | 詳細 |", "|---|---|---|---|"]
    order = {"error": 0, "warning": 1, "info": 2}
    for i in sorted(issues, key=lambda i: (order[i["level"]], i["source_id"] or "")):
        lines.append(f"| {level_ja[i['level']]} | {i['source_id'] or '—'} | {i['what']} | {i['detail'].replace('|', '／')} |")
    lines += ["", "このチェックは毎月の自動取得（Fetch basic country data）のたびに実行され、問題がなくなるとこの Issue は自動で閉じます。"]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", help="write the summary here")
    parser.add_argument("--markdown", help="write a Markdown report here")
    parser.add_argument("--job-status", help="status of the workflow job so far (success / failure / cancelled)")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    issues = check(now, args.job_status)
    summary = {"checked_at": now.isoformat(timespec="seconds"), "ok": not any(i["level"] != "info" for i in issues),
               "errors": sum(i["level"] == "error" for i in issues),
               "warnings": sum(i["level"] == "warning" for i in issues), "issues": issues}
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
    md = markdown(issues, now)
    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as fh:
            fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
