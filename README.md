# Malaysia News RSS Monitor

マレーシアの主要ニュースソース10件の RSS フィードを自動でヘルスチェックするツールと、
GitHub Actions による定期監視パイプラインです。

## 監視対象

| ID | ソース | 言語 | RSS URL |
|----|--------|------|---------|
| `bernama` | BERNAMA | en | https://www.bernama.com/en/rssfeed.php |
| `thestar` | The Star | en | https://www.thestar.com.my/rss/editors-picks/news |
| `malaysiakini` | Malaysiakini | en | https://www.malaysiakini.com/en/news.rss |
| `theedge` | The Edge Malaysia | en | https://theedgemalaysia.com/rss/latest-news |
| `astroawani` | Astro AWANI | ms | https://www.astroawani.com/rss/latest.xml |
| `fmt` | Free Malaysia Today | en | https://www.freemalaysiatoday.com/feed/ |
| `nst` | New Straits Times | en | https://www.nst.com.my/rss/flats/nation |
| `malaymail` | Malay Mail | en | https://www.malaymail.com/feed/rss/malaysia |
| `sinchew` | Sin Chew Daily | zh | https://www.sinchew.com.my/feed/ |
| `borneopost` | The Borneo Post | en | https://www.theborneopost.com/feed/ |

ソースの追加・変更は `config/sources.json` を編集してください（`id`, `name`, `language`, `rss_url`）。

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
FAIL    thestar       The Star              en    403        0    301ms  HTTP 403
...
-------------------------------------------------------------------------------
Result: 9/10 passed, 1 failed
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
