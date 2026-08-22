# World Data Lens

World Bank Indicators APIの公開データを自動取得し、整形・SQLite保存・集計・可視化する学習用Webアプリケーションです。

ローカル版はPCだけで動作します。APIキーや有料サービスは不要です。

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
Pythonで集計
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
- `src/services/`: 更新処理の順序制御と共通集計
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
│   │   └── aggregation_service.py # SQLite/DynamoDB共通集計
│   ├── aws_database/               # DynamoDB Repository
│   ├── aws_handlers/               # Lambdaの薄い入口
│   ├── aws_runtime/                # Lambda用API取得・S3 Raw保存
│   └── web/
│       ├── routes.py              # HTML・JSON・CSVルート
│       ├── templates/             # Jinja2 HTML
│       └── static/                # CSS・Chart.js用JavaScript
├── infrastructure/                 # AWS CDK v2（Python）
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
- 時系列・地域・ランキング集計
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

# AWS IaC

## IaCとは

Infrastructure as Code（IaC）は、AWSコンソールでリソースを1個ずつ手作業する代わりに、S3、Lambda、DynamoDB、API Gatewayなどの構成をコードで定義する方法です。

このリポジトリではAWS CDK v2とPythonを使い、最終的にCloudFormationテンプレートを生成します。CDKコードをGitで管理することで、構成の差分を確認し、同じ構成を`dev`と`prod`へ再現できます。

CDKコマンドの意味は次のとおりです。

| コマンド | 意味 | AWSへの変更 |
|---|---|---|
| `cdk synth` | CloudFormationテンプレートをローカル生成 | なし |
| `cdk diff` | AWS上の現在構成との差分を確認 | 原則なし（AWSへの読取接続は必要） |
| `cdk deploy` | CloudFormation経由でAWSリソースを作成・更新 | あり |
| `cdk destroy` | CDKスタックを削除 | あり |

今回確認済みなのはテストと`cdk synth`までです。`cdk deploy`、`cdk destroy`、AWSアカウントへの変更は実行していません。

## なぜAWS CDKを採用したか

- Pythonでインフラを記述でき、既存アプリの言語とそろえられる
- S3の非公開設定やIAM grantなどを高水準APIで表現できる
- CDK Assertionsで、deploy前にリソースやセキュリティ設定をテストできる
- 最終的には標準のCloudFormationとしてAWSへ適用される
- contextで`dev`と`prod`を分離できる

Terraformなどでも実現できますが、この学習ではAWSサービスとの統合が強く、既存Python知識を活かせるCDKを選択しています。

## AWS構成図

```text
                         ┌─────────────────────┐
                         │ World Bank          │
                         │ Indicators API      │
                         └──────────▲──────────┘
                                    │ HTTPS GET
                         ┌──────────┴──────────┐
                         │ Acquisition Lambda │
                         └──────▲──────┬───────┘
                                │      │
               ┌────────────────┘      ├──────────────→ S3 Raw
               │                       │                 raw/YYYY/MM/DD/...
┌──────────────┴──────────────┐        └──────────────→ DynamoDB
│ EventBridge Scheduler       │
│ 初期値: 1日1回              │
└─────────────────────────────┘

ユーザー
   │
   ├──── HTTPS ───→ CloudFront ───OAC──→ S3 Frontend（非公開）
   │
   └──── HTTPS ───→ HTTP API ───→ API Lambda ───→ DynamoDB

Acquisition Lambda / API Lambda / HTTP API / Scheduler
                           │
                           └────────────→ CloudWatch Logs・Metrics・Alarms
```

S3 Frontend自体がAPI Gatewayを呼ぶのではありません。S3から配信されたJavaScriptがユーザーのブラウザ上でHTTP APIを呼びます。

## infrastructureディレクトリ

```text
infrastructure/
├── app.py                    # 4スタックの組み立て、Tag設定
├── cdk.json                  # CDK入口とdev初期context
├── requirements.txt          # aws-cdk-lib、constructs
├── requirements-dev.txt      # CDKテスト用pytest、boto3
├── pytest.ini
├── .gitignore                # cdk.out等を除外
├── stacks/
│   ├── config.py             # dev/prod、schedule、通知等の設定
│   ├── data_stack.py         # S3 Raw、DynamoDB
│   ├── backend_stack.py      # Lambda、Scheduler、HTTP API
│   ├── frontend_stack.py     # S3 Frontend、CloudFront OAC
│   └── monitoring_stack.py   # Dashboard、Alarm、任意Budget
└── tests/
    ├── test_data_stack.py
    ├── test_backend_stack.py
    ├── test_frontend_stack.py
    └── test_lambda_adapters.py
```

AWS実行用コードは既存`src/`の処理を共有します。

```text
src/aws_handlers/             Lambdaの薄い入口
src/aws_runtime/              標準ライブラリによるAPI取得＋S3 Raw保存
src/aws_database/             DynamoDB Repository
src/acquisition/parser.py     ローカル/AWS共通の整形
src/services/data_service.py  ローカル/AWS共通の更新処理
src/services/aggregation_service.py
                              SQLite/DynamoDB共通の集計
```

Lambda資産には`src/`だけを含めます。`.env`、SQLite、テスト、仮想環境、Git情報は入りません。Lambdaでは標準ライブラリとランタイム同梱のboto3だけを使うため、Dockerによる依存パッケージのビルドなしでsynthできます。

## 使用AWSサービス

CDKはEventBridge Scheduler、Lambda、S3、DynamoDB、API Gateway、CloudFront、CloudWatch、IAMを中核として定義します。SNSとAWS Budgetsは通知先contextを指定した場合だけ追加します。Secrets Manager、WAF、Route 53、ACMは今回作成しません。

## 各AWSサービスの役割

| サービス | 役割 | 主な設定 |
|---|---|---|
| EventBridge Scheduler | 取得Lambdaを1日1回起動 | contextで式を変更可能、最大2回再試行 |
| Lambda（取得） | API取得、Raw保存、整形、DynamoDB保存 | Python 3.12 ARM64、512MB、5分、同時実行1 |
| S3 Raw | 元APIレスポンスをJSON保存 | 非公開、SSE-S3、HTTPS限定、dev 90日、prod 365日 |
| DynamoDB | 整形済み指標と更新履歴 | オンデマンド、1 GSI、AWS管理暗号化 |
| API Gateway HTTP API | 公開データの読取API | GET 6ルート、CORS、スロットリング、アクセスログ |
| Lambda（API） | DynamoDB検索・集計をJSONで返す | Python 3.12 ARM64、256MB、15秒、読取専用 |
| S3 Frontend | 将来の静的HTML/CSS/JS | 非公開、OAC経由だけ許可 |
| CloudFront | 静的フロントをHTTPS配信 | OAC、HTTPSリダイレクト、最適化キャッシュ、Price Class 100 |
| CloudWatch | ログ、メトリクス、Dashboard、Alarm | ログ14日、標準Alarm 5個 |
| SNS | 任意のAlarmメール通知 | `alarm_email`設定時だけ作成 |
| AWS Budgets | 任意の月額予算通知 | `budget_email`設定時だけ月5 USD初期値で作成 |

HTTP APIを採用した理由は、今回が公開オープンデータの単純な読取APIであり、REST API固有のAPIキー、Usage Plan、リクエスト変換、APIキャッシュを必要としないためです。HTTP APIの方が構成が小さく、一般にリクエスト単価も低くなります。

### APIエンドポイント

| Method / Path | 内容 |
|---|---|
| `GET /health` | APIとDynamoDBの疎通、データ件数 |
| `GET /data` | 検索・条件・並び替え・ページ分割付き一覧 |
| `GET /countries` | 国一覧 |
| `GET /indicators` | 指標一覧 |
| `GET /charts/timeseries` | 指標の時系列集計 |
| `GET /charts/ranking` | 最新年または指定年の国別ランキング |

書込・データ更新用の公開APIは作っていません。データ更新はSchedulerからだけ実行します。

## DynamoDB設計

### 指標データのキー

```text
PK     = COUNTRY#{country_code}#INDICATOR#{indicator_code}
SK     = YEAR#{year:04d}

GSI1PK = INDICATOR#{indicator_code}
GSI1SK = YEAR#{year:04d}#COUNTRY#{country_code}
```

例:

```text
PK     = COUNTRY#JPN#INDICATOR#SP.POP.TOTL
SK     = YEAR#2021
GSI1PK = INDICATOR#SP.POP.TOTL
GSI1SK = YEAR#2021#COUNTRY#JPN
```

SQLiteの`country_code + indicator_code + year`という一意性を、DynamoDBのPK＋SKでそのまま保証します。

| アクセスパターン | 使用キー | 理由 |
|---|---|---|
| 国＋指標＋期間 | PK＋SK範囲Query | 最も直接的で効率的 |
| 国別時系列 | PK＋SK範囲Query | 年順で取得できる |
| 指標＋期間 | GSI1PK＋GSI1SK範囲Query | 全対象国を指標・年で取得 |
| 指標＋年のランキング | GSI1の年prefix Query後、Lambdaで値順に並べる | 現在15か国のため安価。ランキング専用GSIを増やさない |
| 地域・所得・全文検索 | 上限付きScan＋Lambda絞り込み | 学習用の約1,000件規模を優先し、GSIを過剰作成しない |

APIの広域検索は最大5,000件を読み込む小規模用設計です。データ量や利用国が大幅に増えたら、必要な検索条件を確認したうえでGSI、集計済みアイテム、S3＋Athenaなどへ変更してください。OpenSearchは固定費が大きいため今回は使用しません。

更新実行履歴も同じテーブルへ、次の別エンティティとして保存します。

```text
PK = UPDATE_RUN
SK = RUN#{UTC日時}#{ランダムID}
```

Billing Modeは`PAY_PER_REQUEST`です。アクセスが少なく不規則な学習サイトで、常時キャパシティを確保しないためです。

## IAM設計

LambdaごとにCDKが別の実行Roleを作成します。AdministratorAccessや`iam:*`は使用しません。

| 実行主体 | 許可 | 許可しない操作 |
|---|---|---|
| Acquisition Lambda | 対象Raw BucketへのPut、対象TableのGet/BatchGet/Put/BatchWrite/Update、自己ログ | 他Bucket操作、DynamoDB Delete、IAM操作 |
| API Lambda | 対象TableのGet/BatchGet/Query/Scan、自己ログ | S3操作、DynamoDB書込・削除、IAM操作 |
| Scheduler Role | 対象Acquisition LambdaのInvokeだけ | 他Lambda・他サービス操作 |
| CloudFront OAC | 対象Frontend BucketのGetObjectだけ | S3 Public公開、書込・削除 |

`dev`の`cdk destroy`でBucket内を削除するため、CDKが自動削除用のCustom Resourceを作ります。この補助Roleの削除権限は対象Bucketに限定され、Acquisition/API Lambdaには付与されません。

## S3 Raw設計

保存キーは同一データセットの再取得を上書きしない形です。

```text
raw/2026/08/21/SP.POP.TOTL/20260821T010203123456Z.json
raw/2026/08/21/country-metadata/20260821T010200123456Z.json
```

- Public Access Blockを全項目有効化
- SSE-S3暗号化
- `aws:SecureTransport=false`をBucket Policyで拒否
- devは再生成可能な学習データとしてVersioningなし・90日で期限切れ
- prodは誤上書き対策としてVersioningあり・365日で期限切れ・旧Versionは90日
- Bucket名は指定せず、CloudFormationに一意名生成を任せる

## フロントエンドとCloudFront

Frontend BucketはPublic Web Hostingを有効にしません。CloudFront OACだけに`GetObject`を許可します。CloudFrontはHTTPをHTTPSへリダイレクトし、`index.html`をDefault Root Objectにします。

現在の画面はFlask＋Jinja2でサーバー側レンダリングされるため、まだ静的ファイルをFrontend Bucketへ配置していません。CloudFrontとBucketは作成できますが、`index.html`を移行・アップロードするまでは完成画面を表示できません。SPAまたは静的HTMLへの移行は別フェーズです。

独自ドメインは不要で、CloudFrontの標準ドメインで作成できます。独自ドメインを導入する段階でRoute 53、`us-east-1`のACM証明書、CloudFront aliasを追加してください。

## CloudWatchと通知

- Acquisition Lambdaログ: 14日保持
- API Lambdaログ: 14日保持
- HTTP APIアクセスログ: 14日保持
- Lambda Errors、DurationをDashboard表示
- HTTP API 4xx、5xxをDashboard表示
- Scheduler `TargetErrorCount`をDashboard表示
- Acquisition失敗、長時間化、API Lambda Error、HTTP API 5xx、Scheduler失敗のAlarm
- 通知メールはコードへ固定せず、`alarm_email` contextがある場合だけSNSを作成

EventBridge SchedulerはLambdaのような実行ログを直接持たないため、Scheduler失敗はCloudWatch Metricsで検知し、実処理の内容はAcquisition Lambda Logsで確認します。

## Secrets Manager・WAF・Budgetの方針

World Bank APIにはAPIキーが不要なので、Secrets Managerは作成しません。将来`API_KEY`、`API_SECRET`、`TOKEN`が必要になったら、ローカル`.env`からSecrets Managerへ移し、対象Lambdaだけに`secretsmanager:GetSecretValue`を付与します。

WAFも今回は作成しません。一般公開後にアクセスや攻撃リスクが増えた段階で、CloudFrontまたはAPI GatewayへAWS WAF Web ACLとAWS Managed Rulesを追加します。WAFには月額Web ACL・Rule・Request料金があるため、学習段階で無意味に固定費を増やしません。

AWS Budgetは、通知先がない状態では作成しても実用性が低いため初期状態では作りません。次のcontextを指定すると、月5 USD（変更可能）・実績80%のメール通知Budgetを作成します。

```bash
npx --yes aws-cdk@2.1138.0 synth \
  --context budget_email=your-address@example.com \
  --context monthly_budget_usd=5
```

メールアドレスをコマンド履歴やCIログに残したくない場合は、AWS Billing and Cost ManagementのBudgets画面から手動作成してください。

## 開発環境と本番環境

```bash
# 初期値
--context environment=dev

# 将来の本番
--context environment=prod
```

| 設定 | dev | prod |
|---|---|---|
| S3/DynamoDB RemovalPolicy | DESTROY | RETAIN |
| S3自動オブジェクト削除 | 有効 | 無効 |
| S3 Versioning | 無効 | 有効 |
| DynamoDB Point-in-Time Recovery | 無効 | 有効 |
| DynamoDB Deletion Protection | 無効 | 有効 |
| CORS初期値 | `*` | なし。明示設定が必要 |
| Raw保持 | 90日 | 365日 |

全スタックに次のTagを付けます。

```text
Project     = WorldDataLens
Environment = dev または prod
ManagedBy   = CDK
```

設定例:

```bash
npx --yes aws-cdk@2.1138.0 synth \
  --context environment=prod \
  --context schedule_expression='cron(0 2 * * ? *)' \
  --context allowed_origins='https://example.com'
```

prodのCORSはCloudFrontドメインまたは独自ドメインを明示してください。値を指定しなければCORSを有効にしません。

## CDKセットアップ

### 必要条件

- Python 3.12
- Node.jsとnpm（CDK CLI実行用）
- AWS CDK CLI v2
- deploy/diff時のみAWS CLIと有効なAWS認証

リポジトリ共通の仮想環境を使う例です。

```bash
cd codex
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -r infrastructure/requirements-dev.txt
cd infrastructure
```

依頼時に指定された形で、既に仮想環境が有効なら次でも構いません。

```bash
cd infrastructure
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

確認済みの組み合わせは`aws-cdk-lib==2.266.0`、CDK CLI `2.1138.0`です。CDK CLIはライブラリと異なるバージョン体系へ移行しているため、数字が一致しなくても異常ではありません。

## CDKテスト

```bash
cd infrastructure
python -m pytest -q
```

Assertionsで次を確認します。

- S3 Raw、Frontend Bucketの存在・暗号化・Public Access Block
- DynamoDB Table、PAY_PER_REQUEST、PK/SK、GSI
- Lambda 2個、Python 3.12、ARM64
- EventBridge SchedulerとSchedule Group
- HTTP APIとGET 6ルート
- CloudFront DistributionとOAC
- CloudWatch AlarmとDashboard
- AdministratorAccessやデータ削除権限がBackend Roleにないこと
- dev/prodの削除・保護方針
- Lambdaアダプター、S3 Raw保存、DynamoDBキー変換

既存ローカル版のテストはリポジトリ直下で実行します。

```bash
cd ..
python -m pytest -q
```

## CDK Bootstrap

Bootstrapは、CDKがデプロイ資産を一時保存するBucketやRoleを対象AWSアカウント・リージョンへ初回作成する操作です。AWSを変更するため、今回は実行していません。

実際にdeployする直前に、AWS CLIで対象アカウントを確認します。Access KeyやSecret Access KeyをREADME、`.env`、ソースコードへ書かないでください。可能ならIAM Identity Center（SSO）を使用してください。

```bash
aws sts get-caller-identity
aws configure get region
```

東京リージョンの例:

```bash
npx --yes aws-cdk@2.1138.0 bootstrap aws://ACCOUNT_ID/ap-northeast-1
```

`ACCOUNT_ID`は実際の値へ置き換えますが、リポジトリには保存しません。

## cdk synth

AWSリソースを作らず、CloudFormationをローカル生成します。

```bash
cd infrastructure
npx --yes aws-cdk@2.1138.0 synth --context environment=dev
```

生成先は`infrastructure/cdk.out/`です。`cdk.out`はGit管理対象外です。

今回のsynthでは次の4スタックが生成されます。

```text
WorldDataLens-dev-Data
WorldDataLens-dev-Backend
WorldDataLens-dev-Frontend
WorldDataLens-dev-Monitoring
```

## cdk diff

deploy済みCloudFormationとの差分を確認します。AWSへの読取認証が必要です。今回はAWSアカウントへ接続せず、実行していません。

```bash
npx --yes aws-cdk@2.1138.0 diff --all --context environment=dev
```

IAM権限の追加、公開設定、削除・置換される永続データがないかを確認してください。

## cdk deploy

このコマンドは実際に料金が発生し得るAWSリソースを作ります。今回は実行していません。

```bash
npx --yes aws-cdk@2.1138.0 deploy --all \
  --context environment=dev \
  --require-approval broadening
```

deployすると主に次が作られます。

- 非公開S3 Bucket 2個
- DynamoDB Table 1個＋GSI 1個
- Lambda 2個＋個別実行Role・Log Group
- EventBridge Scheduler 1個＋Schedule Group・Invoke Role
- API Gateway HTTP API 1個＋GET 6ルート＋アクセスログ
- CloudFront Distribution 1個＋OAC
- CloudWatch Dashboard 1個＋Alarm 5個
- dev Bucket自動削除用のCDK Custom Resource
- context指定時だけSNS・Email Subscription・AWS Budget

初回deploy直後のDynamoDBは空です。Schedulerの時刻を待つか、AWSコンソールからAcquisition Lambdaのテスト実行を1回行うと、World Bankデータを取得します。

## cdk destroy

devの学習リソースを削除する例です。

```bash
npx --yes aws-cdk@2.1138.0 destroy --all --context environment=dev
```

devはRaw/Frontend Bucket内もCDK補助処理で削除し、DynamoDBも削除します。prodはS3とDynamoDBをRETAINし、Deletion Protectionも使うため、誤削除防止を優先します。prodを完全削除するときは、データの退避、保護解除、残存リソースと料金を個別に確認してください。

## 推定料金

料金はリージョン、レスポンスサイズ、キャッシュ率、Lambda時間、DynamoDBで読み取る項目数、Free Tier・クレジットの残量によって変わります。以下は請求額の保証ではありません。

概算前提:

- 1 PVあたりAPIを3回呼ぶ
- API Lambdaは256MB、平均200ms
- 取得Lambdaは1日1回、512MB、平均10秒
- フロント転送量は1 PVあたり1MB未満
- Rawは1GB未満
- WAF、独自ドメイン、Route 53、NAT Gatewayは含めない
- 標準CloudWatch Alarm 5個

| 利用量 | 月間API呼出の例 | 概算レンジ/月 | 主な変動要因 |
|---|---:|---:|---|
| アクセスほぼなし | 数十～数百 | 約0.5～4 USD | 主にAlarm。Dashboardの無料枠状況で変動 |
| 月1万PV | 約3万 | 約0.5～5 USD | Logs、Alarm、DynamoDB Scan、転送量 |
| 月10万PV | 約30万 | 約1～15 USD | API/Lambda回数、Scan量、CloudFront転送量 |

標準料金の計算式は概ね次です。

```text
API Gateway = APIリクエスト数 × HTTP API単価 + データ転送
Lambda      = リクエスト数 + メモリGB × 実行秒数
DynamoDB    = 読み書きRequest Unit + 保存GB
S3          = 保存GB + PUT/GET回数 + lifecycle処理
CloudFront  = リクエスト数 + 転送GB - キャッシュ/無料枠
CloudWatch  = Logs取込・保存 + Alarm + Dashboard
Scheduler   = 月間実行回数
```

参考となるAWS公式料金ページ:

- [AWS Pricing Calculator](https://calculator.aws/)
- [AWS Lambda料金](https://aws.amazon.com/lambda/pricing/)
- [Amazon API Gateway料金](https://aws.amazon.com/api-gateway/pricing/)
- [Amazon DynamoDB料金](https://aws.amazon.com/dynamodb/pricing/)
- [Amazon S3料金](https://aws.amazon.com/s3/pricing/)
- [Amazon CloudFront料金](https://aws.amazon.com/cloudfront/pricing/)
- [Amazon EventBridge料金](https://aws.amazon.com/eventbridge/pricing/)
- [Amazon CloudWatch料金](https://aws.amazon.com/cloudwatch/pricing/)

公式例では、Lambdaには月100万リクエスト・400,000 GB秒のFree Tier、EventBridge Schedulerには月1,400万回の無料枠があります。API Gateway、CloudFront、CloudWatchの無料枠や新規アカウントクレジットは条件が変わるため、必ず実際のアカウントとリージョンで確認してください。標準Alarmは公式の米国東部例で1メトリクスあたり月0.10 USDなので、本構成の5 Alarmは概ね月0.50 USDが基準ですが、東京リージョンの単価を最終確認してください。

最初のdeploy前に、AWS Pricing Calculatorで`ap-northeast-1`を選び、AWS BudgetとBilling Alarmを設定してください。

## AWSへ実際にデプロイする前の確認事項

1. `git diff`で意図しないアプリ変更・秘密情報がない
2. 既存14テストとinfrastructure 12テストが成功する
3. `cdk synth`が成功する
4. `aws sts get-caller-identity`のAccountとRoleが正しい
5. deploy先Regionが正しい
6. `cdk bootstrap`済み
7. `cdk diff --all`でIAM・削除・置換を確認した
8. devのCORS `*`を理解し、prodでは許可Originを限定した
9. Budgetまたは請求アラートを設定した
10. S3/DynamoDBのdev削除、prod保持方針を確認した
11. World Bankのデータ利用条件・帰属表示を再確認した
12. AWS認証情報をGitへ追加していない

## 今回まだAWS化していない部分

- Flask＋Jinja2画面の静的HTML/SPA化
- Frontend BucketへのHTML/CSS/JavaScriptアップロード
- 静的フロントからHTTP APIを呼ぶJavaScriptへの変更
- 既存SQLiteデータのDynamoDB移行（取得Lambdaで再取得可能）
- 独自ドメイン、Route 53、ACM
- AWS WAF
- 認証・認可（APIは公開オープンデータの読取専用）
- CI/CDによる自動テスト・段階deploy
- 大量データ向けのScan廃止、事前集計、Athena等
- APIキーが必要になった場合のSecrets Manager

現在は「ローカル完成版＋AWS用CDK＋AWS用Handler」が共存しています。次のフェーズでは、まずdevへdeployして取得LambdaとDynamoDB/APIを検証し、その後に画面を静的化してCloudFrontへ接続する順序が安全です。
