# Malaysia News RSS Monitor

マレーシアの主要ニュースソースの RSS フィードを自動でヘルスチェックするツールと、
GitHub Actions による定期監視パイプラインです。

## 監視対象（動作確認済み・6件）

各ソースについて、GitHub Actions のランナーから実際に RSS URL へ接続し、
HTTP 200 応答かつ RSS/Atom としてパース可能であることを確認済みです。

| ID | ソース | 言語 | RSS URL |
|----|--------|------|---------|
| `bernama` | BERNAMA | en | https://www.bernama.com/en/rssfeed.php |
| `malaysiakini` | Malaysiakini | en | https://www.malaysiakini.com/rss/en/news.rss |
| `astroawani` | Astro AWANI | ms | https://www.astroawani.com/rss.xml |
| `fmt` | Free Malaysia Today | en | https://www.freemalaysiatoday.com/feed/ |
| `nst` | New Straits Times | en | https://www.nst.com.my/feed |
| `malaymail` | Malay Mail | en | https://www.malaymail.com/feed/rss/malaysia |

ソースの追加・変更は `config/sources.json` を編集してください（`id`, `name`, `language`, `rss_url`）。

## 未収録のソース（既知の制限事項）

当初の要件には以下の4件も含まれていましたが、現時点で有効な RSS URL を
特定できなかったため、監視対象から除外しています。

| ソース | 言語 | 状況 |
|--------|------|------|
| The Star | en | 指定 URL・複数の候補 URL とも HTTP 404。現行の RSS URL が不明 |
| The Edge Malaysia | en | 指定 URL・複数の候補 URL とも HTTP 404。現行の RSS URL が不明 |
| Sin Chew Daily | zh | 全候補 URL・複数の User-Agent で HTTP 403。WAF が GitHub Actions のIPを拒否している可能性 |
| The Borneo Post | en | 全候補 URL・複数の User-Agent で HTTP 403。WAF が GitHub Actions のIPを拒否している可能性 |

正しい RSS URL が判明した場合は、`config/sources.json` にエントリを追加してください
（`scripts/check_rss.py` の変更は不要です）。403 が続くソースについては、
セルフホストランナーの利用や別経路でのアクセスが必要になる可能性があります。

## ファイル構成

```
.
├── .github/workflows/rss-monitor.yml  # 定期実行ワークフロー
├── config/sources.json                # 監視対象ソース定義
├── scripts/check_rss.py               # ヘルスチェックスクリプト
├── requirements.txt                   # 依存ライブラリ (requests, feedparser)
└── README.md
```

## チェック内容

`scripts/check_rss.py` は各ソースに対して以下を検証します。

1. ブラウザ相当の `User-Agent` / `Accept` ヘッダーを付与して GET（WAF によるボット判定の回避）
2. タイムアウト 10 秒以内に応答し、HTTP ステータスが `200` であること
3. レスポンスが RSS/Atom の XML としてパースでき、記事（item/entry）が1件以上含まれること

結果はターミナルにサマリー表として出力されます。1件でも失敗があれば終了コード `1`
（`sys.exit(1)`）を返し、CI 上ではジョブが Fail になります。全件成功時は `0` です。

出力例:

```
===============================================================================
Malaysia News RSS Health Check
===============================================================================
STATUS  ID            NAME                  LANG  HTTP   ITEMS     TIME  DETAIL
-------------------------------------------------------------------------------
OK      bernama       BERNAMA               en    200       20    812ms
OK      malaysiakini  Malaysiakini          en    200       10    350ms
...
-------------------------------------------------------------------------------
Result: 6/6 passed, 0 failed
```

## ローカル実行

Python 3.9 以上が必要です。

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/check_rss.py
echo $?                          # 0 = 全件成功, 1 = 失敗あり
```

## CI/CD（GitHub Actions）

ワークフロー: `.github/workflows/rss-monitor.yml`

- **定期実行**: 毎日 UTC 00:00（JST 09:00）に `cron: "0 0 * * *"` で起動
  - GitHub Actions のスケジュール実行は混雑時に数分〜数十分遅れる場合があります。
- **手動実行**: `workflow_dispatch` を設定済み。GitHub の **Actions → RSS Monitor → Run workflow** から実行できます。
- **処理内容**: リポジトリをチェックアウト → Python 3.12 をセットアップ → 依存をインストール → `python scripts/check_rss.py` を実行
- **判定**: スクリプトが終了コード `1` を返すとジョブが失敗となり、GitHub の通知設定に従って失敗通知が届きます。
- 詳細な結果はジョブログの「Run RSS health check」ステップで確認できます。

> 注意: 一部のニュースサイトは GitHub Actions ランナーのデータセンター IP を WAF でブロックする場合があります。
> 特定ソースのみ継続的に `403` となる場合は、URL の変更やセルフホストランナーの利用を検討してください。
