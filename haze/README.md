# haze/ — ヘイズモニター / Haze Monitor

This dashboard compares air quality and haze in Malaysia (Kuala Lumpur, Penang, Johor) and Singapore across several data sources. Data points are every 2 hours (12 a day), 14 days back (168 points per series), in UTC+8. It is separate from Sea basic but uses the same colour tokens (Campur.ai palette).

## Data sources

| | Source | Indices | How data gets to the page |
|---|---|---|---|
| A | WAQI / AQICN | US AQI, PM2.5 sub-index | **Collected** every 2 hours (requires the `WAQI_TOKEN` secret). Until collected data exists, a viewer can enter their own token to get the current value only |
| B | Malaysia DOE APIMS | API | **Collected** every 2 hours. A browser cannot fetch it because of CORS |
| B | Singapore NEA (data.gov.sg v2) | 24-hour PSI, 1-hour PM2.5 | Fetched in the browser (one request per day; central region) |
| C | Open-Meteo Air Quality (CAMS model) | PM2.5, PM10, US AQI | Fetched in the browser (hourly values at each location's coordinates) |

Any slot without a value is filled with **simulated values**. These are seeded random numbers that combine a regional baseline, a daily cycle and haze episodes. Legends, tiles and tables label them "模擬" (simulated) or "一部実データ" (partly real). In a partly real series, real readings are shown as dots and simulated stretches are drawn faded.

## Collection every 2 hours (GitHub Actions)

`.github/workflows/collect-haze.yml` runs `scripts/collect_haze.py` at minute 7 of every even hour (UTC+8).

- **DOE**: one request fetches the current reading of every station. Each monitor station is mapped to the nearest DOE station within 20 km.
- **WAQI**: the job fetches the current value nearest to each station. It needs the repository secret `WAQI_TOKEN` (Settings → Secrets and variables → Actions); without it, WAQI is skipped.
- **Output files**:
  - `data/archive/YYYY-MM.json`: the permanent monthly record, keyed by slot → station → series.
  - `data/series.json`: the last 14 days (168 slots), which the page reads in preference to other sources.
  - `data/collect_report.json`: the result of the latest run.
- **Commits**: each run commits its readings (`data(haze): readings …`), so up to 12 commits a day.
- **History**: neither DOE nor WAQI provides past values through the free API, so real data starts from the first collection. A full 14 days of real data takes 14 days to build up.

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
