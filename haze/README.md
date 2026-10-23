# haze/ — ヘイズモニター / Haze Monitor

This dashboard compares air quality and haze in Malaysia (Kuala Lumpur, Penang, Johor) and Singapore across several data sources. Data points are every 2 hours (12 a day), 14 days back (168 points per series), in UTC+8. It is separate from Sea basic but uses the same colour tokens (Campur.ai palette).

## Pages

The app has three steps, linked by the bar fixed to the bottom of each page:

1. **知る** (`index.html`): current values and the last 14 days, by station and index.
   - At the top, 「いまの空気」 shows one station: the one nearest the viewer (📍 button, browser geolocation; the position stays in the browser) or the one they chose. It shows the government index (API / PSI) when it has real readings, otherwise the modelled US AQI. The panel is filled with the colour of the health band, compared with the 14-day average, and the last 24 hours are shown as 12 coloured cells.
   - Health-band colours, worst to best: black, purple, red, dark orange, light orange, yellow, green (`--band-*` in `src.css`). A category name has the same colour on every scale: 危険 black, 非常に良くない purple, 健康に良くない red, 敏感な人に良くない light orange, 普通 yellow, 良好 green. Dark orange is NEA's PM2.5 band II (上昇).
   - Station, comparison mode, sources, series and band scale are under 詳細設定 (folded). The page explanation shows on the first visit, then from the 説明 button.
2. **理解する** (`understand.html`):
   - how the indices differ (purpose, publisher, averaging time, reliability, best use)
   - 「同じ空気、違う数字」: a converter from one PM2.5 concentration to US AQI, PSI, NEA's 1-hour band and multiples of the WHO guideline
   - types and causes of haze
   - seasons
   - sources
3. **アクションする**: not built yet.

## Data sources

| | Source | Indices | How data gets to the page |
|---|---|---|---|
| A | WAQI / AQICN | AQI (Malaysia: DOE's API republished unchanged, the same value as DOE; Singapore: US EPA scale), PM2.5 sub-index (US EPA scale) **Not collected**: WAQI's terms of use do not allow its API data to be redistributed as cached or archived data. A viewer can enter their own token to get the current value only. Earlier collected values are removed by the collector, and the WAQI lines are hidden by default |
| B | Malaysia DOE APIMS | API | **Collected** every hour into 2-hour slots. A browser cannot fetch it because of CORS |
| B | Singapore NEA (data.gov.sg v2) | 24-hour PSI, 1-hour PM2.5 | Fetched in the browser (one request per day; central region) |
| C | Open-Meteo Air Quality (CAMS model) | PM2.5, PM10, US AQI | Fetched in the browser (hourly values at each location's coordinates) |

Any slot without a value is filled with **simulated values**. These are seeded random numbers that combine a regional baseline, a daily cycle and haze episodes. Legends, tiles and tables label them "模擬" (simulated) or "一部実データ" (partly real). In a partly real series, real readings are shown as dots and simulated stretches are drawn faded.

## Collection (GitHub Actions)

`.github/workflows/collect-haze.yml` runs `scripts/collect_haze.py` at minute 7 of every hour. GitHub sometimes delays or skips scheduled runs under load. Running hourly means each 2-hour slot still gets a reading when one run is missed; the later reading in a slot replaces the earlier one.

- **DOE**: one request fetches the current reading of every station. Each monitor station is mapped to the nearest DOE station within 20 km.
- **WAQI**: not collected (see the table above). Each run removes `waqi_*` values stored by earlier versions, so the `WAQI_TOKEN` secret is no longer used.
- **Output files**:
  - `data/archive/YYYY-MM.json`: the permanent monthly record, keyed by slot → station → series.
  - `data/series.json`: the last 14 days (168 slots), which the page reads in preference to other sources.
  - `data/collect_report.json`: the result of the latest run.
- **Commits**: each run commits its readings (`data(haze): readings …`), so up to 24 commits a day.
- **History**: DOE does not provide past values through its public map service, so real data starts from the first collection. A full 14 days of real data takes 14 days to build up.

Format of `data/series.json`:

```json
{ "generated_at": "2026-10-22T14:07:00+08:00",
  "slots": ["2026-10-09T00:00:00+08:00", "..."],
  "stations": { "cheras": { "doe_api": [null, 57, "..."] } },
  "meta": { "cheras": { "doe_api": "DOE Cheras (CA0012, PM2.5)" } } }
```

- Station ids: `cheras` `batumuda` `minden` `sperai` `larkin` `pgudang` `sgcentral`
- Series keys: `waqi_aqi` `waqi_pm25` `doe_api` `nea_psi` `nea_pm25` `om_aqi` `om_pm25` `om_pm10`

## Files and build

- `index.html`, `app.js`: the page.
- `vendor/chart-4.4.1.umd.min.js`: Chart.js 4.4.1 (MIT).
- `haze.css`: built from `src.css` with Tailwind CSS v3. After changing classes, rebuild it:

```
npx tailwindcss@3.4.17 -c haze/tailwind.config.js -i haze/src.css -o haze/haze.css --minify
```
