#!/usr/bin/env python3
"""Read the MyCMAQ 5-day PM2.5 forecast at each Haze Monitor station (haze/data/mycmaq.json).

MyCMAQ (https://mycmaq.met.gov.my/) is MetMalaysia's air-quality forecast (WRF-CMAQ, run twice a day,
120 hourly steps). It publishes maps only, as PNG images: no numbers per place. This script reads
the PM2.5 map of the Malaysia domain (d02, 9 km) at each station's position and turns the colour into
the PM2.5 range of that colour on the map's scale. So each value is a range (e.g. 55–87 µg/m³),
not a point value.

The maps have fixed axes (checked on two runs): 110°E at x=574 and 115°E at x=783, 4°N at y=452 and
2°S at y=703, linear in both directions. The colour scale has 24 flat colours, with edges labelled
0, 35, 55, 150, 200, 250, 375 and 500 µg/m³; the edges between labels are spaced evenly. If a map no
longer has this layout (another size, or the expected scale colours missing), the run is skipped and
reported, and the previous forecast is kept.

Runs hourly from the collector workflow, and only downloads when MetMalaysia has published a new run.

Usage:
  python scripts/collect_mycmaq.py [--force]
"""

from __future__ import annotations

import io
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "haze" / "data" / "mycmaq.json"
TZ = timezone(timedelta(hours=8))
BASE = "https://mycmaq.met.gov.my"
HEADERS = {"User-Agent": "sea-haze-collector/0.1 (+https://github.com/aohaus/sea)"}
VARIABLE = "PM25_TOT_d02"
EVERY_HOURS = 2  # the page uses 2-hour steps

# Same ids and coordinates as haze/app.js.
STATIONS = {
    "cheras": (3.1060, 101.7180), "batumuda": (3.2125, 101.6820),
    "minden": (5.3580, 100.2950), "sperai": (5.3980, 100.4050),
    "larkin": (1.4970, 103.7430), "pgudang": (1.4700, 103.9030),
    "sgcentral": (1.35735, 103.82),
}

# Map axes (pixels of the 1024 x 1024 image).
X110, X115, Y4N, Y2S = 574, 783, 452, 703


def pixel(lat: float, lon: float) -> tuple[int, int]:
    x = X110 + (lon - 110) * (X115 - X110) / 5
    y = Y4N + (4 - lat) * (Y2S - Y4N) / 6
    return round(x), round(y)


# The colour scale, low to high, with each colour's PM2.5 range (µg/m³).
SCALE = [(255, 255, 255), (250, 255, 250), (220, 255, 220), (60, 200, 60), (0, 255, 0), (255, 255, 180), (255, 235, 120),
         (255, 255, 0), (255, 190, 120), (255, 160, 80), (255, 126, 0), (255, 60, 60), (255, 25, 25), (255, 0, 0),
         (180, 60, 180), (150, 25, 150), (128, 0, 128), (160, 30, 50), (140, 15, 45), (126, 0, 35), (100, 0, 25),
         (70, 0, 15), (40, 0, 5), (0, 0, 0)]


def _edges() -> list[float]:
    # Labelled edges and the number of colours between them; the first colour is below 0 (0 here).
    labelled = [(0, 0), (35, 3), (55, 4), (150, 3), (200, 3), (250, 3), (375, 3), (500, 3)]
    edges = [0.0]
    for (lo, _), (hi, n) in zip(labelled, labelled[1:]):
        edges += [lo + (hi - lo) * k / n for k in range(1, n + 1)]
    return edges


EDGES = _edges()  # 23 edges: colour i (1..22) covers EDGES[i-1]..EDGES[i]
RANGES = [(0.0, 0.0)] + [(round(EDGES[i - 1], 1), round(EDGES[i], 1)) for i in range(1, len(EDGES))] + [(500.0, 999.0)]
assert len(RANGES) == len(SCALE)


def read_range(img: Image.Image, lat: float, lon: float) -> list[float] | None:
    """The PM2.5 range at a position: the most common scale colour in a 9 x 9 pixel square (wind barbs and
    coastlines are drawn in black over the colours, so black only counts when it fills most of the square)."""
    px = img.load()
    x0, y0 = pixel(lat, lon)
    colours = Counter(px[x, y] for x in range(x0 - 4, x0 + 5) for y in range(y0 - 4, y0 + 5))
    black = colours.pop((0, 0, 0), 0)
    found = [(n, c) for c, n in colours.items() if c in SCALE]
    if not found:
        return list(RANGES[-1]) if black > 40 else None
    return list(RANGES[SCALE.index(max(found)[1])])


def get(url: str, **kw) -> requests.Response:
    r = requests.get(url, headers=HEADERS, timeout=(10, 30), **kw)
    r.raise_for_status()
    return r


def main() -> int:
    now = datetime.now(TZ)
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    runs = sorted(set(re.findall(r"display_(\d{8}_\d{2})\.html", get(BASE + "/").text)))
    if not runs:
        raise SystemExit("no forecast runs listed on the MyCMAQ page")
    run = runs[-1]
    if run == old.get("run") and "--force" not in sys.argv:
        print(f"run {run} already read")
        return 0

    files = sorted(f for f in get(f"{BASE}/{run}/manifest.json").json()["files"] if f.startswith(VARIABLE + "_"))
    frames, values, problems = [], {sid: [] for sid in STATIONS}, []
    for name in files:
        m = re.search(r"_(\d{8})_(\d{2})LST\.png$", name)
        if not m or int(m.group(2)) % EVERY_HOURS:
            continue
        valid = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H").replace(tzinfo=TZ)
        try:
            img = Image.open(io.BytesIO(get(f"{BASE}/{run}/{name}").content)).convert("RGB")
        except (requests.RequestException, OSError) as exc:
            problems.append(f"{name}: {type(exc).__name__}")
            continue
        # The layout check: the size and the colour scale (row y=845) must be as expected.
        bar = {img.getpixel((x, 845)) for x in range(120, 975, 36)}
        if img.size != (1024, 1024) or len(bar & set(SCALE)) < 20:
            problems.append(f"{name}: map layout changed (size {img.size}, {len(bar & set(SCALE))} scale colours)")
            break
        frames.append(valid.isoformat(timespec="minutes"))
        for sid, (lat, lon) in STATIONS.items():
            values[sid].append(read_range(img, lat, lon))

    if not frames or any("layout" in p for p in problems):
        report = {**old, "checked_at": now.isoformat(timespec="seconds"), "problem": problems[:5] or ["no frames"]}
        OUT.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(json.dumps(report["problem"], ensure_ascii=False))
        return 0

    init = datetime.strptime(run, "%Y%m%d_%H").replace(tzinfo=timezone.utc)
    data = {
        "run": run,
        "init": init.isoformat(),
        "fetched_at": now.isoformat(timespec="seconds"),
        "source": {"name": "MyCMAQ (MetMalaysia)", "url": f"{BASE}/display_{run}.html", "variable": VARIABLE},
        "unit": "µg/m³",
        "note": "PM2.5 range read from the colour of the forecast map at each station",
        "times": frames,
        "stations": values,
        "problems": problems[:10],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"run {run}: {len(frames)} frames, {len(problems)} problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
