#!/usr/bin/env python3
"""Freeze the current data as a yearly version ("2026年版") under basic/archive/<year>/.

The site's data in basic/data/ is rebuilt on every run and overwritten. To keep
what was known in each year (values are revised later, sources disappear), this
script copies the export tables into basic/archive/<year>/ once a year and never
touches a version again:

  basic/archive/<year>/<table>.json.gz   the table as it was (gzip of the JSON in basic/data/)
  basic/archive/<year>/manifest.json     when and from which commit it was frozen, row counts,
                                         SHA-256 of each table, latest retrieval per source
  basic/archive/<year>/revisions.json.gz values that differ from the previous version
                                         (changed / added / removed), with old and new values
  basic/archive/index.json               list of versions with their revision summary

Values are compared by key: observations (country, indicator, source, year),
city observations (city, indicator, source, year, url) and profiles (country,
field, source). A change smaller than 1e-9 (relative) is ignored.

Usage:
  python scripts/snapshot.py                 # freeze the current year (fails if it exists)
  python scripts/snapshot.py --if-missing    # freeze only if this year has no version yet
  python scripts/snapshot.py --year 2026     # freeze as a given year
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from fetch_basic import BASIC_DIR, load_json, write_json

SCHEMA_VERSION = 1
ARCHIVE_DIR = BASIC_DIR / "archive"
TABLES = ["observations", "profiles", "city_observations", "city_list", "currencies", "sources", "validation"]
# Tables whose values are compared between versions, and the columns that identify a value.
KEYS = {
    "observations": ("country_code", "indicator_id", "source_id", "year"),
    "city_observations": ("city_id", "indicator_id", "source_id", "year", "url"),
    "profiles": ("country_code", "field_id", "source_id"),
}
VALUE = {"observations": "value", "city_observations": "value", "profiles": "value_text"}


def gz_bytes(data: bytes) -> bytes:
    """gzip with a fixed timestamp, so the same table always gives the same file."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as fh:
        fh.write(data)
    return buf.getvalue()


def read_gz_json(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def git_commit() -> str | None:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def differs(old, new) -> bool:
    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
        return abs(old - new) > 1e-9 * max(1.0, abs(old), abs(new))
    return old != new


def revisions(prev_dir, tables: dict) -> tuple[list[dict], dict]:
    """Rows whose value differs from the previous version, and counts per table."""
    rows, summary = [], {}
    for table, key_cols in KEYS.items():
        path = prev_dir / f"{table}.json.gz"
        if not path.exists() or table not in tables:
            continue
        val = VALUE[table]
        old = {tuple(r.get(k) for k in key_cols): r for r in read_gz_json(path)}
        new = {tuple(r.get(k) for k in key_cols): r for r in tables[table]}
        counts = {"changed": 0, "added": 0, "removed": 0}
        for key in sorted(set(old) | set(new), key=lambda k: tuple("" if v is None else str(v) for v in k)):
            o, n = old.get(key), new.get(key)
            if o is None:
                kind = "added"
            elif n is None:
                kind = "removed"
            elif differs(o.get(val), n.get(val)):
                kind = "changed"
            else:
                continue
            counts[kind] += 1
            entry = {"table": table, "kind": kind, **dict(zip(key_cols, key)),
                     "old": o.get(val) if o else None, "new": n.get(val) if n else None}
            if kind == "changed" and isinstance(entry["old"], (int, float)) and isinstance(entry["new"], (int, float)) and entry["old"]:
                entry["diff_pct"] = round((entry["new"] - entry["old"]) / abs(entry["old"]) * 100, 4)
            rows.append(entry)
        summary[table] = counts
    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--year", type=int, default=datetime.now(timezone.utc).year)
    parser.add_argument("--if-missing", action="store_true", help="do nothing if the version already exists")
    args = parser.parse_args()

    out = ARCHIVE_DIR / str(args.year)
    if out.exists():
        if args.if_missing:
            print(f"version {args.year} already exists; nothing to do")
            return 0
        print(f"version {args.year} already exists; versions are never overwritten", file=sys.stderr)
        return 1

    index_path = ARCHIVE_DIR / "index.json"
    index = load_json(index_path) if index_path.exists() else {"schema_version": SCHEMA_VERSION, "versions": []}
    earlier = sorted((v["version"] for v in index["versions"] if v["version"] < args.year), reverse=True)
    prev_dir = ARCHIVE_DIR / str(earlier[0]) if earlier else None

    tables, files = {}, {}
    for name in TABLES:
        src = BASIC_DIR / "data" / f"{name}.json"
        if not src.exists():
            print(f"skip {name}: {src} not found")
            continue
        raw = src.read_bytes()
        tables[name] = json.loads(raw)
        files[name] = {"file": f"{name}.json.gz", "rows": len(tables[name]), "sha256": hashlib.sha256(raw).hexdigest()}

    latest_by_source: dict[str, str] = {}
    for name in ("observations", "profiles", "city_observations"):
        for r in tables.get(name, []):
            sid, t = r.get("source_id"), r.get("retrieved_at")
            if sid and t and t > latest_by_source.get(sid, ""):
                latest_by_source[sid] = t

    rev_rows, rev_summary = revisions(prev_dir, tables) if prev_dir else ([], {})

    out.mkdir(parents=True)
    for name, meta in files.items():
        (out / meta["file"]).write_bytes(gz_bytes((BASIC_DIR / "data" / f"{name}.json").read_bytes()))
    if prev_dir:
        (out / "revisions.json.gz").write_bytes(gz_bytes(json.dumps(rev_rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "schema_version": SCHEMA_VERSION, "version": args.year, "created_at": created, "git_commit": git_commit(),
        "previous_version": earlier[0] if earlier else None, "tables": files,
        "latest_retrieval_by_source": dict(sorted(latest_by_source.items())),
        "revisions": {"file": "revisions.json.gz" if prev_dir else None, "summary": rev_summary},
    }
    write_json(out / "manifest.json", manifest)

    index["schema_version"] = SCHEMA_VERSION
    index["versions"] = sorted(
        [v for v in index["versions"] if v["version"] != args.year]
        + [{"version": args.year, "created_at": created, "path": f"{args.year}/",
            "rows": {k: v["rows"] for k, v in files.items()},
            "previous_version": manifest["previous_version"], "revisions": rev_summary}],
        key=lambda v: v["version"], reverse=True)
    write_json(index_path, index)
    print(f"froze version {args.year}: " + ", ".join(f"{k} {v['rows']}" for k, v in files.items()))
    if prev_dir:
        print(f"revisions vs {earlier[0]}: {rev_summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
