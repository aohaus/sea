# basic/ — ASEAN 各国の基礎データ / Basic country data

ASEAN 加盟国（東ティモールを含む11か国）と ASEAN 全体の基礎データを、**出所つき**で蓄積します。
Basic data on the 11 ASEAN members (including Timor-Leste) and ASEAN as a whole, stored **with sources**.

## 構成 / Layout

| パス / Path | 内容 / Contents |
|---|---|
| `countries.json` | 対象国マスタ（フォルダコード、ISO3、日英名、JETRO URL コード） / Country master |
| `sources.json` | 出所台帳（発行元・資料名・URL・利用条件・保存方針） / Source registry |
| `schema/fields.json` | データ項目の定義（日英ラベル・単位・段階） / Field definitions |
| `<code>/<source_id>.json` | 出所ページから抽出した表・見出し（テキストのみ）と取得日。`jetro_basic`＝JETRO「概況・基本統計」、`mofa_basic`＝外務省「基礎データ」 / Extracted rows + retrieval date |
| `<code>/profile.json` | 第1段階（静的情報）の値。項目ごとに整理し、各値に出所を付与 / Static values per field, each with its source |
| `<code>/indicators.json` | 第2段階（経済指標）の時系列。出所ごとに別系列で保存 / Economic time series, one series per source |
| `<code>/worldbank_wdi.json` | 世界銀行 API から取得した観測値と URL・取得日 / Raw World Bank observations |
| `asean/` | ASEAN 全体のデータ（JETRO「ASEANの貿易投資年報」など） / ASEAN-wide data |
| `data/` | 統合データ（`dataset.json`）と出所つきの書き出し用の表（`observations`・`profiles`・`sources`・`validation` の CSV/JSON）/ Consolidated dataset and flat export tables with provenance |
| `cities/` | 主要都市のマスタ（`cities.json`）と、取得した元データ（`raw/`）・取得結果 / Major cities |
| `reference/` | 検証用の参照値（日本アセアンセンター「ひと目で分かる日ASEAN基本情報」）と照合結果 / Reference figures and validation report |
| `fetch_report.json` | 直近の取得結果（国ごとの成否・埋まった項目） / Last fetch summary |

フォルダコードは ISO 3166-1 alpha-2 の小文字です（`bn kh id la my mm ph sg th tl vn`）。
JETRO の URL ではインドネシアのみ `idn` です。

## 値の書式 / Value format

```json
"area": {
  "label_ja": "面積", "label_en": "Area", "unit": "km2", "phase": 1,
  "values": [{
    "value": 330855,
    "value_text": "33万855平方キロメートル（日本の0.87倍）",
    "as_of": null,
    "original_source": null,
    "source_label": "面積",
    "source_id": "jetro_basic",
    "url": "https://www.jetro.go.jp/world/asia/my/basic_01.html",
    "retrieved_at": "2026-10-13T00:00:00+00:00",
    "page_last_updated": "2026-08-19",
    "retrieval_method": "auto"
  }]
}
```

- `value_text` は原文の表記そのまま、`value` は数値化したものです（数値項目のみ）。
- `original_source` は、セル内に「出所：…」とある場合の元統計です（例：内務省）。
- 同じ項目で出所が複数ある場合は、上書きせず `values` に並べます。
- `retrieval_method` は取得方法です：`auto`＝スクリプトによる自動取得、`manual_pdf`＝保存されたページ PDF からの抽出。

## 照合結果を出所の一部として持つ / Cross-checks as part of provenance

各値（`data/observations`・`data/profiles` の各行、`data/dataset.json` の `checks`）に、他のデータとの照合結果を出所情報として付けます。

| 種類 | 内容 |
|---|---|
| `cross_source` | 同じ国・指標・年の、このデータ内の別の出所の値（例：世界銀行 ↔ JETRO） |
| `reference` | その国についての参照値（例：日本アセアンセンター。IMF の GDP と世界銀行の人口から算出） |
| `aggregate` | この値を合計に含めた参照値（例：ASEAN 10か国の人口）。こちらの合計と参照値の差 |

- 判定：金額・人数は差の割合で、±2%以内が「一致」、±10%以内が「近い」、それ以上が「差あり」。比率の指標（成長率・物価上昇率・失業率）はポイント差で、±0.2pt以内が「一致」、±1pt以内が「近い」、それ以上が「差あり」。
- フラットな表では `cross_check`（読める形の要約）と `cross_check_status`（最も悪い判定）の2列です。
- 例：ミャンマーの一人当たりGDP（2024年、世界銀行）は日本アセアンセンター（IMF ベース）と +20.2% の「差あり」。出所間で見方が分かれる値であることが、値と一緒に書き出されます。

## 方針 / Policy

- **保存するのは抽出した値・URL・取得日だけです。** ページ本文（HTML）の写しは保存しません。
- 値の記入は推測や記憶では行いません。取得できなかった項目は `values: []` のまま残します。
- 日英併記は**ラベルと出所のメタデータ**に適用します。値は原文の言語（JETRO は日本語）で保存します。

## 取得状況 / Coverage

- JETRO「概況・基本統計」から9か国分を取得しました（kh id la my mm ph sg th vn）。最新の状況は `fetch_report.json` を参照してください。
- ブルネイ（bn）と東ティモール（tl）は JETRO に該当ページがない（HTTP 404）ため、**外務省「基礎データ」**（`mofa_basic`）で補完します。外務省のコンテンツは公共データ利用規約（PDL1.0）に従い、出典の記載と加工した旨の明記が必要です（`sources.json` の `citation_format`）。
- 外務省サイトは GitHub Actions からの自動取得を HTTP 403 で拒否するため、手動で取り込んでいます。
  - **ブルネイ**：ブラウザで保存した PDF のテキストから抽出済み（`retrieval_method: manual_pdf`、ページ日付 2026-06-23）。
  - **東ティモール**：同上（ページ日付 2025-11-10）。
  - 取り込み手順：外務省「基礎データ」ページをブラウザで PDF 保存し、`python scripts/import_mofa_pdf.py <PDF> <国コード>` を実行してから `python scripts/fetch_basic.py --build` で profile.json を作り直します（PyMuPDF が必要）。
  - 自動取得が失敗しても、手動で取り込んだ値は上書きされません。
- ミャンマーのページには「政治体制」欄がないため、政体と元首は空です。
- シンガポールのページには「首都」欄がありません（都市国家のため）。

## 更新 / Updating

GitHub Actions の `Fetch basic country data` が各出所から取得し、結果をコミットします（抽出内容が変わらない場合はコミットしません）。
起動のタイミングは、毎月1日、手動実行、スクリプトやスキーマの変更時です。
ローカルで出所データから `profile.json` だけを作り直す場合：

```bash
python scripts/fetch_basic.py --build
python scripts/fetch_indicators.py --build
python scripts/build_dataset.py
```

## 第2段階：経済指標 / Phase 2: economic indicators

| 項目 | 単位 | 世界銀行 WDI | IMF WEO | JETRO 表 |
|---|---|---|---|---|
| 人口 | 人 | SP.POP.TOTL | LP | 「人口」欄（単年） |
| 名目GDP | USD | NY.GDP.MKTP.CD | NGDPD | ― |
| 一人当たり名目GDP | USD | NY.GDP.PCAP.CD | NGDPDPC | 1人当たりGDP |
| 実質GDP成長率 | % | NY.GDP.MKTP.KD.ZG | NGDP_RPCH | 実質GDP成長率 |
| 消費者物価上昇率 | % | FP.CPI.TOTL.ZG | PCPIPCH | 消費者物価上昇率 |
| 失業率 | % | SL.UEM.TOTL.ZS | LUR | 失業率 |
| 対内直接投資（純流入） | USD | BX.KLT.DINV.CD.WD | ― | ― |
| 為替レート（1米ドルあたりの現地通貨、年平均） | LCU/USD | PA.NUS.FCRF | ― | 為替レート |

- 値は基本単位（USD・人・%）に換算します。出所ごとに別の系列として保存し、1つの値にまとめません（出所間の差がそのまま見えるようにするため）。
- ミャンマーの JETRO 値は年度（例：2024/25年度）です。`year` は開始年とし、`note` に年度である旨を記録します。
- 為替レートは世界銀行の公式為替レート（PA.NUS.FCRF）を主な系列とし、JETRO「概況・基本統計」の為替レート欄を照合に使います。JETRO の表記が年平均でないもの（インドネシアは「期末平均」、ミャンマーは「公定レート」・年度）は、各値の `note` に記録します。
- 通貨は `countries.json` の `currency`（ISO 4217 の通貨コードと日英名）で、`data/currencies.{csv,json}` に書き出します。東ティモールは米ドルを法定通貨としています。
- 民間の金融情報サイト（Trading Economics・Investing.com・Yahoo Finance など）は、利用規約でデータの再配布や自動取得を制限しているため使いません。
- **IMF は自動取得を止めています**（`sources.json` の `auto_fetch: false`）。IMF の利用条件が、自動技術による一括ダウンロードと商用再利用に IMF の許可を求めているためです。許可を得たら有効にできます。

## 主要都市 / Major cities

`cities/cities.json` に ASEAN 各国1〜3都市（計22都市）と、比較用に日本の政令指定都市20市を定義し、`scripts/fetch_cities.py` が取得します。結果は `data/city_observations.{csv,json}` です。

| 指標 | 内容 |
|---|---|
| `grdp_per_capita_local` | 一人当たり地域GDP（現地通貨。各国統計局の州・県・市の値） |
| `grdp_per_capita_usd` | 上の値を世界銀行の公式為替レート（PA.NUS.FCRF、年平均）で米ドル換算 |
| `grdp_per_capita_ratio` | 対全国比（同じ基準の全国一人当たりGDP で割った値） |
| `city_population` | 国連 WUP 2025 の都市人口（DEGURBA の都市域。2025年より後は予測） |

| 国 | 地域GDP の出所 | 都市と単位 |
|---|---|---|
| フィリピン | PSA OpenSTAT（州・高度都市化市別、名目） | マニラ首都圏（NCR）、セブ市、ダバオ市 |
| タイ | 国家統計局 統計年鑑 表10.14（県別、名目、最新年は暫定値） | バンコク都、チョンブリ県、チェンマイ県 |
| マレーシア | 統計局 API（州別の実質GDP〔2015年価格〕÷ 州人口） | クアラルンプール（プトラジャヤを含む）、ペナン州、ジョホール州。実質値のため米ドル換算はなし |
| マレーシア（名目・2025年） | 統計局プレスリリース「State Socioeconomic Report, 2025」本文の一人当たりGDP（手動で PDF から取り込み：`scripts/import_dosm_ssr.py`） | クアラルンプール（プトラジャヤを含まない）、ペナン州。名目値のため米ドル換算あり。ジョホールは本文に値がないため未取得 |
| シンガポール | 世界銀行（国全体＝都市） | シンガポール |
| 日本（比較） | 内閣府「県民経済計算」総括表1（県内総生産・名目）・9（総人口）＜政令指定都市分＞ | 政令指定都市16市（市単位、年度値）。最新版（2023年度版）で数値の入っていないセルは前版（2022年度版）で補い、各値の `derivation` に版を記録。さいたま・相模原・静岡・熊本の4市は表に市の計数がないため地域GDP なし |
| ベトナム・インドネシア | 未取得（統計局のデータを自動取得できない） | 人口のみ |
| カンボジア・ラオス・ミャンマー・ブルネイ・東ティモール | 地域別の公表なし | 人口のみ |

- 換算や比率の行には、計算過程を `derivation` 列に書きます（例：「675,979 THB ÷ 世界銀行 公式為替レート 2023年平均 34.8022 THB/USD」）。
- 都市そのものと統計の単位が違う場合は `unit_note` に書きます（例：ジョホールバル → ジョホール州全体）。
- 国連の都市人口は都市域（市街地のまとまり）の人口で、行政区域の人口とは異なります。日本では横浜・川崎・さいたま・千葉・相模原が「東京」、京都・神戸・堺が「大阪」の都市域に含まれるため、これらの市単独の人口はありません。
- 都市ごとの単位と、データがない理由は `data/city_list.{csv,json}` にあります。

## 今後 / Next

1. 第1段階：静的情報（面積・首都・言語・公用語・宗教など）— JETRO を主、外務省で照合
2. 第2段階：経済指標（人口・GDP・一人当たりGDP・FDI）— 世界銀行・IMF API を主、JETRO を補完
3. 出所つきエクスポート（CSV / JSON）
