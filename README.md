# World Data Lens

World Bank Indicators APIの公開データを自動取得し、整形・SQLite保存・集計・可視化する学習用Webアプリケーションです。

ローカルPCだけで動作します。APIキーや有料サービスは不要です。

## プロジェクト概要

このプロジェクトでは、次の一連の処理を実装しています。

```text
World Bank Indicators API
        ↓
取得（タイムアウト・リトライ・アクセス間隔）
        ↓
整形・欠損検査・数値変換
        ↓
SQLiteへ重複を避けて保存
        ↓
pandasで集計
        ↓
Flask + HTML/CSS/JavaScript + Chart.jsで表示
```

以前リポジトリ直下にあったプラットフォームゲームは削除せず、`legacy/platformer/` に保存しています。

## 何ができるか

- 世界15か国について、3つの指標を公式APIから取得
- 同じ「国・指標・年」のデータを再取得しても重複しないUPSERT保存
- 取得成功、欠損による除外、失敗、新規保存、更新、変更なしの件数を記録
- トップページで件数、最終更新日時、最新データ、更新結果、人口推移を確認
- データ一覧をキーワード、国、地域、所得区分、指標、期間、値の範囲で絞り込み
- 国、地域、指標、年、値、取得日時による並び替え
- 25・50・100件単位のページネーション
- 現在の絞り込み条件を反映したCSVダウンロード
- 時系列、地域別比較、国別ランキングをグラフ表示
- CLIからデータ更新
- ヘルスチェック用JSONエンドポイント

初期設定では次の指標を扱います。

| 指標コード | 表示名 | 単位 |
|---|---|---|
| `SP.POP.TOTL` | 人口（総数） | 人 |
| `SP.URB.TOTL.IN.ZS` | 都市人口比率 | % |
| `SP.DYN.LE00.IN` | 平均寿命 | 年 |

対象国や期間は `.env` で変更できます。

## アーキテクチャ

役割を分けているため、API、データベース、Web画面を個別に交換できます。

```text
manage.py / Flask routes
          ↓
src/services/              ユースケース・集計
       ↙          ↘
src/acquisition/      src/database/
外部API取得・整形      SQLite保存・検索
          ↓                 ↓
World Bank API        instance/dashboard.db
```

- `src/acquisition/`: HTTPアクセスとAPIレスポンスの整形
- `src/services/`: 更新処理の順序制御とpandas集計
- `src/database/`: SQLiteの初期化、保存、検索
- `src/web/`: Flaskルート、テンプレート、CSS、JavaScript

Webルートから直接APIを呼ばないため、API障害が発生しても保存済みデータの閲覧は継続できます。

## データ取得元

取得元は[World Bank Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation)です。APIはWorld Bank Open Dataと同じ時系列指標へプログラムからアクセスする公式手段です。

### なぜ利用して問題ないと判断したか

- HTMLをスクレイピングせず、提供元の公式API v2を利用しています。
- [World Bankのデータ利用条件](https://data.worldbank.org/summary-terms-of-use)では、個別メタデータに別の表示がない限り、データセットはCC BY 4.0の下で商用・非商用を問わず利用、共有、加工、表示できると説明されています。
- このアプリとCSVには取得元名とAPI URLを保存し、画面フッターにもWorld Bankへの帰属表示を行っています。
- API利用でありHTMLページをクロールしないため、Webページの`robots.txt`によるクロール可否判定は対象外です。
- [公式の開発ベストプラクティス](https://datahelpdesk.worldbank.org/knowledgebase/articles/902064-development-best-practices)は結果のキャッシュを推奨しています。本アプリでは取得結果をSQLiteに保存し、閲覧のたびにAPIへアクセスしません。
- 1回の更新は国メタデータ1回と指標3回の合計4リクエストです。各リクエストの間に初期値0.5秒の間隔を設けています。

本番利用では、使用する各指標のメタデータに第三者由来のデータや個別条件がないかを改めて確認し、World Bankの名称・ロゴを公式提携のように表示しないでください。本アプリはWorld Bankの公式製品ではありません。

## データ取得方法

`src/acquisition/client.py` が、次のような公式APIへGETリクエストを送ります。

```text
https://api.worldbank.org/v2/country/{国コード}/indicator/{指標コード}
```

アクセス制御は次のとおりです。

- 接続・読み取りタイムアウト: 初期値20秒
- `User-Agent`: `.env` で設定
- 429、500、502、503、504: 最大3回リトライ
- exponential backoff: 初期係数0.8
- `Retry-After`ヘッダーを尊重
- リクエスト間隔: 初期値0.5秒
- 並列リクエストなし

## ディレクトリ構成

```text
.
├── app.py                         # WSGIエントリーポイント
├── manage.py                      # DB初期化・更新・Web起動CLI
├── requirements.txt               # 実行用依存パッケージ
├── requirements-dev.txt           # テスト用依存パッケージ
├── .env.example                   # 環境変数の見本
├── src/
│   ├── config.py                  # 環境変数と指標設定
│   ├── acquisition/
│   │   ├── client.py              # HTTP・リトライ・アクセス間隔
│   │   └── parser.py              # APIレスポンスの検査・整形
│   ├── database/
│   │   ├── schema.sql             # SQLiteスキーマ
│   │   └── repository.py          # 保存・検索・ページネーション
│   ├── services/
│   │   ├── data_service.py        # 取得→整形→保存の処理順序
│   │   └── aggregation_service.py # pandas集計
│   └── web/
│       ├── routes.py              # HTML・JSON・CSVルート
│       ├── templates/             # Jinja2 HTML
│       └── static/                # CSS・Chart.js用JavaScript
├── tests/                          # 外部APIをモックしたpytest
└── legacy/platformer/              # 以前のゲーム（保存）
```

`instance/dashboard.db` は初回実行時に自動作成されます。

## セットアップ

### 1. 必要条件

- Python 3.10以上（開発時の確認環境はPython 3.12）
- インターネット接続（データ更新とChart.jsの読込み時）

### 2. リポジトリを取得

```bash
git clone https://github.com/Kaito-Mori0516/codex.git
cd codex
```

### 3. 仮想環境

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

ターミナルの先頭に `(.venv)` と表示されれば有効です。

### 4. 必要パッケージのインストール

アプリを動かすだけの場合:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

テストも行う場合:

```bash
python -m pip install -r requirements-dev.txt
```

### 5. 環境変数

```bash
cp .env.example .env
```

初期設定のままでも起動できます。`.env` はGit管理対象外です。

## データ取得方法

仮想環境を有効にした状態で実行します。

```bash
python manage.py update
```

成功時は次のように件数が表示されます。

```text
Status: success
取得・整形成功: 1155件
新規保存: 1155件
更新: 0件
変更なし: 0件
欠損のため除外: 15件
失敗: 0件
```

再実行時は同じ「国・指標・年」を更新するため、データ件数は無意味に増えません。

## Webサーバー起動方法

```bash
python manage.py run
```

起動後、ブラウザで次を開きます。

```text
http://127.0.0.1:5000
```

終了するときは、起動したターミナルで `Control + C` を押します。

ポートを変更する例:

```bash
python manage.py run --port 8000
```

### 主なURL

| URL | 内容 |
|---|---|
| `/` | トップダッシュボード |
| `/data` | データ一覧・検索・絞り込み・並び替え |
| `/charts` | 時系列・地域比較・ランキング |
| `/data.csv` | 絞り込み後のCSV |
| `/api/chart-data` | グラフ用JSON |
| `/health` | ヘルスチェック |

## テスト方法

```bash
python -m pytest -q
```

カバレッジも確認する場合:

```bash
python -m pytest --cov=src --cov-report=term-missing
```

テストは外部APIへアクセスしません。HTTPレスポンスをモックし、次を検証します。

- データ取得時のパラメータ、タイムアウト、HTTPエラー
- APIレスポンス構造変更の検出
- 欠損値・数値変換失敗を含むデータ整形
- SQLite保存と重複防止
- 条件検索、並び替え、ページネーション
- pandas集計
- 更新処理全体
- HTML、JSON、CSV、ヘルスチェック

## データベース

開発段階ではSQLiteを使用し、初期値では `instance/dashboard.db` に保存します。

### `indicator_values`

| 主な列 | 内容 |
|---|---|
| `id` | SQLite内部ID |
| `country_code` / `country_name` | 国コード・国名 |
| `region` | World Bank地域区分 |
| `income_level` | 所得区分 |
| `indicator_code` / `indicator_name` | 指標コード・表示名 |
| `value` / `unit` | 値・単位 |
| `year` / `period` | 対象年・日付形式の期間 |
| `retrieved_at` | データ取得日時（UTC） |
| `source_name` / `source_url` | 取得元 |

`country_code + indicator_code + year` に一意制約があります。

### `update_runs`

更新処理ごとに、開始・完了日時、状態、成功、保存、欠損、失敗件数を記録します。

SQLiteファイルは、公開APIから再生成でき、実行のたびに更新されるためGitHubへ含めません。サンプルDBの代わりにモックデータを使うテストを同梱しています。

## 環境変数

| 変数 | 初期値 | 内容 |
|---|---|---|
| `DATABASE_PATH` | `instance/dashboard.db` | SQLiteファイル |
| `WORLD_BANK_API_BASE_URL` | `https://api.worldbank.org/v2` | 公式API |
| `WORLD_BANK_COUNTRIES` | 15か国 | カンマ区切りISO3コード |
| `DATA_START_YEAR` | `2000` | 取得開始年 |
| `DATA_END_YEAR` | 空欄 | 空欄なら現在年 |
| `REQUEST_TIMEOUT_SECONDS` | `20` | HTTPタイムアウト |
| `REQUEST_MAX_RETRIES` | `3` | 最大リトライ回数 |
| `REQUEST_BACKOFF_FACTOR` | `0.8` | backoff係数 |
| `REQUEST_INTERVAL_SECONDS` | `0.5` | リクエスト間隔 |
| `USER_AGENT` | 学習用の初期値 | APIへ送る識別情報 |
| `FLASK_HOST` | `127.0.0.1` | ローカル待受先 |
| `FLASK_PORT` | `5000` | ローカルポート |
| `FLASK_DEBUG` | `false` | デバッグモード |

秘密情報は現在必要ありません。将来APIキーを追加する場合は `.env` に保存し、ソースコードやREADMEへ値を書かないでください。

## エラー処理

- 接続失敗: タイムアウト後に安全なエラーメッセージを記録
- HTTP 404: API URLの変更として失敗扱い
- HTTP 429: `Retry-After`を尊重して再試行後、失敗扱い
- HTTP 500系: exponential backoff付きで再試行
- API構造変更: JSONの型とデータ部分を検査
- データ欠損: 保存せず「欠損のため除外」に計上
- 数値変換失敗: 処理全体を止めず「失敗」に計上
- 指標単位の失敗: 他の指標の保存を継続し、状態を`partial`に設定
- DB接続失敗: Webではエラーページ、CLIでは終了コード1

データ取得に失敗しても、既にSQLiteへ保存済みのデータはWebで閲覧できます。

## データ更新の自動化（ローカル）

手動更新は次です。

```bash
python manage.py update
```

定期更新はOSのcron等から同じコマンドを呼び出せます。仮想環境とプロジェクトへの絶対パスを指定してください。公開Web画面には更新ボタンを置いていないため、第三者がデータ取得処理を起動することはありません。

## 注意事項

- Flask付属サーバーはローカル開発用です。インターネットへ直接公開しないでください。
- `FLASK_DEBUG=true` はローカル開発時だけ使用してください。
- 値の単位が異なる指標同士を同じグラフで混在させない設計です。
- APIの更新時期によって、国・指標・年の組み合わせに欠損があります。
- Chart.jsはjsDelivr CDNから読み込むため、グラフ表示時もインターネット接続が必要です。表とCSVは保存済みデータだけで動作します。
- この画面の平均値・ランキングは学習用の単純集計です。政策判断や研究利用では、指標定義、推計方法、欠損、比較可能性を原典で確認してください。
- `.env`、`.venv`、`__pycache__`、SQLite DB、テストキャッシュは `.gitignore` で除外しています。

## 将来的なAWS構成

### このプロジェクトをAWSへ移行する場合の構成案

```text
EventBridge Scheduler
        ↓
Lambda または ECS Fargate（データ取得）
        ↓
World Bank Indicators API
        ↓
S3 Raw（取得JSON）
        ↓
Lambda / Glue（整形・集計）
        ↓
DynamoDB / RDS / S3 + Athena
        ↓
Lambda + API Gateway
        ↓
S3（HTML/CSS/JS）
        ↓
CloudFront
```

### ローカル構成との対応

| 現在 | AWS移行後 | 主な作業 |
|---|---|---|
| cron / 手動CLI | EventBridge Scheduler | スケジュールと失敗通知を設定 |
| `WorldBankClient` | Lambda / ECS Fargate | ハンドラーを薄く追加しサービスを再利用 |
| `DataUpdateService` | Lambda / Step Functions | 長時間化した場合は指標単位に分割 |
| SQLite | DynamoDB / RDS / S3 + Athena | Repository実装を差し替え、データ移行 |
| pandas集計 | Lambda / Glue / Athena | データ量に応じて集計SQL・ETLへ変更 |
| FlaskローカルWeb | Lambda + API Gateway | HTMLとAPIを分離しREST API化 |
| HTML/CSS/JavaScript | S3 + CloudFront | Jinja2依存部分を静的フロントへ移行 |
| Pythonログ | CloudWatch Logs | 個人情報や秘密情報を出さない構造化ログ |
| `.env` | Secrets Manager / Parameter Store | APIキー追加時にIAM最小権限で取得 |
| SQLite内の更新履歴 | DynamoDB / CloudWatch Metrics | 取得成功・失敗件数の監視とアラーム |

### AWS化で追加する作業

1. 保存先のアクセスパターンに合わせてDynamoDB、RDS、Athenaを選定
2. `DataRepository` と同じ責務を持つAWS用Repositoryを実装
3. 生のAPIレスポンスをS3へ保存し、再処理可能にする
4. データ取得Lambdaのタイムアウト、メモリ、同時実行数を設定
5. EventBridge Schedulerから定期実行
6. API Gatewayで検索・集計APIを提供
7. フロントを静的化してS3 + CloudFrontへ配置
8. IAM最小権限、WAF、CloudWatch Alarm、予算アラートを設定
9. Secrets Managerへ秘密情報を移行（必要になった場合のみ）
10. CI/CDでテスト後に開発・本番環境へ段階的に反映

現在の取得、整形、保存、集計、Web表示が分離されているため、最初から全体を書き直さずに段階的に移行できます。
