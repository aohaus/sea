#!/usr/bin/env python3
"""Check whether the data is still being refreshed, and report what needs attention.

Over decades, sources change their URLs and APIs, pages disappear and series stop.
This reads the reports the fetch scripts leave behind and the built tables, and
lists:

  error    a source that failed in this run (automatic sources), or a failed workflow run
  warning  a manually imported source whose import is older than MANUAL_MAX_DAYS
           (time to save the page/PDF again), or a series whose latest year is more
           than STALE_YEARS behind the current year (the source may have stopped)

Writes a JSON summary and a Markdown body (for a GitHub issue). Exits 0 either
way; the workflow decides what to do with the result.

Usage:
  python scripts/check_health.py --json health.json --markdown health.md [--job-status failure]
"""

from __future__ import annotations

import argparse
import json
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
    for raw in sorted((BASIC_DIR / "cities" / "raw").glob("*.json")):
        d = load_json(raw)
        if d.get("retrieval_method") == "manual_pdf":
            days = age_days(d.get("retrieved_at"), now)
            if days is not None and days > MANUAL_MAX_DAYS:
                add("warning", d.get("source_id"), f"手動取り込みから{days}日経過",
                    f"{d.get('publication') or raw.name}：新しい版を取り込んでください（前回 {d['retrieved_at'][:10]}）")

    # Series that stopped: latest year per source and indicator
    for table, ind_key in (("observations", "indicator_id"), ("city_observations", "indicator_id")):
        path = BASIC_DIR / "data" / f"{table}.json"
        if not path.exists():
            continue
        latest: dict[tuple, int] = {}
        for r in load_json(path):
            k = (r["source_id"], r[ind_key])
            latest[k] = max(latest.get(k, 0), int(r["year"]))
        for (source_id, ind), year in sorted(latest.items()):
            if year < now.year - STALE_YEARS:
                add("warning", source_id, f"{ind}：最新年が{year}年", f"{now.year - STALE_YEARS}年より古いデータしかありません。出所の更新停止や URL の変更がないか確認してください")
    return issues


def markdown(issues: list[dict], now: datetime) -> str:
    level_ja = {"error": "エラー", "warning": "要確認"}
    lines = [f"データの自動チェック（{now.date().isoformat()}）", ""]
    if not issues:
        return "\n".join(lines + ["問題は見つかりませんでした。"]) + "\n"
    lines += ["| 区分 | 出所 | 内容 | 詳細 |", "|---|---|---|---|"]
    for i in sorted(issues, key=lambda i: (i["level"] != "error", i["source_id"] or "")):
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
    summary = {"checked_at": now.isoformat(timespec="seconds"), "ok": not issues,
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
