#!/usr/bin/env python3
"""Collect current air-quality readings every hour, into 2-hour slots, for the Haze Monitor (haze/).

Sources that a browser cannot fetch directly are read here, server-side:
  doe_api              Malaysia DOE (APIMS / EQMS) — the public map service lists every station's
                       latest Air Pollutant Index; each Haze Monitor station takes the nearest DOE
                       station (within MAX_KM)

WAQI / AQICN is not collected: its terms of use do not allow its API data to be redistributed as
cached or archived data. The page shows WAQI's current value only to a viewer who enters their
own token. Each run also removes WAQI values stored by earlier versions (waqi_* series).

Readings are put in two-hour slots (UTC+8, even hours) and kept in
  haze/data/archive/YYYY-MM.json   {"slots": {"2026-10-22T14": {"<station>": {"<series>": value}}},
                                    "meta": {"<station>": {"<series>": "source station name"}}}
— a permanent record, one file per month. From the archive it writes
  haze/data/series.json            the last 14 days (168 slots) in the layout haze/app.js reads
  haze/data/collect_report.json    what this run fetched and any errors

A failed source is reported and the run still succeeds, so the other source is not lost.

Usage:
  python scripts/collect_haze.py
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "haze" / "data"
TZ = timezone(timedelta(hours=8))
SLOTS_SHOWN = 168
MAX_KM = 20
SAMPLES: dict[str, str] = {}  # one raw reading time per source, written to the report
HEADERS = {"User-Agent": "sea-haze-collector/0.1 (+https://github.com/aohaus/sea)"}
DOE_URL = ("https://eqms.doe.gov.my/api3/publicmapproxy/PUBLIC_DISPLAY/CAQM_MCAQM_Current_Reading/MapServer/0/query"
           "?where=1%3D1&outFields=*&f=json")

# Same ids and coordinates as haze/app.js.
STATIONS = {
    "cheras": (3.1060, 101.7180, "my"), "batumuda": (3.2125, 101.6820, "my"),
    "minden": (5.3580, 100.2950, "my"), "sperai": (5.3980, 100.4050, "my"),
    "larkin": (1.4970, 103.7430, "my"), "pgudang": (1.4700, 103.9030, "my"),
    "sgcentral": (1.35735, 103.82, "sg"),
}


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    (la1, lo1), (la2, lo2) = map(lambda p: (math.radians(p[0]), math.radians(p[1])), (a, b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def slot_of(t: datetime) -> str:
    """The two-hour slot (UTC+8, even hour) a reading time falls in, e.g. '2026-10-22T14'."""
    t = t.astimezone(TZ)
    return t.replace(hour=t.hour - t.hour % 2, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H")


def get_json(url: str) -> dict:
    last = None
    for _ in range(2):
        try:
            r = requests.get(url, headers=HEADERS, timeout=(15, 45))
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            last = exc
    raise RuntimeError(f"{type(last).__name__}: {last}")


def fetch_doe() -> tuple[list[tuple], list[str]]:
    """(slot, station, 'doe_api', value, source name) for each Malaysian station."""
    d = get_json(DOE_URL)
    feats = [f["attributes"] for f in d.get("features", [])]
    if not feats:
        raise RuntimeError("no features in the DOE response")
    out, notes = [], []
    for sid, (lat, lon, country) in STATIONS.items():
        if country != "my":
            continue
        best = min(feats, key=lambda a: km((lat, lon), (float(a.get("LATITUDE") or 0), float(a.get("LONGITUDE") or 0))))
        dist = km((lat, lon), (float(best.get("LATITUDE") or 0), float(best.get("LONGITUDE") or 0)))
        if dist > MAX_KM:
            notes.append(f"{sid}: nearest DOE station {best.get('STATION_LOCATION')} is {dist:.0f} km away; skipped")
            continue
        api, when = best.get("API"), best.get("DATETIME")
        if api is None or when is None or float(api) < 0:
            notes.append(f"{sid}: no reading at {best.get('STATION_LOCATION')}")
            continue
        # DATETIME is the local (UTC+8) wall-clock time stored as if it were UTC.
        t = datetime.fromtimestamp(int(when) / 1000, tz=timezone.utc).replace(tzinfo=TZ)
        name = f"DOE {best.get('STATION_LOCATION')} ({best.get('STATION_ID')}, {best.get('PARAM_SELECTED') or 'API'})"
        out.append((slot_of(t), sid, "doe_api", round(float(api)), name))
        if sid == "cheras":  # one raw time in the report, to check the time zone of DOE's DATETIME
            SAMPLES["doe"] = f"{name} DATETIME={when} -> {t.isoformat()} (slot {slot_of(t)})"
    return out, notes


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    now = datetime.now(TZ)
    report = {"run_at": now.isoformat(timespec="seconds"), "sources": {}}
    readings = []
    for name, fn in (("doe", fetch_doe),):
        try:
            got, notes = fn()
            readings += got
            report["sources"][name] = {"status": "ok" if not notes else "partial", "readings": len(got), "notes": notes}
        except Exception as exc:  # noqa: BLE001 - report and keep the other source
            report["sources"][name] = {"status": "error", "detail": f"{type(exc).__name__}: {exc}"}

    # WAQI data may not be kept as an archive (its terms of use), so remove what earlier runs stored.
    removed = 0
    for path in sorted((DATA / "archive").glob("*.json")):
        arc = load(path, {"slots": {}, "meta": {}})
        before = json.dumps(arc, sort_keys=True)
        for by_station in [*arc["slots"].values(), arc["meta"]]:
            for sid in list(by_station):
                for key in [k for k in by_station[sid] if k.startswith("waqi_")]:
                    del by_station[sid][key]
                    removed += 1
                if not by_station[sid]:
                    del by_station[sid]
        if json.dumps(arc, sort_keys=True) != before:
            save(path, arc)
    if removed:
        report["removed_waqi_values"] = removed

    # Add to the monthly archives (a later reading for the same slot replaces an earlier one). A reading
    # dated after the current slot means a time-zone mistake; it is reported, not stored.
    current = slot_of(now)
    for slot, sid, key, value, source in readings:
        if slot > current:
            report.setdefault("rejected", []).append(f"{sid} {key}: reading slot {slot} is after the current slot {current}")
            continue
        path = DATA / "archive" / f"{slot[:7]}.json"
        arc = load(path, {"slots": {}, "meta": {}})
        arc["slots"].setdefault(slot, {}).setdefault(sid, {})[key] = value
        arc["meta"].setdefault(sid, {})[key] = source
        save(path, arc)

    # series.json: the last 168 slots up to the current one.
    last = now.replace(hour=now.hour - now.hour % 2, minute=0, second=0, microsecond=0)
    slots = [last - timedelta(hours=2 * (SLOTS_SHOWN - 1 - i)) for i in range(SLOTS_SHOWN)]
    keys = [s.strftime("%Y-%m-%dT%H") for s in slots]
    archives = {m: load(DATA / "archive" / f"{m}.json", {"slots": {}, "meta": {}}) for m in sorted({k[:7] for k in keys})}
    stations: dict[str, dict[str, list]] = {}
    meta: dict[str, dict[str, str]] = {}
    for i, k in enumerate(keys):
        arc = archives[k[:7]]
        for sid, vals in arc["slots"].get(k, {}).items():
            for key, v in vals.items():
                stations.setdefault(sid, {}).setdefault(key, [None] * SLOTS_SHOWN)[i] = v
                meta.setdefault(sid, {})[key] = arc["meta"].get(sid, {}).get(key, "")
    save(DATA / "series.json", {
        "generated_at": now.isoformat(timespec="seconds"),
        "slots": [s.isoformat() for s in slots],
        "stations": stations, "meta": meta,
    })
    report["time_samples"] = SAMPLES
    text = json.dumps(report, ensure_ascii=False, indent=2)
    (DATA / "collect_report.json").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
