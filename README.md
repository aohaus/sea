# Malaysia News RSS Monitor

マレーシアの主要ニュースソースの RSS フィードを自動でヘルスチェックするツールと、
GitHub Actions による定期監視パイプラインです。

## 監視対象（10件）

すべて GitHub Actions のランナーから実際に接続し、HTTP 200 応答かつ RSS/Atom として
パース可能であることを確認済みです。取得経路（`via`）は2種類あります。

### 直接取得（`via: direct`・6件）

各サイトが配信している RSS を直接取得します。

| ID | ソース | 言語 | RSS URL |
|----|--------|------|---------|
| `bernama` | BERNAMA | en | https://www.bernama.com/en/rssfeed.php |
| `malaysiakini` | Malaysiakini | en | https://www.malaysiakini.com/rss/en/news.rss |
| `astroawani` | Astro AWANI | ms | https://www.astroawani.com/rss.xml |
| `fmt` | Free Malaysia Today | en | https://www.freemalaysiatoday.com/feed/ |
| `nst` | New Straits Times | en | https://www.nst.com.my/feed |
| `malaymail` | Malay Mail | en | https://www.malaymail.com/feed/rss/malaysia |

### Google News 経由（`via: google_news`・4件）

以下の4件はサイトから直接 RSS を取得できないため、Google News の検索 RSS
（`site:<ドメイン> when:1d` = 直近24時間の同サイト記事）で代替しています。

| ID | ソース | 言語 | 直接取得できない理由 |
|----|--------|------|------|
| `thestar` | The Star | en | 指定 URL・候補 URL とも HTTP 404（公開 RSS が見つからない） |
| `theedge` | The Edge Malaysia | en | 指定 URL・候補 URL とも HTTP 404（公開 RSS・サイトマップとも見つからない） |
| `sinchew` | Sin Chew Daily | zh | 全 URL で HTTP 403（WAF が GitHub Actions の IP を拒否していると推定） |
| `borneopost` | The Borneo Post | en | 全 URL で HTTP 403（同上） |

Google News 経由のソースには次の違いがあります。

- **監視の意味が異なる**: 確認しているのは「Google News がそのサイトの記事を直近24時間に収録しているか」であり、サイト自身の配信状態ではありません。
- **遅延・取りこぼし**: Google 側の収録タイミングに依存し、数十分程度の遅れや一部記事の欠落があり得ます。
- **リンク先**: 各記事のリンクは `news.google.com` 経由のリダイレクト URL になります。
- 各サイトが公開 RSS を再開した場合や、セルフホストランナーなどで 403 が解消できる場合は、`rss_url` を直接の URL に差し替え、`via` を `direct` に変更してください。

ソースの追加・変更は `config/sources.json` を編集してください
（`id`, `name`, `language`, `rss_url`, `via`）。`scripts/check_rss.py` の変更は不要です。

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
============================================================================================
Malaysia News RSS Health Check
============================================================================================
STATUS  ID            NAME                  LANG  VIA          HTTP   ITEMS     TIME  DETAIL
--------------------------------------------------------------------------------------------
OK      bernama       BERNAMA               en    direct       200       10   1506ms
OK      thestar       The Star              en    google_news  200      100    300ms
...
--------------------------------------------------------------------------------------------
Result: 10/10 passed, 0 failed
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

> 注意: 一部のニュースサイト（Sin Chew Daily、The Borneo Post など）は GitHub Actions ランナーのデータセンター IP を WAF でブロックする場合があります。
> 特定ソースのみ継続的に `403` となる場合は、URL の変更やセルフホストランナーの利用を検討してください。
