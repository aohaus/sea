# haze/ — ヘイズモニター / Haze Monitor

This dashboard compares air quality and haze in Malaysia (Kuala Lumpur, Penang, Johor) and Singapore across several data sources. Data points are every 2 hours (12 a day), 14 days back (168 points per series), in UTC+8. It is separate from Sea basic but uses the same colour tokens (Campur.ai palette).

## Data sources

| | Source | Indices | How data gets to the page |
|---|---|---|---|
| A | WAQI / AQICN | US AQI, PM2.5 sub-index | The viewer enters a personal token. The free API gives only the current value, so it becomes the newest point and earlier points are simulated |
| B | Malaysia DOE APIMS | API | DOE does not allow cross-site requests (CORS), so a browser cannot fetch it. Shown as simulated values until a collector writes it to `data/series.json` |
| B | Singapore NEA (data.gov.sg v2) | 24-hour PSI, 1-hour PM2.5 | Fetched in the browser (one request per day; central region) |
| C | Open-Meteo Air Quality (CAMS model) | PM2.5, PM10, US AQI | Fetched in the browser (hourly values at each location's coordinates) |

Any series that cannot be fetched falls back to **simulated values**. These are seeded random numbers that combine a regional baseline, a daily cycle and haze episodes. The chart legend, tiles and tables always label them as simulated.

## Collected data (optional)

If `data/series.json` exists, its series are shown in preference to everything else. For example, a server-side job that runs every 2 hours could write this file.

```json
{ "generated_at": "2026-10-22T14:05:00+08:00",
  "slots": ["2026-10-09T00:00:00+08:00", "..."],
  "stations": { "cheras": { "doe_api": [55, 57, "..."] } } }
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
