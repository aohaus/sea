// Haze Monitor: multi-source air quality for Malaysia (Kuala Lumpur, Penang, Johor) and Singapore.
//
// Every series is 168 two-hour slots (12 a day × 14 days, UTC+8). The page starts from seeded,
// realistic simulated data, then replaces what it can with live data:
//   A  WAQI / AQICN        current value only, with the viewer's own token (no free history)
//   B  DOE APIMS / NEA     NEA (data.gov.sg v2) live in the browser; DOE blocks cross-site requests,
//                          so its series stay simulated until a server-side collector provides them
//   C  Open-Meteo          modelled PM2.5 / PM10 / US AQI, live in the browser
// A collector can also publish data/series.json (same slot layout); its series take precedence.
(() => {
  'use strict';

  // ---------- places ----------
  const CITIES = [
    { id: 'kl', ja: 'クアラルンプール', en: 'Kuala Lumpur' },
    { id: 'pg', ja: 'ペナン', en: 'Penang' },
    { id: 'jh', ja: 'ジョホール', en: 'Johor' },
    { id: 'sg', ja: 'シンガポール', en: 'Singapore' },
  ];
  // Haze episodes (simulation): day offset within the 14-day window, width in days, extra PM2.5 (µg/m³).
  // The south (Johor, Singapore) gets the strongest smoke from Sumatra; Penang an earlier, weaker one.
  const STATIONS = [
    { id: 'cheras', city: 'kl', ja: 'チェラス', en: 'Cheras', lat: 3.1060, lon: 101.7180, country: 'my', base: 24, haze: [[8.8, 1.7, 58], [3.0, 0.8, 10]] },
    { id: 'batumuda', city: 'kl', ja: 'バトゥ・ムダ', en: 'Batu Muda', lat: 3.2125, lon: 101.6820, country: 'my', base: 21, haze: [[9.0, 1.8, 52], [3.1, 0.8, 9]] },
    { id: 'minden', city: 'pg', ja: 'ミンデン', en: 'Minden', lat: 5.3580, lon: 100.2950, country: 'my', base: 16, haze: [[4.2, 1.2, 30], [11.2, 0.9, 16]] },
    { id: 'sperai', city: 'pg', ja: 'スブランプライ', en: 'Seberang Perai', lat: 5.3980, lon: 100.4050, country: 'my', base: 19, haze: [[4.4, 1.3, 34], [11.3, 0.9, 18]] },
    { id: 'larkin', city: 'jh', ja: 'ラーキン', en: 'Larkin', lat: 1.4970, lon: 103.7430, country: 'my', base: 20, haze: [[9.4, 1.6, 78], [6.0, 0.7, 14]] },
    { id: 'pgudang', city: 'jh', ja: 'ジョホールバル（パシルグダン）', en: 'Johor Bahru (Pasir Gudang)', lat: 1.4700, lon: 103.9030, country: 'my', base: 22, haze: [[9.5, 1.6, 82], [6.1, 0.7, 15]] },
    { id: 'sgcentral', city: 'sg', ja: 'シンガポール中部（NEA）', en: 'Singapore Central (NEA)', lat: 1.35735, lon: 103.82, country: 'sg', base: 15, haze: [[9.7, 1.5, 70], [6.2, 0.7, 12]] },
  ];
  const stationById = new Map(STATIONS.map((s) => [s.id, s]));

  // ---------- indices and bands ----------
  // kind: index (0–500 scale, left axis) or conc (µg/m³, right axis); bands: which health scale applies.
  // In the order of how much weight they get on the page: US AQI (the scale most sites show), the
  // Malaysian API (DOE APIMS), PM2.5 concentration, Singapore's NEA readings, then WAQI.
  const SERIES = [
    { key: 'om_aqi', src: 'C', kind: 'index', ja: 'US AQI（Open-Meteo）', en: 'modelled US AQI', unit: '', bands: 'usaqi', color: '--src-c', for: ['my', 'sg'] },
    { key: 'doe_api', src: 'B', kind: 'index', ja: 'API（DOE APIMS）', en: 'Malaysia Air Pollutant Index', unit: '', bands: 'apipsi', color: '--src-b', for: ['my'] },
    { key: 'om_pm25', src: 'C', kind: 'conc', ja: 'PM2.5（Open-Meteo）', en: 'modelled PM2.5', unit: 'µg/m³', bands: 'pm25', color: '--src-d', for: ['my', 'sg'] },
    { key: 'om_pm10', src: 'C', kind: 'conc', ja: 'PM10（Open-Meteo）', en: 'modelled PM10', unit: 'µg/m³', bands: null, color: '--src-g', for: ['my', 'sg'] },
    { key: 'nea_psi', src: 'B', kind: 'index', ja: 'PSI 24時間（NEA）', en: '24-hr PSI', unit: '', bands: 'apipsi', color: '--src-b', for: ['sg'] },
    { key: 'nea_pm25', src: 'B', kind: 'conc', ja: 'PM2.5 1時間値（NEA）', en: '1-hr PM2.5', unit: 'µg/m³', bands: 'pm25', color: '--src-e', for: ['sg'] },
    // For Malaysia, WAQI republishes DOE's API as its AQI (the collected values equal DOE's), so the
    // series is labelled and banded as an API there; Singapore's is on the US EPA scale.
    { key: 'waqi_aqi', src: 'A', kind: 'index', ja: 'WAQI AQI', en: 'US-EPA AQI', unit: '', bands: 'usaqi', color: '--src-a', for: ['my', 'sg'],
      byCountry: { my: { ja: 'WAQI AQI（DOE API の転載）', en: 'Malaysian API as republished by WAQI', bands: 'apipsi' } } },
    { key: 'waqi_pm25', src: 'A', kind: 'index', ja: 'WAQI PM2.5 指数（米国基準）', en: 'PM2.5 sub-index (US EPA)', unit: '', bands: 'usaqi', color: '--src-f', for: ['my', 'sg'] },
  ];
  const seriesByKey = new Map(SERIES.map((s) => [s.key, s]));
  // A series definition as it applies to a station's country.
  const defFor = (s, country) => (s.byCountry?.[country] ? { ...s, ...s.byCountry[country] } : s);
  const SOURCES = {
    A: { ja: 'A：WAQI', en: 'World Air Quality Index (aqicn.org)', url: 'https://aqicn.org/' },
    B: { ja: 'B：政府公式', en: 'Malaysia DOE APIMS / Singapore NEA', url: 'https://eqms.doe.gov.my/' },
    C: { ja: 'C：モデル', en: 'Open-Meteo Air Quality (CAMS)', url: 'https://open-meteo.com/en/docs/air-quality-api' },
    M: { ja: '予報：MyCMAQ', en: 'MetMalaysia air-quality forecast', url: 'https://mycmaq.met.gov.my/' },
  };
  const KINDS = { index: '指数（0–500）', conc: '濃度（µg/m³）' };
  // Places mode: one metric across stations. "official" = API for Malaysia, PSI for Singapore.
  const METRICS = [
    { key: 'om_aqi', ja: 'US AQI（Open-Meteo）' },
    { key: 'om_pm25', ja: 'PM2.5（Open-Meteo、µg/m³）' },
    { key: 'official', ja: '政府公式の指数（マレーシア API／シンガポール PSI）' },
  ];

  // tone: the band colour (--band-<tone>), the same for the same words across scales:
  // green 良好, yellow 普通, lorange 敏感な人に良くない, dorange PM2.5 上昇, red 健康に良くない, purple 非常に良くない, black 危険.
  const L = (lo, hi, ja, en, tone) => ({ lo, hi, ja, en, tone });
  const BANDS = {
    usaqi: { ja: 'US AQI（米国 EPA）', axis: 'index', harmful: 150, levels: [
      L(0, 50, '良好', 'Good', 'green'), L(50, 100, '普通', 'Moderate', 'yellow'), L(100, 150, '敏感な人に良くない', 'Unhealthy for sensitive groups', 'lorange'),
      L(150, 200, '健康に良くない', 'Unhealthy', 'red'), L(200, 300, '非常に良くない', 'Very unhealthy', 'purple'), L(300, 500, '危険', 'Hazardous', 'black')] },
    apipsi: { ja: 'API・PSI（マレーシア・シンガポール）', axis: 'index', harmful: 100, levels: [
      L(0, 50, '良好', 'Good', 'green'), L(50, 100, '普通', 'Moderate', 'yellow'), L(100, 200, '健康に良くない', 'Unhealthy', 'red'),
      L(200, 300, '非常に良くない', 'Very unhealthy', 'purple'), L(300, 500, '危険', 'Hazardous', 'black')] },
    pm25: { ja: 'PM2.5 1時間値（NEA の4段階）', axis: 'conc', harmful: 55, levels: [
      L(0, 55, '通常（I）', 'Normal', 'green'), L(55, 150, '上昇（II）', 'Elevated', 'dorange'), L(150, 250, '高い（III）', 'High', 'red'),
      L(250, 500, '非常に高い（IV）', 'Very high', 'purple')] },
  };
  const category = (bandsKey, v) => {
    const b = BANDS[bandsKey];
    if (!b || v == null || !isFinite(v)) return null;
    return b.levels.find((l) => v <= l.hi) || b.levels[b.levels.length - 1];
  };

  // US EPA AQI from PM2.5 (µg/m³), 2024 breakpoints.
  const AQI_PM25 = [[0, 9.0, 0, 50], [9.1, 35.4, 51, 100], [35.5, 55.4, 101, 150], [55.5, 125.4, 151, 200], [125.5, 225.4, 201, 300], [225.5, 325.4, 301, 500]];
  // PSI-style PM2.5 sub-index (NEA), used to approximate the 24-hr PSI and, in the simulation, the DOE API.
  const PSI_PM25 = [[0, 12, 0, 50], [13, 55, 51, 100], [56, 150, 101, 200], [151, 250, 201, 300], [251, 350, 301, 400], [351, 500, 401, 500]];
  const interp = (table, c, step) => {
    if (c == null || !isFinite(c)) return null;
    const x = Math.max(0, c);
    // Truncate to the table's precision (EPA: 0.1 µg/m³; PSI: whole µg/m³), then use the band that
    // contains the value, so a value just above a band's upper bound falls in the next band.
    // Compared in whole steps (35.4 is 354 tenths), as 354 * 0.1 is not exactly 35.4 in floating point.
    const n = Math.floor(x / step + 1e-9);
    for (const [cl, ch, il, ih] of table) {
      if (n <= Math.round(ch / step)) return Math.round(il + (ih - il) * (n * step - cl) / (ch - cl));
    }
    return 500;
  };
  const usAqi = (pm) => interp(AQI_PM25, pm, 0.1);
  const psiIndex = (pm) => interp(PSI_PM25, pm, 1);

  // ---------- time slots (UTC+8, every 2 hours) ----------
  const N = 168, STEP = 2 * 3600e3, TZ = 8 * 3600e3;
  const nowMs = Date.now();
  const lastSlot = Math.floor((nowMs + TZ) / STEP) * STEP - TZ;            // latest even hour (UTC+8) not in the future
  const SLOTS = Array.from({ length: N }, (_, i) => lastSlot - (N - 1 - i) * STEP);
  const pad = (n) => String(n).padStart(2, '0');
  const local = (ms) => new Date(ms + TZ);
  const slotKey = (ms) => { const d = local(ms); return d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate()) + 'T' + pad(d.getUTCHours()); };
  const slotHour = (ms) => local(ms).getUTCHours();
  const shortLabel = (ms) => { const d = local(ms); return (d.getUTCMonth() + 1) + '/' + d.getUTCDate() + ' ' + pad(d.getUTCHours()) + ':00'; };
  const longLabel = (ms) => { const d = local(ms); return d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate()) + ' ' + pad(d.getUTCHours()) + ':00（UTC+8）'; };
  const slotIndex = new Map(SLOTS.map((ms, i) => [slotKey(ms), i]));
  const WD = ['日', '月', '火', '水', '木', '金', '土'];
  // "3時間前", "45分前" (a slot time is the start of its two hours).
  const ago = (ms) => { const m = Math.max(0, Math.round((Date.now() - ms) / 60e3)); return m < 60 ? m + '分前' : m < 48 * 60 ? Math.floor(m / 60) + '時間前' : Math.floor(m / 1440) + '日前'; };
  // The 5 days after the latest slot (60 two-hour slots), for the forecast chart.
  const NF = 60;
  const FSLOTS = Array.from({ length: NF }, (_, i) => lastSlot + (i + 1) * STEP);
  const futureIndex = new Map(FSLOTS.map((ms, i) => [slotKey(ms), i]));

  // ---------- simulation ----------
  function rng(seedText) {
    let a = 0;
    for (const ch of seedText) a = (Math.imul(a ^ ch.charCodeAt(0), 2654435761) + 0x9e3779b9) >>> 0;
    return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const gauss = (rand) => { let u = 0, v = 0; while (!u) u = rand(); while (!v) v = rand(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  // Diurnal shape: morning traffic peak, afternoon mixing low, night inversion build-up.
  const diurnal = (h) => 1 + 0.28 * Math.exp(-((h - 8) ** 2) / 6) + 0.22 * Math.exp(-((h - 21) ** 2) / 10) - 0.2 * Math.exp(-((h - 15) ** 2) / 8);
  const rolling = (arr, w) => arr.map((_, i) => { const s = arr.slice(Math.max(0, i - w + 1), i + 1).filter((v) => v != null); return s.length ? s.reduce((a, b) => a + b, 0) / s.length : null; });

  // The seed is the station and the window's last day, so the curves are stable through a day.
  const EXTRA = 12; // one more day before the window, for 24-hour averages
  function simulate(st) {
    const rand = rng(st.id + ':' + slotKey(lastSlot).slice(0, 10));
    const M = N + EXTRA;
    let ar = 0;
    const truth = [];
    for (let i = 0; i < M; i++) {
      const ms = lastSlot - (M - 1 - i) * STEP;
      const day = (i - EXTRA) / 12;
      ar = 0.82 * ar + 0.18 * gauss(rand);
      const smoke = st.haze.reduce((s, [c, w, amp]) => s + amp * Math.exp(-((day - c) ** 2) / (2 * w * w)), 0);
      truth.push(Math.max(3, (st.base * diurnal(slotHour(ms)) + smoke * (0.85 + 0.3 * diurnal(slotHour(ms)) - 0.3)) * (1 + 0.22 * ar)));
    }
    const obs = truth.map((v) => v * (1 + 0.08 * gauss(rand)));                    // station measurement
    const model = rolling(truth, 3).map((v, i, a) => (a[Math.max(0, i - 1)] ?? v) * 0.86 + 2);  // smoother, lagged, biased
    const r24 = rolling(obs, 12), r12 = rolling(obs, 6), m24 = rolling(model, 12);
    const cut = (arr) => arr.slice(EXTRA).map((v) => (v == null ? null : Math.round(v * 10) / 10));
    const out = {
      waqi_aqi: cut(obs.map((v) => usAqi(v * 1.05))),
      waqi_pm25: cut(obs.map((v) => usAqi(v))),
      om_aqi: cut(m24.map(usAqi)),
      om_pm25: cut(model),
      om_pm10: cut(model.map((v, i) => v * (1.38 + 0.06 * Math.sin(i / 5)))),
    };
    if (st.country === 'my') { out.doe_api = cut(r12.map(psiIndex)); out.waqi_aqi = out.doe_api.slice(); }
    else { out.nea_psi = cut(r24.map(psiIndex)); out.nea_pm25 = cut(obs); }
    return out;
  }

  // ---------- data store ----------
  // DATA[station][seriesKey] = { values: [168], mode: 'sim' | 'live' | 'mixed', note, real }
  // mode 'mixed': only the slots in real (a Set of indices) are real readings; the rest are simulated.
  const DATA = {};
  for (const st of STATIONS) {
    const sim = simulate(st);
    DATA[st.id] = {};
    for (const s of SERIES) if (s.for.includes(st.country)) DATA[st.id][s.key] = { values: sim[s.key], mode: 'sim', note: '模擬値' };
  }
  // Forecasts: Open-Meteo (CAMS) values for the future slots, and the MyCMAQ PM2.5 ranges.
  const FUTURE = Object.fromEntries(STATIONS.map((st) => [st.id, { om_pm25: Array(NF).fill(null), om_aqi: Array(NF).fill(null) }]));
  let MYCMAQ = null;
  const STATUS = {
    A: { state: 'sim', text: 'トークン未設定のため模擬値' },
    B: { state: 'sim', text: '取得前' },
    C: { state: 'sim', text: '取得前' },
    collector: { state: 'none', text: '' },
  };
  // Collected series (data/series.json) are kept; the browser fetchers only replace the others.
  const setLive = (st, key, values, mode, note, collected = false, real = null) => {
    const cur = DATA[st]?.[key];
    if (!cur || (cur.collected && !collected)) return;
    DATA[st][key] = { values, mode, note, collected, real };
  };
  const isReal = (data, i) => data.mode === 'live' || !!data.real?.has(i);

  // ---------- live fetchers ----------
  const fetchJson = async (url, ms = 20000) => {
    const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), ms);
    try { const r = await fetch(url, { signal: ctl.signal }); if (!r.ok) throw new Error('HTTP ' + r.status); return await r.json(); }
    finally { clearTimeout(t); }
  };

  async function loadOpenMeteo() {
    STATUS.C = { state: 'loading', text: '取得中…' }; renderStatus();
    let ok = 0;
    await Promise.all(STATIONS.map(async (st) => {
      try {
        const url = 'https://air-quality-api.open-meteo.com/v1/air-quality?latitude=' + st.lat + '&longitude=' + st.lon
          + '&hourly=pm2_5,pm10,us_aqi&past_days=15&forecast_days=6&timezone=Asia%2FSingapore';
        const d = await fetchJson(url);
        const h = d.hourly; const vals = { om_pm25: Array(N).fill(null), om_pm10: Array(N).fill(null), om_aqi: Array(N).fill(null) };
        h.time.forEach((t, j) => {
          const f = futureIndex.get(t.slice(0, 13));
          if (f != null) { FUTURE[st.id].om_pm25[f] = h.pm2_5[j]; FUTURE[st.id].om_aqi[f] = h.us_aqi[j]; }
          const i = slotIndex.get(t.slice(0, 13));
          if (i == null) return;
          vals.om_pm25[i] = h.pm2_5[j]; vals.om_pm10[i] = h.pm10[j]; vals.om_aqi[i] = h.us_aqi[j];
        });
        if (vals.om_pm25.filter((v) => v != null).length < N / 2) throw new Error('too few values');
        for (const k of Object.keys(vals)) setLive(st.id, k, vals[k], 'live', 'Open-Meteo（CAMS モデル、格子 ' + d.latitude.toFixed(2) + ', ' + d.longitude.toFixed(2) + '）');
        ok++;
      } catch (e) { console.warn('Open-Meteo', st.id, e); }
    }));
    STATUS.C = ok === STATIONS.length ? { state: 'live', text: '実データ（全' + ok + '地点）' }
      : ok ? { state: 'mixed', text: '一部実データ（' + ok + '/' + STATIONS.length + '地点、残りは模擬値）' }
      : { state: 'error', text: '取得できなかったため模擬値' };
    render();
  }

  async function loadNea() {
    STATUS.B = { state: 'loading', text: 'NEA 取得中…' }; renderStatus();
    const days = [...new Set(SLOTS.map((ms) => slotKey(ms).slice(0, 10)))];
    const pm = Array(N).fill(null), psi = Array(N).fill(null);
    let okDays = 0;
    // A few requests at a time (one per day and endpoint).
    const queue = days.flatMap((d) => [['pm25', d], ['psi', d]]);
    const worker = async () => {
      while (queue.length) {
        const [ep, day] = queue.shift();
        try {
          const d = await fetchJson('https://api-open.data.gov.sg/v2/real-time/api/' + ep + '?date=' + day);
          for (const it of d.data?.items || []) {
            const i = slotIndex.get(String(it.timestamp).slice(0, 13));
            if (i == null) continue;
            if (ep === 'pm25') pm[i] = it.readings?.pm25_one_hourly?.central ?? null;
            else psi[i] = it.readings?.psi_twenty_four_hourly?.central ?? null;
          }
          okDays++;
        } catch (e) { console.warn('NEA', ep, day, e); }
      }
    };
    await Promise.all([worker(), worker(), worker()]);
    const have = (a) => a.filter((v) => v != null).length;
    if (have(pm) >= N / 2) setLive('sgcentral', 'nea_pm25', pm, 'live', 'NEA（data.gov.sg）中部地域の1時間値');
    if (have(psi) >= N / 2) setLive('sgcentral', 'nea_psi', psi, 'live', 'NEA（data.gov.sg）中部地域の24時間 PSI');
    const live = have(pm) >= N / 2 && have(psi) >= N / 2;
    STATUS.B = live ? { state: 'mixed', text: 'NEA は実データ、DOE（マレーシア）は模擬値' }
      : { state: 'error', text: 'NEA を取得できなかったため模擬値。DOE も模擬値' };
    render();
  }

  // WAQI: the free API returns the current reading only; it becomes the latest point of the series.
  async function loadWaqi(token) {
    if (!token) { STATUS.A = { state: 'sim', text: 'トークン未設定のため模擬値' }; render(); return; }
    STATUS.A = { state: 'loading', text: '取得中…' }; renderStatus();
    let ok = 0;
    await Promise.all(STATIONS.map(async (st) => {
      try {
        const d = await fetchJson('https://api.waqi.info/feed/geo:' + st.lat + ';' + st.lon + '/?token=' + encodeURIComponent(token));
        if (d.status !== 'ok') throw new Error(String(d.data));
        const t = Date.parse(d.data.time.iso);
        const i = SLOTS.findIndex((ms) => Math.abs(ms - t) <= STEP / 2 + 1);
        if (i < 0) throw new Error('reading outside the window');
        for (const [key, v] of [['waqi_aqi', Number(d.data.aqi)], ['waqi_pm25', d.data.iaqi?.pm25?.v]]) {
          const cur = DATA[st.id][key];
          if (!cur || cur.collected || v == null || !isFinite(v)) continue;
          const values = cur.values.slice(); values[i] = v;
          // History stays simulated: only the reading at slot i is real.
          setLive(st.id, key, values, 'mixed', 'WAQI 観測局「' + d.data.city.name + '」の現在値（' + shortLabel(SLOTS[i]) + '）。それ以前は模擬値', false, new Set([i]));
        }
        ok++;
      } catch (e) { console.warn('WAQI', st.id, e); }
    }));
    STATUS.A = ok ? { state: 'mixed', text: '現在値のみ実データ（' + ok + '/' + STATIONS.length + '地点）、履歴は模擬値' } : { state: 'error', text: '取得できなかった（トークンを確認）ため模擬値' };
    render();
  }

  // A server-side collector (e.g. a GitHub Actions job every 2 hours) may publish data/series.json:
  //   { "generated_at": ISO, "slots": [ISO, ...], "stations": { "<station>": { "<series>": [values aligned to slots] } } }
  async function loadMycmaq() {
    try { MYCMAQ = await fetchJson('data/mycmaq.json', 10000); } catch (e) { MYCMAQ = null; }
  }

  let collectedAt = null; // when data/series.json was written (the latest DOE collection)
  async function loadCollector() {
    try {
      const d = await fetchJson('data/series.json', 10000);
      const idx = (d.slots || []).map((t) => slotIndex.get(slotKey(Date.parse(t))));
      let n = 0;
      // Collected readings replace the simulated values slot by slot; until 14 days have been collected
      // the older slots stay simulated (mode 'mixed').
      for (const [st, byKey] of Object.entries(d.stations || {})) for (const [key, arr] of Object.entries(byKey)) {
        if (!DATA[st]?.[key]) continue;
        const values = DATA[st][key].values.slice(), real = new Set();
        arr.forEach((v, j) => { if (idx[j] != null && v != null && isFinite(v)) { values[idx[j]] = v; real.add(idx[j]); } });
        if (!real.size) continue;
        const source = d.meta?.[st]?.[key] || '';
        setLive(st, key, values, real.size === N ? 'live' : 'mixed',
          '収集データ' + (source ? '：' + source : '') + '（' + real.size + '/' + N + '枠、' + String(d.generated_at).slice(0, 16).replace('T', ' ') + ' 更新）'
            + (real.size < N ? '。収集前の枠は模擬値' : ''), true, real);
        n++;
      }
      STATUS.collector = n ? { state: 'live', text: n + '系列に収集データ（2時間ごと）' } : { state: 'none', text: '' };
      collectedAt = Date.parse(d.generated_at) || null;
    } catch (e) { STATUS.collector = { state: 'none', text: '' }; }
  }

  // ---------- state ----------
  const DEFAULT = { city: 'kl', station: 'cheras', mode: 'indices', sources: ['A', 'B', 'C'], kinds: ['index', 'conc'],
    // WAQI is not archived (its terms of use), so without a viewer's token its lines are simulated only:
    // hidden by default, still available from the series chips.
    hidden: ['waqi_aqi', 'waqi_pm25', 'om_pm10'], metric: 'om_aqi', places: STATIONS.map((s) => s.id), bands: 'auto', located: false };
  let state = { ...DEFAULT };
  try { state = { ...DEFAULT, ...JSON.parse(localStorage.getItem('haze-ui') || '{}') }; } catch (e) { /* storage unavailable */ }
  if (!stationById.has(state.station)) state.station = DEFAULT.station;
  if (!METRICS.some((m) => m.key === state.metric)) state.metric = DEFAULT.metric;
  const set = (patch) => { state = { ...state, ...patch }; try { localStorage.setItem('haze-ui', JSON.stringify(state)); } catch (e) { /* storage unavailable */ } render(); };
  const $ = (id) => document.getElementById(id);
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const fmt = (v, unit) => (v == null || !isFinite(v) ? '—' : (unit ? (Math.round(v * 10) / 10).toLocaleString('ja-JP') : Math.round(v).toLocaleString('ja-JP')));

  // ---------- which lines to draw ----------
  function lines() {
    if (state.mode === 'indices') {
      const st = stationById.get(state.station);
      return SERIES.filter((s) => s.for.includes(st.country) && state.sources.includes(s.src) && state.kinds.includes(s.kind) && !state.hidden.includes(s.key))
        .map((s) => defFor(s, st.country)).map((s) => ({ id: s.key, def: s, label: s.ja, color: css(s.color), data: DATA[st.id][s.key], station: st }));
    }
    const palette = ['--src-a', '--src-b', '--src-c', '--src-d', '--src-e', '--src-f', '--src-g'];
    return STATIONS.filter((st) => state.places.includes(st.id)).map((st, i) => {
      const key = state.metric === 'official' ? (st.country === 'my' ? 'doe_api' : 'nea_psi') : state.metric;
      const def = defFor(seriesByKey.get(key), st.country);
      return { id: st.id, def, label: st.ja + (state.metric === 'official' ? '（' + (st.country === 'my' ? 'API' : 'PSI') + '）' : ''), color: css(palette[STATIONS.indexOf(st) % palette.length]), data: DATA[st.id][key], station: st };
    }).filter((l) => l.data);
  }
  const bandsFor = (ls) => {
    if (state.bands === 'none') return null;
    if (state.bands !== 'auto') return state.bands;
    return (ls.find((l) => l.def.kind === 'index' && l.def.bands) || ls.find((l) => l.def.bands))?.def.bands || null;
  };

  // ---------- controls ----------
  // What the folded filter panel holds, so a phone shows the selection without opening it.
  function renderFilterSummary(ls, bandsKey) {
    const parts = [];
    if (state.mode === 'indices') parts.push(stationById.get(state.station).ja, ls.length + '系列', '出所 ' + (state.sources.length ? [...state.sources].sort().join('・') : 'なし'));
    else parts.push('地点どうしを比較（' + state.places.length + '地点）');
    parts.push('色帯：' + (BANDS[bandsKey]?.ja.replace(/（.*/, '') || 'なし'));
    $('filters-summary').textContent = parts.join('／');
  }

  function renderControls() {
    $('city-tabs').replaceChildren(...CITIES.map((c) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'tab'; b.role = 'tab'; b.textContent = c.ja;
      b.setAttribute('aria-selected', String(state.city === c.id));
      b.onclick = () => {
        const first = STATIONS.find((s) => s.city === c.id);
        set(state.mode === 'indices' ? { city: c.id, station: first.id, located: false } : { city: c.id });
      };
      return b;
    }));
    const inCity = STATIONS.filter((s) => s.city === state.city);
    $('station-chips').replaceChildren(...(state.mode === 'indices' ? inCity : STATIONS).map((s) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'chip'; b.textContent = s.ja;
      if (state.mode === 'indices') {
        b.setAttribute('aria-pressed', String(state.station === s.id));
        b.onclick = () => set({ station: s.id, located: false });
      } else {
        b.setAttribute('aria-pressed', String(state.places.includes(s.id)));
        b.onclick = () => set({ places: state.places.includes(s.id) ? state.places.filter((x) => x !== s.id) : [...state.places, s.id] });
      }
      return b;
    }));
    $('city-tabs').parentElement.classList.toggle('hidden', state.mode === 'places');
    document.querySelectorAll('[data-mode]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.mode === state.mode)));
    $('mode-indices').classList.toggle('hidden', state.mode !== 'indices');
    $('mode-places').classList.toggle('hidden', state.mode !== 'places');

    const toggle = (list, v) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
    $('source-chips').replaceChildren(...Object.entries(SOURCES).map(([k, s]) => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'chip'; b.textContent = s.ja;
      b.title = s.en; b.setAttribute('aria-pressed', String(state.sources.includes(k)));
      b.onclick = () => set({ sources: toggle(state.sources, k) });
      return b;
    }));
    $('kind-chips').replaceChildren(...Object.entries(KINDS).map(([k, label]) => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'chip'; b.textContent = label;
      b.setAttribute('aria-pressed', String(state.kinds.includes(k)));
      b.onclick = () => set({ kinds: toggle(state.kinds, k) });
      return b;
    }));
    const st = stationById.get(state.station);
    $('series-chips').replaceChildren(...SERIES.filter((s) => s.for.includes(st.country) && state.sources.includes(s.src) && state.kinds.includes(s.kind)).map((s) => defFor(s, st.country)).map((s) => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'chip';
      const sw = document.createElement('span'); sw.className = 'swatch'; sw.style.background = css(s.color);
      b.append(sw, s.ja); b.setAttribute('aria-pressed', String(!state.hidden.includes(s.key)));
      b.onclick = () => set({ hidden: toggle(state.hidden, s.key) });
      return b;
    }));
    $('metric').replaceChildren(...METRICS.map((m) => new Option(m.ja, m.key)));
    $('metric').value = state.metric;
    $('bands').replaceChildren(new Option('自動（表示中の指標に合わせる）', 'auto'), ...Object.entries(BANDS).map(([k, b]) => new Option(b.ja, k)), new Option('表示しない', 'none'));
    $('bands').value = state.bands;
    $('theme').value = document.documentElement.dataset.theme || 'auto';
  }

  // ---------- now: the nearest (or chosen) station at a glance ----------
  const km = (lat1, lon1, lat2, lon2) => {
    const r = Math.PI / 180, h = Math.sin((lat2 - lat1) * r / 2) ** 2 + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin((lon2 - lon1) * r / 2) ** 2;
    return 6371 * 2 * Math.asin(Math.sqrt(h));
  };
  // here: the station nearest the viewer ({ id, km }) once located; locating: a request is open; locError: why it failed.
  let here = null, locating = false, locError = '';
  function locate(fromButton) {
    if (!navigator.geolocation) { locError = 'このブラウザは位置情報に対応していません'; render(); return; }
    locating = true; locError = ''; render();
    navigator.geolocation.getCurrentPosition((pos) => {
      const { latitude: la, longitude: lo } = pos.coords;
      const [st, d] = STATIONS.map((s) => [s, km(la, lo, s.lat, s.lon)]).sort((a, b) => a[1] - b[1])[0];
      here = { id: st.id, km: d }; locating = false;
      set({ city: st.city, station: st.id, located: true });
    }, (err) => {
      locating = false;
      locError = err.code === err.PERMISSION_DENIED ? '位置情報の利用が許可されていません（ブラウザの設定で許可できます）' : '現在地を取得できませんでした';
      if (!fromButton) locError = '';
      render();
    }, { enableHighAccuracy: false, timeout: 15000, maximumAge: 10 * 60e3 });
  }
  // The headline series: US AQI (the scale most sites show) when it is live, else the government index
  // (API / PSI) when it has real readings, else the government index (simulated, and labelled so).
  function headline(st) {
    const official = st.country === 'my' ? 'doe_api' : 'nea_psi';
    const key = ['om_aqi', official].find((k) => DATA[st.id][k] && DATA[st.id][k].mode !== 'sim') || official;
    const def = defFor(seriesByKey.get(key), st.country);
    return { def, data: DATA[st.id][key] };
  }
  function renderNow() {
    const st = stationById.get(state.station);
    $('now-station').replaceChildren(...CITIES.map((c) => {
      const g = document.createElement('optgroup'); g.label = c.ja;
      g.append(...STATIONS.filter((s) => s.city === c.id).map((s) => new Option(s.ja, s.id)));
      return g;
    }));
    $('now-station').value = st.id;
    $('locate').textContent = locating ? '📍 取得中…' : '📍 現在地から';
    $('locate').disabled = locating;
    $('now-loc').textContent = locError || (here
      ? (here.id === st.id
        ? (here.km > 150 ? '現在地はこのページの対象地域（KL・ペナン・ジョホール・シンガポール）の外です。いちばん近い観測地点（約' + Math.round(here.km).toLocaleString('ja-JP') + ' km）を表示しています。'
          : '現在地からいちばん近い観測地点です（約' + Math.max(1, Math.round(here.km)) + ' km）。')
        : '選んだ地点を表示しています。')
      : '「📍 現在地から」で近い観測地点に切り替えます（位置はこの端末の中だけで使います）。');

    const { def, data } = headline(st);
    const vals = data.values, i = latestShown(data), v = i >= 0 ? vals[i] : null;
    const cat = category(def.bands, v);
    const panel = $('now-panel');
    panel.style.background = cat ? css('--band-' + cat.tone) : css('--panel');
    panel.style.color = cat ? css('--on-band-' + cat.tone) : css('--fg');
    // Compare with the 14-day average of the same series, from real readings when there are some.
    const pool = data.mode === 'sim' ? vals.filter((x) => x != null) : vals.filter((x, j) => x != null && isReal(data, j));
    const avg = pool.length ? pool.reduce((a, b) => a + b, 0) / pool.length : null;
    let vs = '';
    if (v != null && avg != null && pool.length >= 6) {
      const d = v - avg, big = Math.abs(d) >= Math.max(5, avg * 0.2);
      vs = big ? (d > 0 ? 'いつもより高め' : 'いつもより低め') : 'いつもと同じくらい';
    }
    const days = Math.round(pool.length / 12);
    const el = (tag, cls, text) => { const e = document.createElement(tag); e.className = cls; if (text != null) e.textContent = text; return e; };
    const top = el('div', 'flex flex-wrap items-baseline gap-x-4 gap-y-1');
    const num = el('div', 'text-[3.2rem] sm:text-[3.8rem] font-black leading-none tnum', fmt(v, def.unit));
    const words = el('div', 'grid');
    words.append(el('div', 'text-[1.5rem] sm:text-[1.8rem] font-black leading-tight', cat ? cat.ja : '—'),
      el('div', 'text-[.8rem] font-bold', def.ja + (data.mode === 'sim' ? '・模擬値' : '')));
    top.append(num, words);
    const cmp = el('div', (vs ? 'text-[.95rem] font-bold' : 'text-[.8rem] font-medium') + ' mt-1', vs
      ? vs + '（' + (days >= 14 || data.mode === 'live' ? '14日' : days >= 1 ? '直近' + days + '日' : '直近') + '平均 ' + fmt(avg, def.unit) + '）'
      : 'いつもとの比較は、実データが半日分（6枠）たまってから表示します（いまは' + pool.length + '枠）');
    // When the shown value was observed: its 2-hour slot (the header has when the data was updated).
    const when = el('div', 'text-[.85rem] font-bold tnum', i >= 0
      ? (() => { const d = local(SLOTS[i]); return (d.getUTCMonth() + 1) + '/' + d.getUTCDate() + '（' + WD[d.getUTCDay()] + '）' + d.getUTCHours() + '〜' + (d.getUTCHours() + 2) + '時の値'; })()
      : 'データなし');
    panel.replaceChildren(when, top, cmp);

    // Last 24 hours as 12 coloured cells.
    const last12 = SLOTS.map((ms, j) => j).slice(-12);
    $('now-strip').replaceChildren(...last12.map((j) => {
      const x = vals[j], c = category(def.bands, x), cell = document.createElement('span');
      // Simulated slots are striped, real readings solid.
      const col = c && css('--band-' + c.tone);
      if (x == null || !c) cell.className = 'empty';
      else cell.style.background = isReal(data, j) || data.mode === 'sim' ? col : 'repeating-linear-gradient(135deg, ' + col + ' 0 3px, transparent 3px 7px)';
      cell.title = shortLabel(SLOTS[j]) + '：' + fmt(x, def.unit) + (c ? '（' + c.ja + '）' : '') + (x != null && !isReal(data, j) ? ' 模擬' : '');
      return cell;
    }));
    $('now-strip').setAttribute('aria-label', '直近24時間の区分：' + last12.map((j) => category(def.bands, vals[j])?.ja || 'データなし').join('、'));
    $('now-source').textContent = st.ja + '・' + (i >= 0 ? shortLabel(SLOTS[i]) + ' の値' : 'データなし') + '・' + SOURCES[def.src].ja.replace(/^.：/, '')
      + (data.mode === 'sim' ? '（実データがないため模擬値）' : data.mode === 'mixed' ? '（しま模様のマスは収集前の模擬値）' : '')
      + (def.bands ? '・区分は ' + BANDS[def.bands].ja : '');
  }

  // ---------- tiles ----------
  const latestOf = (arr) => { for (let i = arr.length - 1; i >= 0; i--) if (arr[i] != null) return i; return -1; };
  // The latest reading to show: in a partly real series, the latest real one (not a simulated fill).
  const latestShown = (data) => {
    if (data.mode !== 'mixed') return latestOf(data.values);
    for (let i = data.values.length - 1; i >= 0; i--) if (data.values[i] != null && isReal(data, i)) return i;
    return -1;
  };
  const modeBadge = (mode) => {
    const s = document.createElement('span');
    s.className = 'badge ' + (mode === 'live' ? 'badge-live' : mode === 'mixed' ? 'badge-live' : 'badge-sim');
    s.textContent = mode === 'live' ? '実データ' : mode === 'mixed' ? '一部実データ' : '模擬';
    return s;
  };
  function renderTiles(ls) {
    $('tiles').replaceChildren(...ls.map((l) => {
      const vals = l.data.values, i = latestShown(l.data), v = i >= 0 ? vals[i] : null;
      const cat = category(l.def.bands, v);
      const div = document.createElement('div');
      div.className = 'card grid gap-1 content-start !p-3 sm:!p-5 lg:!p-3 xl:!p-4';
      // The band colour fills the tile; the series' line colour is the small swatch by its name.
      if (cat) { div.classList.add('banded'); div.style.background = css('--band-' + cat.tone); div.style.color = css('--on-band-' + cat.tone); }
      const head = document.createElement('div'); head.className = 'flex flex-wrap items-start justify-between gap-1';
      const name = document.createElement('div'); name.className = 'text-[.8rem] font-bold leading-snug';
      const lsw = document.createElement('span'); lsw.className = 'swatch'; lsw.style.background = l.color; lsw.style.outline = '1.5px solid currentColor';
      name.append(lsw, state.mode === 'places' ? l.station.ja : l.def.ja);
      head.append(name, modeBadge(l.data.mode));
      const val = document.createElement('div'); val.className = 'text-[1.6rem] sm:text-[1.9rem] font-black leading-none tnum';
      val.textContent = fmt(v, l.def.unit);
      if (l.def.unit) { const u = document.createElement('span'); u.className = 'text-[.8rem] font-medium text-muted ml-1'; u.textContent = l.def.unit; val.append(u); }
      const sub = document.createElement('div'); sub.className = 'text-[.75rem] text-muted';
      if (cat) {
        const c = document.createElement('span'); c.className = 'font-bold'; c.style.color = css('--on-band-' + cat.tone); c.textContent = cat.ja;
        sub.append(c, '・');
      }
      sub.append(i >= 0 ? shortLabel(SLOTS[i]) : 'データなし');
      const max = Math.max(...vals.filter((x) => x != null));
      const foot = document.createElement('div'); foot.className = 'text-[.72rem] text-muted';
      foot.textContent = (state.mode === 'places' ? l.def.ja + '・' : SOURCES[l.def.src].ja + '・') + '14日間の最大 ' + fmt(isFinite(max) ? max : null, l.def.unit);
      div.append(head, val, sub, foot);
      return div;
    }));
    if (!ls.length) {
      const p = document.createElement('p'); p.className = 'note card'; p.textContent = '表示する系列がありません。出所・指標の種類・系列を選んでください。';
      $('tiles').replaceChildren(p);
    }
  }

  // ---------- charts ----------
  // Health bands drawn behind the lines, on the axis of the chosen scale.
  const bandPlugin = {
    id: 'bands',
    beforeDatasetsDraw(chart, _args, opts) {
      const b = opts.key && BANDS[opts.key];
      if (!b) return;
      const scale = chart.scales[b.axis === 'index' ? 'yIndex' : 'yConc'];
      if (!scale) return;
      const { ctx, chartArea: a } = chart;
      ctx.save();
      ctx.globalAlpha = Number(css('--band-alpha')) || 0.1;
      for (const lv of b.levels) {
        const y1 = scale.getPixelForValue(Math.min(lv.hi, scale.max)), y0 = scale.getPixelForValue(Math.max(lv.lo, scale.min));
        if (lv.lo >= scale.max || y0 <= y1) continue;
        ctx.fillStyle = css('--band-' + lv.tone);
        ctx.fillRect(a.left, Math.max(a.top, y1), a.right - a.left, Math.min(a.bottom, y0) - Math.max(a.top, y1));
      }
      ctx.globalAlpha = 0.55;
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = css('--band-red');
      const yh = scale.getPixelForValue(b.harmful);
      if (yh > a.top && yh < a.bottom) { ctx.beginPath(); ctx.moveTo(a.left, yh); ctx.lineTo(a.right, yh); ctx.stroke(); }
      ctx.restore();
    },
  };

  let trend = null, diur = null;
  // Legends say when a line is (partly) simulated, so averages of simulated values are not read as measurements.
  const legendLabel = (l) => l.label + (l.data.mode === 'sim' ? '（模擬）' : l.data.mode === 'mixed' ? '（一部実データ）' : '');
  const axisMax = (ls, kind) => {
    const m = Math.max(0, ...ls.filter((l) => l.def.kind === kind).flatMap((l) => l.data.values.filter((v) => v != null)));
    const step = kind === 'index' ? 50 : 25;
    return Math.max(kind === 'index' ? 150 : 75, Math.ceil((m * 1.08) / step) * step);
  };
  function renderTrend(ls, bandsKey) {
    const hasIndex = ls.some((l) => l.def.kind === 'index'), hasConc = ls.some((l) => l.def.kind === 'conc');
    const grid = css('--grid'), muted = css('--muted'), fg = css('--fg');
    const datasets = ls.map((l) => ({
      label: legendLabel(l),
      data: l.data.values, borderColor: l.color, backgroundColor: l.color,
      yAxisID: l.def.kind === 'index' ? 'yIndex' : 'yConc',
      borderWidth: l.data.mode === 'sim' ? 1.6 : 2.2,
      borderDash: l.def.kind === 'conc' ? [6, 3] : [],
      // In a partly real series, real readings get a dot and the simulated stretches are faded.
      pointRadius: (ctx) => (l.data.mode === 'mixed' && isReal(l.data, ctx.dataIndex) ? (l.data.real.size === 1 ? 5 : 2.5) : 0),
      segment: l.data.mode === 'mixed' ? { borderColor: (ctx) => (isReal(l.data, ctx.p0DataIndex) && isReal(l.data, ctx.p1DataIndex) ? l.color : l.color + '55') } : undefined,
      pointHoverRadius: 4, tension: 0.25, spanGaps: false,
      meta: l,
    }));
    const scales = {
      // A date label at midnight; every day on wide screens, every 2nd or 3rd day on narrow ones.
      x: { ticks: { color: muted, maxRotation: 0, autoSkip: false, font: { size: 11 },
        callback(v, i) {
          if (slotHour(SLOTS[i]) !== 0) return '';
          const step = this.chart.width >= 700 ? 1 : this.chart.width >= 450 ? 2 : 3;
          return Math.floor(i / 12) % step === 0 ? shortLabel(SLOTS[i]).split(' ')[0] : '';
        } },
        grid: { color: (c) => (c.index != null && slotHour(SLOTS[c.index]) === 0 ? grid : 'transparent') } },
    };
    if (hasIndex || !hasConc) scales.yIndex = { position: 'left', min: 0, max: axisMax(ls, 'index'), title: { display: true, text: '指数（AQI・API・PSI）', color: muted }, ticks: { color: muted }, grid: { color: grid } };
    if (hasConc) scales.yConc = { position: hasIndex ? 'right' : 'left', min: 0, max: axisMax(ls, 'conc'), title: { display: true, text: '濃度 µg/m³', color: muted }, ticks: { color: muted }, grid: { color: hasIndex ? 'transparent' : grid } };
    const options = {
      responsive: true, maintainAspectRatio: false, animation: { duration: 250 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        bands: { key: bandsKey },
        legend: { position: 'bottom', labels: { color: fg, usePointStyle: true, pointStyle: 'line', boxWidth: 28, font: { size: 12 } } },
        tooltip: {
          callbacks: {
            title: (items) => (items.length ? longLabel(SLOTS[items[0].dataIndex]) : ''),
            label: (item) => {
              const l = item.dataset.meta, v = item.parsed.y;
              const cat = category(l.def.bands, v);
              const live = isReal(l.data, item.dataIndex);
              return ' ' + l.label + '：' + fmt(v, l.def.unit) + (l.def.unit ? ' ' + l.def.unit : '') + (cat ? '（' + cat.ja + '）' : '') + (live ? '' : ' 模擬');
            },
          },
        },
      },
      scales,
    };
    const labels = SLOTS.map(shortLabel);
    if (trend) { trend.data.labels = labels; trend.data.datasets = datasets; trend.options = options; trend.update(); }
    else trend = new Chart($('trend'), { type: 'line', data: { labels, datasets }, options, plugins: [bandPlugin] });
  }

  // ---------- last 7 days and the 5-day forecast ----------
  // 2-hour slots from 7 days back to 5 days ahead: the last 84 slots of SLOTS, then FSLOTS.
  const OSLOTS = [...SLOTS.slice(-84), ...FSLOTS];
  const NOW_AT = 83; // index of the latest slot in OSLOTS
  const nowLine = {
    id: 'nowLine',
    beforeDatasetsDraw(chart) {
      const x = chart.scales.x, { ctx, chartArea: a } = chart;
      const x0 = x.getPixelForValue(NOW_AT);
      ctx.save();
      ctx.fillStyle = css('--grid'); ctx.globalAlpha = 0.5;
      ctx.fillRect(x0, a.top, a.right - x0, a.bottom - a.top);
      ctx.globalAlpha = 1; ctx.strokeStyle = css('--fg'); ctx.setLineDash([2, 3]);
      ctx.beginPath(); ctx.moveTo(x0, a.top); ctx.lineTo(x0, a.bottom); ctx.stroke();
      ctx.fillStyle = css('--muted'); ctx.font = '11px sans-serif'; ctx.textAlign = 'left';
      ctx.fillText('予報 →', x0 + 4, a.top + 12);
      ctx.restore();
    },
  };
  let outlook = null;
  function mycmaqFor(st) {
    // MyCMAQ ranges aligned to OSLOTS (a range [lo, hi] or null).
    const lo = Array(OSLOTS.length).fill(null), hi = Array(OSLOTS.length).fill(null);
    if (!MYCMAQ?.stations?.[st.id]) return null;
    const at = new Map(OSLOTS.map((ms, i) => [slotKey(ms), i]));
    MYCMAQ.times.forEach((t, j) => {
      const i = at.get(slotKey(Date.parse(t))), r = MYCMAQ.stations[st.id][j];
      if (i != null && r) { lo[i] = r[0]; hi[i] = Math.min(r[1], 600); }
    });
    return { lo, hi };
  }
  function renderOutlook() {
    const st = stationById.get(state.station);
    const muted = css('--muted'), grid = css('--grid'), fg = css('--fg');
    const pastPm = DATA[st.id].om_pm25.values.slice(-84);
    const cams = [...pastPm, ...FUTURE[st.id].om_pm25];
    const camsLive = DATA[st.id].om_pm25.mode !== 'sim';
    const my = mycmaqFor(st);
    // Observed: Malaysia's API (real readings only, right axis), Singapore's 1-hr PM2.5 (left axis).
    const obsKey = st.country === 'my' ? 'doe_api' : 'nea_pm25';
    const obs = DATA[st.id][obsKey];
    const obsVals = [...obs.values.slice(-84).map((v, k) => (isReal(obs, SLOTS.length - 84 + k) ? v : null)), ...Array(NF).fill(null)];
    const hasObs = obsVals.some((v) => v != null);
    const datasets = [];
    if (my) {
      const c = css('--src-b');
      datasets.push({ label: '_mycmaq_lo', data: my.lo, borderWidth: 0, pointRadius: 0, yAxisID: 'yConc', spanGaps: false, stepped: 'middle' },
        { label: 'MyCMAQ 予報 PM2.5（範囲）', data: my.hi, borderColor: c, backgroundColor: c + '40', borderWidth: 1, pointRadius: 0, fill: '-1', yAxisID: 'yConc', spanGaps: false, stepped: 'middle' });
    }
    if (camsLive) {
      const c = css('--src-d');
      datasets.push({ label: 'CAMS PM2.5（Open-Meteo）', data: cams, borderColor: c, backgroundColor: c, borderWidth: 2, pointRadius: 0, tension: 0.25, yAxisID: 'yConc',
        segment: { borderDash: (ctx) => (ctx.p0DataIndex >= NOW_AT ? [6, 3] : []) } });
    }
    if (hasObs) {
      const def = defFor(seriesByKey.get(obsKey), st.country), c = css(def.color);
      datasets.push({ label: '実測 ' + def.ja, data: obsVals, borderColor: c, backgroundColor: c, borderWidth: 0, pointRadius: 3, showLine: false,
        yAxisID: def.kind === 'index' ? 'yIndex' : 'yConc' });
    }
    const concMax = Math.max(75, ...[...cams, ...(my ? my.hi : []), ...(obsKey === 'nea_pm25' ? obsVals : [])].filter((v) => v != null && isFinite(v)));
    const scales = {
      x: { ticks: { color: muted, maxRotation: 0, autoSkip: false, font: { size: 11 },
        callback(v, i) { if (slotHour(OSLOTS[i]) !== 0) return ''; const step = this.chart.width >= 600 ? 1 : 2; return Math.floor(i / 12) % step === 0 ? shortLabel(OSLOTS[i]).split(' ')[0] : ''; } },
        grid: { color: (c) => (c.index != null && slotHour(OSLOTS[c.index]) === 0 ? grid : 'transparent') } },
      yConc: { position: 'left', min: 0, max: Math.ceil((concMax * 1.08) / 25) * 25, title: { display: true, text: 'PM2.5 µg/m³', color: muted }, ticks: { color: muted }, grid: { color: grid } },
    };
    if (hasObs && obsKey === 'doe_api') scales.yIndex = { position: 'right', min: 0, max: axisMax([{ def: { kind: 'index' }, data: { values: obsVals } }], 'index'), title: { display: true, text: 'API', color: muted }, ticks: { color: muted }, grid: { color: 'transparent' } };
    const options = {
      responsive: true, maintainAspectRatio: false, animation: { duration: 250 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        bands: { key: 'pm25' },
        legend: { position: 'bottom', labels: { color: fg, usePointStyle: true, boxWidth: 24, font: { size: 12 }, filter: (it) => !it.text.startsWith('_') } },
        tooltip: { filter: (it) => !it.dataset.label.startsWith('_') && it.parsed.y != null, callbacks: {
          title: (items) => (items.length ? longLabel(OSLOTS[items[0].dataIndex]) + (items[0].dataIndex > NOW_AT ? '（予報）' : '') : ''),
          label: (item) => {
            if (item.dataset.label.startsWith('MyCMAQ')) return ' MyCMAQ：' + fmt(my.lo[item.dataIndex], 'µg') + '〜' + (my.hi[item.dataIndex] >= 500 ? '500 超' : fmt(my.hi[item.dataIndex], 'µg')) + ' µg/m³';
            return ' ' + item.dataset.label + '：' + fmt(item.parsed.y, item.dataset.yAxisID === 'yConc' ? 'µg' : '');
          } } },
      },
      scales,
    };
    const labels = OSLOTS.map(shortLabel);
    if (outlook) { outlook.data.labels = labels; outlook.data.datasets = datasets; outlook.options = options; outlook.update(); }
    else outlook = new Chart($('outlook'), { type: 'line', data: { labels, datasets }, options, plugins: [bandPlugin, nowLine] });

    // One tile per day for the next 5 days (today included): the highest MyCMAQ range, and CAMS's highest value.
    const days = [];
    for (let i = NOW_AT + 1; i < OSLOTS.length; i++) {
      const d = slotKey(OSLOTS[i]).slice(0, 10);
      if (!days.length || days[days.length - 1].d !== d) days.push({ d, idx: [] });
      days[days.length - 1].idx.push(i);
    }
    const wd = ['日', '月', '火', '水', '木', '金', '土'];
    $('outlook-days').replaceChildren(...days.slice(0, 5).map(({ d, idx }) => {
      const tile = document.createElement('div'); tile.className = 'card banded grid gap-0.5 content-start !p-2.5';
      const date = new Date(d + 'T00:00:00Z');
      const head = document.createElement('div'); head.className = 'text-[.78rem] font-bold'; head.textContent = (date.getUTCMonth() + 1) + '/' + date.getUTCDate() + '（' + wd[date.getUTCDay()] + '）';
      const top = my ? idx.filter((i) => my.hi[i] != null).sort((a, b) => my.hi[b] - my.hi[a])[0] : undefined;
      const camsMax = Math.max(...idx.map((i) => cams[i]).filter((v) => v != null && isFinite(v)));
      const val = document.createElement('div'); val.className = 'text-[1.05rem] font-black leading-tight tnum';
      const sub = document.createElement('div'); sub.className = 'text-[.72rem] text-muted';
      let cat = null;
      if (top != null) {
        const lo = my.lo[top], hi = my.hi[top];
        cat = category('pm25', (lo + Math.min(hi, 500)) / 2);
        val.textContent = '最大 ' + Math.round(lo) + (hi >= 500 ? '+' : '–' + Math.round(hi));
        sub.textContent = 'MyCMAQ PM2.5 µg/m³' + (camsLive && isFinite(camsMax) ? '・CAMS 最大 ' + Math.round(camsMax) : '');
      } else if (camsLive && isFinite(camsMax)) {
        cat = category('pm25', camsMax);
        val.textContent = '最大 ' + Math.round(camsMax);
        sub.textContent = 'CAMS PM2.5 µg/m³（MyCMAQ なし）';
      } else { val.textContent = '—'; sub.textContent = '予報なし'; }
      if (cat) { tile.style.background = css('--band-' + cat.tone); tile.style.color = css('--on-band-' + cat.tone); }
      const c = document.createElement('div'); c.className = 'text-[.75rem] font-bold'; c.textContent = cat ? cat.ja : '';
      tile.append(head, val, c, sub);
      return tile;
    }));
    const init = MYCMAQ?.init ? longLabel(Date.parse(MYCMAQ.init)) : null;
    $('outlook-note').textContent = st.ja + '（' + st.en + '）。点は政府の実測（' + (obsKey === 'doe_api' ? 'マレーシア API、右の軸' : 'NEA の PM2.5 1時間値') + '）、帯は MyCMAQ、線は CAMS（点線が予報）。'
      + (init ? 'MyCMAQ は ' + init + ' 開始の予報（地図の色から読み取った範囲）。' : 'MyCMAQ の予報を読み込めていません。')
      + (camsLive ? '' : 'CAMS（Open-Meteo）を取得できていないため、その線は出していません。');
  }

  function renderDiurnal(ls) {
    const hours = Array.from({ length: 12 }, (_, k) => k * 2);
    const muted = css('--muted'), grid = css('--grid'), fg = css('--fg');
    const hasIndex = ls.some((l) => l.def.kind === 'index'), hasConc = ls.some((l) => l.def.kind === 'conc');
    const datasets = ls.map((l) => ({
      label: legendLabel(l), borderColor: l.color, backgroundColor: l.color, tension: 0.3, pointRadius: 2.5,
      borderDash: l.def.kind === 'conc' ? [6, 3] : [], yAxisID: l.def.kind === 'index' ? 'yIndex' : 'yConc',
      data: hours.map((h) => { const v = l.data.values.filter((x, i) => x != null && slotHour(SLOTS[i]) === h); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; }),
      meta: l,
    }));
    const scales = { x: { ticks: { color: muted, maxRotation: 0, autoSkip: true, autoSkipPadding: 8 }, grid: { display: false } } };
    if (hasIndex || !hasConc) scales.yIndex = { position: 'left', beginAtZero: true, ticks: { color: muted }, grid: { color: grid }, title: { display: true, text: '指数', color: muted } };
    if (hasConc) scales.yConc = { position: hasIndex ? 'right' : 'left', beginAtZero: true, ticks: { color: muted }, grid: { color: hasIndex ? 'transparent' : grid }, title: { display: true, text: 'µg/m³', color: muted } };
    const options = {
      responsive: true, maintainAspectRatio: false, animation: { duration: 250 },
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { position: 'bottom', labels: { color: fg, usePointStyle: true, pointStyle: 'line', boxWidth: 24, font: { size: 11 } } }, tooltip: { callbacks: {
        title: (items) => (items.length ? hours[items[0].dataIndex] + ':00 の平均（14日間）' : ''),
        label: (item) => ' ' + item.dataset.meta.label + '：' + fmt(item.parsed.y, item.dataset.meta.def.unit) } } },
      scales,
    };
    const labels = hours.map((h) => h + '時');
    if (diur) { diur.data.labels = labels; diur.data.datasets = datasets; diur.options = options; diur.update(); }
    else diur = new Chart($('diurnal'), { type: 'line', data: { labels, datasets }, options });
  }

  // ---------- summary ----------
  function rangeBar(l, vals, latest, max) {
    const pct = (v) => Math.max(0, Math.min(100, (v / max) * 100)) + '%';
    const wrap = document.createElement('div'); wrap.className = 'rb';
    const track = document.createElement('div'); track.className = 'rb-track';
    const b = BANDS[l.def.bands];
    for (const lv of b ? b.levels : []) {
      if (lv.lo >= max) continue;
      const seg = document.createElement('span'); seg.className = 'rb-band';
      seg.style.left = pct(lv.lo); seg.style.width = 'calc(' + pct(Math.min(lv.hi, max)) + ' - ' + pct(lv.lo) + ')';
      seg.style.background = css('--band-' + lv.tone);
      track.append(seg);
    }
    if (vals.length) {
      const lo = Math.min(...vals), hi = Math.max(...vals), avg = vals.reduce((a, c) => a + c, 0) / vals.length;
      const range = document.createElement('span'); range.className = 'rb-range';
      range.style.left = pct(lo); range.style.width = 'calc(' + pct(hi) + ' - ' + pct(lo) + ')';
      const tick = document.createElement('span'); tick.className = 'rb-avg'; tick.style.left = pct(avg);
      track.append(range, tick);
      if (latest != null) {
        const dot = document.createElement('span'); dot.className = 'rb-latest'; dot.style.left = pct(latest);
        const c = category(l.def.bands, latest);
        dot.style.background = c ? css('--band-' + c.tone) : css('--fg');
        track.append(dot);
      }
      track.title = '最小 ' + fmt(lo, l.def.unit) + '・平均 ' + fmt(avg, l.def.unit) + '・最大 ' + fmt(hi, l.def.unit) + (latest != null ? '・最新 ' + fmt(latest, l.def.unit) : '');
    }
    const scale = document.createElement('div'); scale.className = 'rb-scale';
    scale.append(document.createElement('span'), document.createElement('span'));
    scale.firstChild.textContent = '0'; scale.lastChild.textContent = max + (l.def.unit ? ' ' + l.def.unit : '');
    wrap.append(track, scale);
    return wrap;
  }

  function renderSummary(ls) {
    const rows = ls.map((l) => {
      const vals = l.data.values.filter((v) => v != null);
      const b = BANDS[l.def.bands];
      const share = b && vals.length ? vals.filter((v) => v > b.harmful).length / vals.length : null;
      const tr = document.createElement('tr'); tr.className = 'border-b border-line';
      // The name gets room (min width) and the badge its own line, so phones do not wrap each word.
      const name = document.createElement('td'); name.className = 'py-1.5 pr-2 sm:pr-3 min-w-[8rem]';
      const sw = document.createElement('span'); sw.className = 'swatch'; sw.style.background = l.color;
      const badge = document.createElement('div'); badge.className = 'mt-0.5'; badge.append(modeBadge(l.data.mode));
      name.append(sw, l.label, badge);
      const td = (t) => { const c = document.createElement('td'); c.className = 'py-1.5 px-1.5 sm:px-2 text-right whitespace-nowrap'; c.textContent = t; return c; };
      const i = latestShown(l.data);
      const latest = i >= 0 ? l.data.values[i] : null;
      tr.append(name, td(fmt(latest, l.def.unit)),
        td(fmt(vals.length ? vals.reduce((a, c) => a + c, 0) / vals.length : null, l.def.unit)),
        td(fmt(vals.length ? Math.max(...vals) : null, l.def.unit)),
        share == null ? td('—') : (() => {
          const c = td(Math.round(share * 100) + '%');
          const sub = document.createElement('div'); sub.className = 'text-[.7rem] text-muted'; sub.textContent = b.harmful + ' 超';
          c.append(sub); return c;
        })());
      tr.className = '';
      // Under the numbers, one bar: the 14-day range, the average and the latest value on the
      // band colours of the series' scale (the same axis as the chart, so index rows line up).
      const bar = document.createElement('tr'); bar.className = 'border-b border-line';
      const cell = document.createElement('td'); cell.colSpan = 5; cell.className = 'pb-2.5 pt-0.5';
      cell.append(rangeBar(l, vals, latest, axisMax(ls, l.def.kind)));
      bar.append(cell);
      return [tr, bar];
    });
    $('summary').querySelector('tbody').replaceChildren(...rows.flat());
    const key = (cls, text) => { const s = document.createElement('span'); s.className = 'inline-flex items-center gap-1.5'; const m = document.createElement('span'); m.className = cls; s.append(m, text); return s; };
    $('summary-legend').replaceChildren(key('rb-legend-range', '14日間の幅（最小〜最大）'), key('rb-legend-avg', '平均'), key('rb-legend-latest', '最新'), '背景の色は区分');
    $('summary-note').textContent = '基準超えの割合：その系列の基準で「健康に良くない」の下限（US AQI 150、API・PSI 100、PM2.5 1時間値 55 µg/m³）を超えた2時間枠の割合です。PM10 は基準を設けていません。';
  }

  // ---------- sources & status ----------
  const stateText = { live: '実データ', mixed: '一部実データ', sim: '模擬値', loading: '取得中', error: '取得失敗 → 模擬値', none: '' };
  function renderStatus() {
    const box = $('status-line');
    const items = [['A', STATUS.A], ['B', STATUS.B], ['C', STATUS.C]].map(([k, s]) => {
      const span = document.createElement('span');
      span.className = 'badge ' + (s.state === 'live' || s.state === 'mixed' ? 'badge-live' : s.state === 'error' ? 'badge-err' : 'badge-sim');
      span.textContent = SOURCES[k].ja + '：' + stateText[s.state];
      return span;
    });
    const range = document.createElement('span');
    range.textContent = '期間：' + longLabel(SLOTS[0]).replace('（UTC+8）', '') + ' 〜 ' + longLabel(SLOTS[N - 1]) + '・2時間ごと ' + N + '点';
    box.replaceChildren(range, ...items);
    if (STATUS.collector.state === 'live') { const c = document.createElement('span'); c.className = 'badge badge-live'; c.textContent = STATUS.collector.text; box.append(c); }

    // Collected series (GitHub Actions every 2 hours): how many slots of the 14 days are real.
    const collected = (keys) => {
      const ds = STATIONS.flatMap((st) => keys.map((k) => DATA[st.id][k])).filter((x) => x?.collected);
      if (!ds.length) return null;
      const share = Math.min(...ds.map((x) => (x.mode === 'live' ? N : x.real.size)));
      return { state: share >= N ? 'live' : 'mixed', text: '2時間ごとの収集データ（14日のうち' + share + '枠以上）。収集前の枠は模擬値' };
    };
    const doe = collected(['doe_api']);
    const rows = [
      ['A', 'AQI、PM2.5 指数（米国基準）', STATUS.A, 'WAQI（aqicn.org）が各国の観測局の値を集めて公開。マレーシアの AQI は DOE の API をそのまま載せたもの（DOE と同じ値）、シンガポールの AQI と各地の PM2.5 指数は米国 EPA の基準です。'
        + 'WAQI の利用条件はデータを貯めて再配布することを認めていないため、このサイトでは保存していません。下でご自身のトークンを入れると、その場で現在値だけ取得して表示します（グラフでは「系列」から表示できます）。'],
      ['B', 'マレーシア：API（DOE APIMS）', doe || { state: 'sim', text: '' }, 'マレーシア環境局の API は、ブラウザから他サイトの読み込みを許可していないため、2時間ごとにサーバー側で全観測局の現在値を取得して貯めています。'
        + (doe ? '' : 'まだ収集データがないため模擬値です。')],
      ['B', 'シンガポール：24時間 PSI、PM2.5 1時間値（NEA）', STATUS.B.state === 'mixed' ? { state: 'live' } : STATUS.B, 'シンガポール国家環境庁（NEA）の data.gov.sg v2 API から、中部地域の値を日ごとに取得します。'],
      ['C', 'PM2.5・PM10（µg/m³）、US AQI', STATUS.C, 'Open-Meteo Air Quality API（欧州 CAMS のモデル）。地点の座標に最も近い格子の1時間値です。実測ではないため、観測値との比較や傾向の確認に使います。向こう5日の予報も同じ API から取得します。'],
      ['M', 'PM2.5 の5日予報（地図）', MYCMAQ?.run ? { state: 'live', text: '' } : { state: 'error', text: '読み込めませんでした' }, 'マレーシア気象局（MetMalaysia）の大気質予報 MyCMAQ（WRF-CMAQ、9 km、1日2回）。公開されているのは地図だけなので、サーバー側で新しい予報が出るたびに PM2.5 の地図を2時間おきに取得し、各地点の位置の色を地図の色の目盛りで PM2.5 の範囲に読み替えています。'
        + (MYCMAQ?.init ? '現在の予報：' + longLabel(Date.parse(MYCMAQ.init)) + ' 開始。' : '')],
    ];
    // One block per source: name, indices and state on one line, the explanation below (readable on phones).
    $('sources').replaceChildren(...rows.map(([src, what, s, desc]) => {
      const div = document.createElement('div'); div.className = 'py-2.5 border-b border-line grid gap-1';
      const head = document.createElement('div'); head.className = 'flex flex-wrap items-center gap-x-3 gap-y-1';
      const a = document.createElement('a'); a.href = SOURCES[src].url; a.target = '_blank'; a.rel = 'noopener'; a.className = 'underline font-bold'; a.textContent = SOURCES[src].ja;
      const w = document.createElement('span'); w.className = 'text-[.82rem]'; w.textContent = what;
      const badge = document.createElement('span');
      badge.className = 'badge ' + (s.state === 'live' || s.state === 'mixed' ? 'badge-live' : s.state === 'error' ? 'badge-err' : 'badge-sim');
      badge.textContent = stateText[s.state] || '';
      head.append(a, w, badge);
      const p = document.createElement('p'); p.className = 'note'; p.textContent = desc + (s.text && s.state !== 'live' ? '（' + s.text + '）' : '');
      div.append(head, p);
      return div;
    }));
  }

  // ---------- render ----------
  function render() {
    renderControls();
    renderNow();
    const ls = lines();
    const bandsKey = bandsFor(ls);
    renderFilterSummary(ls, bandsKey);
    const b = BANDS[bandsKey];
    $('bands-note').textContent = b ? '色帯は' + (b.axis === 'index' ? '左（指数）' : '濃度') + 'の軸に合わせています。点線は「健康に良くない」の下限です。' : '';
    $('band-legend').replaceChildren(...(b ? b.levels.map((lv) => {
      const s = document.createElement('span'); const sw = document.createElement('span'); sw.className = 'swatch'; sw.style.background = css('--band-' + lv.tone);
      s.append(sw, lv.lo + '–' + (lv.hi === 500 ? '' : lv.hi) + ' ' + lv.ja + '（' + lv.en + '）'); return s;
    }) : []));
    const st = stationById.get(state.station);
    $('chart-note').textContent = state.mode === 'indices'
      ? st.ja + '（' + st.en + '）の指標を重ねています。実線は指数（左の軸）、破線は濃度（' + (ls.some((l) => l.def.kind === 'index') ? '右' : '左') + 'の軸、µg/m³）。模擬値の系列は凡例に「模擬」と付きます。'
      : (METRICS.find((m) => m.key === state.metric)?.ja || '') + 'を、選んだ地点どうしで比べています。';
    renderTiles(ls);
    renderTrend(ls, bandsKey);
    renderOutlook();
    renderDiurnal(ls);
    renderSummary(ls);
    renderStatus();
  }

  // ---------- events ----------
  document.querySelectorAll('[data-mode]').forEach((b) => { b.onclick = () => set({ mode: b.dataset.mode }); });
  $('now-station').onchange = (e) => { const s = stationById.get(e.target.value); set({ city: s.city, station: s.id, located: false }); };
  $('locate').onclick = () => locate(true);
  // The explanation shows on the first visit, then only from the 説明 button.
  const showIntro = (open) => { $('intro').classList.toggle('hidden', !open); $('intro-btn').setAttribute('aria-expanded', String(open)); };
  $('intro-btn').onclick = () => showIntro($('intro').classList.contains('hidden'));
  $('intro-close').onclick = () => showIntro(false);
  try { if (!localStorage.getItem('haze-intro-seen')) { showIntro(true); localStorage.setItem('haze-intro-seen', '1'); } } catch (e) { /* storage unavailable */ }
  $('metric').onchange = (e) => set({ metric: e.target.value });
  $('bands').onchange = (e) => set({ bands: e.target.value });
  $('theme').onchange = (e) => {
    const t = e.target.value;
    if (t === 'auto') delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = t;
    try { localStorage.setItem('haze-theme', t); } catch (err) { /* storage unavailable */ }
    render();
  };
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', render);
  let waqiToken = '';
  try { waqiToken = localStorage.getItem('haze-waqi-token') || ''; } catch (e) { /* storage unavailable */ }
  $('waqi-token').value = waqiToken;
  $('waqi-save').onclick = () => {
    waqiToken = $('waqi-token').value.trim();
    try { localStorage.setItem('haze-waqi-token', waqiToken); } catch (e) { /* storage unavailable */ }
    loadWaqi(waqiToken);
  };
  $('waqi-clear').onclick = () => {
    waqiToken = ''; $('waqi-token').value = '';
    try { localStorage.removeItem('haze-waqi-token'); } catch (e) { /* storage unavailable */ }
    // Back to the simulated WAQI series.
    for (const st of STATIONS) { const sim = simulate(st); for (const k of ['waqi_aqi', 'waqi_pm25']) DATA[st.id][k] = { values: sim[k], mode: 'sim', note: '模擬値' }; }
    loadWaqi('');
  };

  // Clock (UTC+8) in the header, with the time of the latest collected readings.
  function tick() {
    const d = local(Date.now());
    $('clock').textContent = d.getUTCFullYear() + '/' + (d.getUTCMonth() + 1) + '/' + d.getUTCDate() + '（' + WD[d.getUTCDay()] + '）' + pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes());
    $('clock').dateTime = new Date().toISOString();
    if (collectedAt) { const c = local(collectedAt); $('data-time').textContent = '・データ更新 ' + pad(c.getUTCHours()) + ':' + pad(c.getUTCMinutes()) + '（' + ago(collectedAt) + '）'; }
  }
  tick();
  setInterval(tick, 30e3);

  render();
  // A viewer who allowed location and used it last time gets the nearest station without asking;
  // choosing a station by hand turns this off (located: false).
  if (state.located && navigator.permissions?.query) {
    navigator.permissions.query({ name: 'geolocation' }).then((p) => { if (p.state === 'granted' && state.located) locate(false); }).catch(() => {});
  }
  // Live data: collector first (it may cover DOE), then the browser-callable APIs.
  Promise.all([loadCollector(), loadMycmaq()]).then(() => { tick(); return null; }).then(() => Promise.all([loadOpenMeteo(), loadNea(), waqiToken ? loadWaqi(waqiToken) : null])).then(render);
})();
