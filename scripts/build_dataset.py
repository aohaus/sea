#!/usr/bin/env python3
"""Consolidate basic/ into one dataset file and validate it against reference figures.

Reads countries.json, schema/fields.json, sources.json, every <code>/profile.json
and <code>/indicators.json, and writes:
  basic/data/dataset.json
      everything the viewer needs, with full provenance on every value.
  basic/data/observations.{csv,json}, profiles.{csv,json}, sources.{csv,json}
      flat tables for export and the dashboard: one row per value, each row
      carrying its publisher, URL, retrieval date and license, and its cross-checks
      (CSV in UTF-8 with BOM so it opens in Excel).
  Cross-checks are attached to every value as part of its provenance:
      cross_source  the same country/indicator/year from another source here
      reference     a reference figure for that country (e.g. ASEAN-Japan Centre, IMF-based)
      aggregate     a reference total (e.g. ASEAN 10) this value was summed into
  basic/reference/validation_report.json
      for each figure in basic/reference/*.json, the value computed from our data
      (sum over the figure's scope, or a ratio of two sums), the difference in %,
      and a status: match (<=2%), close (<=10%), differs (>10%), no_data.

No network access. Usage:
  python scripts/build_dataset.py
"""

from __future__ import annotations

import csv
import json
import sys

from fetch_basic import BASIC_DIR, load_json, write_json

# Which series to use when computing a figure from our data, in order of preference.
SERIES_PREFERENCE = ["worldbank_wdi", "imf_weo", "jetro_basic", "mofa_basic"]


def build() -> dict:
    master = load_json(BASIC_DIR / "countries.json")
    fields = load_json(BASIC_DIR / "schema" / "fields.json")["fields"]
    sources = load_json(BASIC_DIR / "sources.json")["sources"]
    places = ([{**c, "group": "asean"} for c in master["countries"]]
              + [{**c, "group": "benchmark"} for c in master.get("benchmarks", [])])

    dataset = {
        "countries": [{k: c.get(k) for k in ("code", "iso3", "name_ja", "name_en", "group")} for c in places],
        "fields": [{k: f.get(k) for k in ("id", "phase", "type", "unit", "label_ja", "label_en")} for f in fields],
        "sources": {s["id"]: {k: v for k, v in s.items() if k != "id"} for s in sources},
        "profiles": {},
        "indicators": {},
    }
    for c in places:
        folder = BASIC_DIR / c["code"]
        if (folder / "profile.json").exists():
            profile = load_json(folder / "profile.json")
            dataset["profiles"][c["code"]] = {k: v["values"] for k, v in profile["fields"].items() if v["values"]}
        if (folder / "indicators.json").exists():
            ind = load_json(folder / "indicators.json")
            dataset["indicators"][c["code"]] = {k: v["series"] for k, v in ind["indicators"].items() if v["series"]}
    return dataset


def our_value(dataset: dict, code: str, field: str, year: int | None) -> tuple[float | None, str | None]:
    """A single country's value for field/year from the preferred series (or the profile)."""
    if year is None:
        values = dataset["profiles"].get(code, {}).get(field, [])
        return (values[0]["value"], values[0]["source_id"]) if values else (None, None)
    series = dataset["indicators"].get(code, {}).get(field, [])
    for source_id in SERIES_PREFERENCE:
        for s in series:
            if s["source_id"] != source_id:
                continue
            for o in s["observations"]:
                if o["year"] == year:
                    return o["value"], source_id
    return None, None


def compute(dataset: dict, fig: dict) -> tuple[float | None, list[str], list[str]]:
    """Value for a reference figure: sum over scope, or ratio of two sums."""
    def total(field: str):
        acc, used, missing = 0.0, set(), []
        for code in fig["scope"]:
            v, src = our_value(dataset, code, field, fig["year"])
            if v is None:
                missing.append(code)
            else:
                acc += v
                used.add(src)
        return acc, used, missing

    agg = fig.get("aggregate")
    if agg and agg.startswith("ratio:"):
        num, den = agg[len("ratio:"):].split("/")
        a, used_a, miss_a = total(num)
        b, used_b, miss_b = total(den)
        missing = sorted(set(miss_a + miss_b))
        return (a / b if b and not missing else None), sorted(used_a | used_b), missing
    if len(fig["scope"]) == 1:
        v, src = our_value(dataset, fig["scope"][0], fig["field"], fig["year"])
        return v, [src] if src else [], [] if v is not None else fig["scope"]
    a, used, missing = total(fig["field"])
    return (a if not missing else None), sorted(used), missing


STATUS_RANK = {"match": 0, "close": 1, "differs": 2}
STATUS_JA = {"match": "一致", "close": "近い", "differs": "差あり", "no_data": "データなし"}


def status_of(diff: float) -> str:
    return "match" if abs(diff) <= 2 else "close" if abs(diff) <= 10 else "differs"


def compare(value, against, unit: str | None = None) -> tuple[float | None, str | None, str]:
    """Difference and status. Rates (unit %) compare in percentage points:
    match <= 0.2pt, close <= 1pt; everything else in % of the other value."""
    if value is None or against is None or (unit != "%" and not against):
        return None, None, "pct"
    if unit == "%":
        pt = value - against
        return round(pt, 2), ("match" if abs(pt) <= 0.2 else "close" if abs(pt) <= 1 else "differs"), "pt"
    diff = (value - against) / against * 100
    return round(diff, 2), status_of(diff), "pct"


def attach_checks(dataset: dict) -> None:
    """Add a `checks` list to every observation and profile value (see module docstring)."""
    sources = dataset["sources"]
    fields = {f["id"]: f for f in dataset["fields"]}
    refs = {}
    for path in sorted((BASIC_DIR / "reference").glob("*.json")):
        if path.name != "validation_report.json":
            ref = load_json(path)
            refs[ref["reference_id"]] = ref
    results = {(r["reference_id"], r["figure_id"]): r for r in dataset["validation"]["results"]}

    def ref_label(ref: dict, fig: dict) -> str:
        return f"{ref['publisher_ja'].split('（')[0]}「{ref['title_ja']}」（{fig['cited_source']}）"

    def scope_label(scope: list[str]) -> str:
        n = len(scope)
        return "ASEAN 全11か国" if n == 11 else f"ASEAN {n}か国" if n > 1 else scope[0]

    # Observations: cross-source and single-country references.
    for code, by_field in dataset["indicators"].items():
        for field_id, series_list in by_field.items():
            index = {(s["source_id"], o["year"]): o["value"] for s in series_list for o in s["observations"]}
            for s in series_list:
                for o in s["observations"]:
                    checks = []
                    for other in series_list:
                        if other["source_id"] == s["source_id"]:
                            continue
                        against = index.get((other["source_id"], o["year"]))
                        diff, status, kind = compare(o["value"], against, fields[field_id]["unit"])
                        if status:
                            checks.append({"kind": "cross_source", "against": sources[other["source_id"]]["publisher_ja"],
                                           "against_source_id": other["source_id"], "against_value": against,
                                           f"diff_{kind}": diff, "status": status})
                    o["checks"] = checks
    for ref_id, ref in refs.items():
        for fig in ref["figures"]:
            res = results.get((ref_id, fig["id"]))
            # A reference for one country: compare every source's value for that year.
            if len(fig["scope"]) == 1 and fig["year"] is not None:
                for s in dataset["indicators"].get(fig["scope"][0], {}).get(fig["field"], []):
                    for o in s["observations"]:
                        if o["year"] == fig["year"]:
                            diff, status, kind = compare(o["value"], fig["value"], fields[fig["field"]]["unit"])
                            o["checks"].append({"kind": "reference", "against": ref_label(ref, fig),
                                                "reference_id": ref_id, "figure_id": fig["id"],
                                                "against_value": fig["value"], f"diff_{kind}": diff, "status": status})
                continue
            # A reference total: note it on every value that went into our total.
            if not res or res["our_value"] is None:
                continue
            what = f"{scope_label(fig['scope'])}の{fields[fig['field']]['label_ja']}" + (f"（{fig['year']}年）" if fig["year"] else "")
            check = {"kind": "aggregate", "subject": what, "against": ref_label(ref, fig),
                     "reference_id": ref_id, "figure_id": fig["id"], "against_value": fig["value"],
                     "our_total": res["our_value"], "diff_pct": res["diff_pct"], "status": res["status"]}
            for code in fig["scope"]:
                if fig["year"] is None:
                    for v in dataset["profiles"].get(code, {}).get(fig["field"], []):
                        if v["source_id"] in res["our_sources"]:
                            v.setdefault("checks", []).append(check)
                    continue
                inputs = fig.get("aggregate", "").removeprefix("ratio:").split("/") if fig.get("aggregate") else [fig["field"]]
                for field_id in inputs:
                    for s in dataset["indicators"].get(code, {}).get(field_id, []):
                        if s["source_id"] in res["our_sources"]:
                            for o in s["observations"]:
                                if o["year"] == fig["year"]:
                                    o["checks"].append(check)
    for by_field in dataset["profiles"].values():
        for values in by_field.values():
            for v in values:
                v.setdefault("checks", [])


def check_text(checks: list[dict]) -> tuple[str | None, str | None]:
    """'JETRO: 12,098（差 -5.9%・近い）; ...' and the worst status, for the flat tables."""
    if not checks:
        return None, None
    parts = []
    for c in checks:
        st = STATUS_JA.get(c["status"], c["status"])
        if c.get("diff_pt") is not None:
            diff = f"{c['diff_pt']:+.1f}pt"
        elif c.get("diff_pct") is not None:
            diff = f"{c['diff_pct']:+.1f}%"
        else:
            diff = "—"
        if c["kind"] == "aggregate":
            parts.append(f"{c['subject']}を照合 {c['against']}: {c['against_value']:,.0f}／このデータ: {c['our_total']:,.0f}（差 {diff}・{st}）")
        else:
            parts.append(f"{c['against']}: {c['against_value']:,.6g}（差 {diff}・{st}）")
    worst = max((c["status"] for c in checks if c["status"] in STATUS_RANK), key=STATUS_RANK.get, default=None)
    return "; ".join(parts), worst


def validate(dataset: dict) -> dict:
    results = []
    for path in sorted((BASIC_DIR / "reference").glob("*.json")):
        if path.name == "validation_report.json":
            continue
        ref = load_json(path)
        for fig in ref["figures"]:
            ours, used, missing = compute(dataset, fig)
            if ours is None:
                status, diff = "no_data", None
            else:
                diff = (ours - fig["value"]) / fig["value"] * 100
                status = "match" if abs(diff) <= 2 else "close" if abs(diff) <= 10 else "differs"
            results.append({
                "reference_id": ref["reference_id"], "figure_id": fig["id"], "field": fig["field"],
                "year": fig["year"], "scope": fig["scope"],
                "reference_value": fig["value"], "reference_text": fig["value_text"],
                "reference_cited_source": fig["cited_source"],
                "our_value": round(ours, 2) if ours is not None else None,
                "our_sources": used, "missing": missing,
                "diff_pct": round(diff, 2) if diff is not None else None, "status": status,
            })
    return {"thresholds": {"match": "<=2%", "close": "<=10%", "differs": ">10%"}, "results": results}


def flatten(dataset: dict) -> dict[str, list[dict]]:
    countries = {c["code"]: c for c in dataset["countries"]}
    fields = {f["id"]: f for f in dataset["fields"]}
    sources = dataset["sources"]

    def place(code: str) -> dict:
        c = countries[code]
        return {"country_code": code, "country_ja": c["name_ja"], "country_en": c["name_en"], "group": c["group"]}

    def source_cols(source_id: str) -> dict:
        s = sources.get(source_id, {})
        return {"source_id": source_id, "source_publisher_ja": s.get("publisher_ja"),
                "source_publisher_en": s.get("publisher_en"), "source_title_ja": s.get("title_ja"),
                "license": s.get("license")}

    observations = []
    for code, by_field in dataset["indicators"].items():
        for field_id, series_list in by_field.items():
            f = fields[field_id]
            for series in series_list:
                for o in series["observations"]:
                    observations.append({
                        **place(code), "indicator_id": field_id, "indicator_ja": f["label_ja"],
                        "indicator_en": f["label_en"], "unit": f["unit"], "year": o["year"], "value": o["value"],
                        "note": o.get("note"), **source_cols(series["source_id"]),
                        "indicator_code": series.get("indicator_code"),
                        "original_source": o.get("original_source"), "url": series["url"],
                        "retrieved_at": series["retrieved_at"],
                        "source_last_updated": series.get("source_last_updated") or series.get("page_last_updated"),
                        "retrieval_method": series.get("retrieval_method", "auto"),
                        **dict(zip(("cross_check", "cross_check_status"), check_text(o.get("checks", [])))),
                    })
    profiles = []
    for code, by_field in dataset["profiles"].items():
        for field_id, values in by_field.items():
            f = fields[field_id]
            for v in values:
                profiles.append({
                    **place(code), "field_id": field_id, "field_ja": f["label_ja"], "field_en": f["label_en"],
                    "unit": f["unit"], "value": v["value"], "value_text": v["value_text"], "as_of": v["as_of"],
                    "note": v.get("note"), **source_cols(v["source_id"]),
                    "original_source": v["original_source"], "url": v["url"], "retrieved_at": v["retrieved_at"],
                    "page_last_updated": v.get("page_last_updated"),
                    "retrieval_method": v.get("retrieval_method", "auto"),
                    **dict(zip(("cross_check", "cross_check_status"), check_text(v.get("checks", [])))),
                })
    source_rows = [{"source_id": k, **{c: v.get(c) for c in (
        "publisher_ja", "publisher_en", "title_ja", "title_en", "type", "license", "terms_url",
        "citation_format", "auto_fetch", "storage_policy")}} for k, v in sources.items()]
    return {"observations": observations, "profiles": profiles, "sources": source_rows}


def write_table(name: str, rows: list[dict]) -> None:
    out = BASIC_DIR / "data"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    columns = list(rows[0]) if rows else []
    with open(out / f"{name}.csv", "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    dataset = build()
    report = validate(dataset)
    dataset["validation"] = report
    attach_checks(dataset)
    dataset["references"] = {
        load_json(p)["reference_id"]: {k: v for k, v in load_json(p).items() if k != "figures"}
        for p in sorted((BASIC_DIR / "reference").glob("*.json")) if p.name != "validation_report.json"
    }
    write_json(BASIC_DIR / "data" / "dataset.json", dataset)
    write_json(BASIC_DIR / "reference" / "validation_report.json", report)
    tables = flatten(dataset)
    tables["validation"] = [{**r, "scope": ",".join(r["scope"]), "our_sources": ",".join(r["our_sources"]),
                             "missing": ",".join(r["missing"])} for r in report["results"]]
    for name, rows in tables.items():
        write_table(name, rows)
    for r in report["results"]:
        ours = f"{r['our_value']:,.0f}" if r["our_value"] is not None else "-"
        diff = f"{r['diff_pct']:+.1f}%" if r["diff_pct"] is not None else ""
        print(f"{r['figure_id']:<28} ref={r['reference_value']:>16,.0f} ours={ours:>16} {diff:>8} "
              f"{r['status']:<8} {','.join(r['our_sources'])} vs {r['reference_cited_source']}"
              + (f" missing={r['missing']}" if r["missing"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
