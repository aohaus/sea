#!/usr/bin/env python3
"""Consolidate basic/ into one dataset file and validate it against reference figures.

Reads countries.json, schema/fields.json, sources.json, every <code>/profile.json
and <code>/indicators.json, and writes:
  basic/data/dataset.json
      everything the viewer needs, with full provenance on every value.
  basic/reference/validation_report.json
      for each figure in basic/reference/*.json, the value computed from our data
      (sum over the figure's scope, or a ratio of two sums), the difference in %,
      and a status: match (<=2%), close (<=10%), differs (>10%), no_data.

No network access. Usage:
  python scripts/build_dataset.py
"""

from __future__ import annotations

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


def main() -> int:
    dataset = build()
    report = validate(dataset)
    dataset["validation"] = report
    dataset["references"] = {
        load_json(p)["reference_id"]: {k: v for k, v in load_json(p).items() if k != "figures"}
        for p in sorted((BASIC_DIR / "reference").glob("*.json")) if p.name != "validation_report.json"
    }
    write_json(BASIC_DIR / "data" / "dataset.json", dataset)
    write_json(BASIC_DIR / "reference" / "validation_report.json", report)
    for r in report["results"]:
        ours = f"{r['our_value']:,.0f}" if r["our_value"] is not None else "-"
        diff = f"{r['diff_pct']:+.1f}%" if r["diff_pct"] is not None else ""
        print(f"{r['figure_id']:<28} ref={r['reference_value']:>16,.0f} ours={ours:>16} {diff:>8} "
              f"{r['status']:<8} {','.join(r['our_sources'])} vs {r['reference_cited_source']}"
              + (f" missing={r['missing']}" if r["missing"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
