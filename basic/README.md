# basic/ — ASEAN 各国の基礎データ / Basic country data

ASEAN 加盟国（東ティモールを含む11か国）と ASEAN 全体の基礎データを、**出所つき**で蓄積します。
Basic data on the 11 ASEAN members (including Timor-Leste) and ASEAN as a whole, stored **with sources**.

## 構成 / Layout

| パス / Path | 内容 / Contents |
|---|---|
| `countries.json` | 対象国マスタ（フォルダコード、ISO3、日英名、JETRO URL コード） / Country master |
| `sources.json` | 出所台帳（発行元・資料名・URL・利用条件・保存方針） / Source registry |
| `schema/fields.json` | データ項目の定義（日英ラベル・単位・段階） / Field definitions |
| `<code>/jetro_basic.json` | JETRO「概況・基本統計」から抽出した表（テキストのみ）と取得日 / Extracted tables + retrieval date |
| `<code>/profile.json` | 項目ごとに整理した値。各値に出所を付与 / Values per field, each with its source |
| `asean/` | ASEAN 全体のデータ（JETRO「ASEANの貿易投資年報」など） / ASEAN-wide data |
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
    "jetro_label": "面積",
    "source_id": "jetro_basic",
    "url": "https://www.jetro.go.jp/world/asia/my/basic_01.html",
    "retrieved_at": "2026-10-13T00:00:00+00:00",
    "page_last_updated": "2026-08-19"
  }]
}
```

- `value_text` は原文の表記そのまま、`value` は数値化したものです（数値項目のみ）。
- `original_source` は、セル内に「出所：…」とある場合の元統計です（例：内務省）。
- 同じ項目で出所が複数ある場合は、上書きせず `values` に並べます。

## 方針 / Policy

- **保存するのは抽出した値・URL・取得日だけです。** ページ本文（HTML）の写しは保存しません。
- 値の記入は推測や記憶では行いません。取得できなかった項目は `values: []` のまま残します。
- 日英併記は**ラベルと出所のメタデータ**に適用します。値は原文の言語（JETRO は日本語）で保存します。

## 取得状況 / Coverage

- JETRO「概況・基本統計」から9か国分を取得しました（kh id la my mm ph sg th vn）。最新の状況は `fetch_report.json` を参照してください。
- **ブルネイ（bn）と東ティモール（tl）は JETRO に該当ページがなく（HTTP 404）、`values` は空です。** 外務省「国・地域」ページなどで補う予定です。
- ミャンマーのページには「政治体制」欄がないため、政体と元首は空です。
- シンガポールのページには「首都」欄がありません（都市国家のため）。

## 更新 / Updating

GitHub Actions の `Fetch basic country data` が JETRO から取得し、結果をコミットします。
起動のタイミングは、毎月1日、手動実行、スクリプトやスキーマの変更時です。
ローカルで出所データから `profile.json` だけを作り直す場合：

```bash
python scripts/fetch_jetro_basic.py --build
```

## 今後 / Next

1. 第1段階：静的情報（面積・首都・言語・公用語・宗教など）— JETRO を主、外務省で照合
2. 第2段階：経済指標（人口・GDP・一人当たりGDP・FDI）— 世界銀行・IMF API を主、JETRO を補完
3. 出所つきエクスポート（CSV / JSON）
