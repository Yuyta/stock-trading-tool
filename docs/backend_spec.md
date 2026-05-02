# TradeAlgo Pro バックエンド仕様書

このドキュメントでは、TradeAlgo Pro（株式自動判定ツール）のバックエンド側のディレクトリ構成、および各プログラムファイルの役割について解説します。

## 📁 バックエンド ディレクトリ構成

```text
backend/
├── main.py            # APIサーバーのエントリーポイント (FastAPI)
├── models.py          # Pydanticデータモデル (リクエスト/レスポンス型)
├── db_models.py       # SQLAlchemyデータベースモデル (User, History)
├── database.py        # データベース接続設定 (SQLite/PostgreSQL自動切替)
├── auth_utils.py      # 認証ユーティリティ (JWT, パスワードハッシュ)
├── analyzer.py        # 判定アルゴリズム・スコアリングロジックコア
├── data_fetcher.py    # 外部API（yfinance, J-Quants）データ収集
├── requirements.txt   # Python パッケージ依存関係
├── stock_app.db       # ローカルデータベース (SQLite/自動生成)
└── render.yaml        # Render デプロイ用設定ファイル
```

## 🚀 デプロイとインフラ構成

本アプリケーションは、スケーラビリティとコスト（無料枠）のバランスを考慮し、以下の構成でデプロイ可能です。

- **フロントエンド (Vercel)**: React (Vite) をホスティング。バックエンドURLは環境変数 `VITE_API_URL` で設定。
- **バックエンド (Render)**: FastAPI サーバーをホスティング。`render.yaml` に基づき自動デプロイ。
- **データベース (Supabase)**: マネージド PostgreSQL を使用。Render の無料枠制限を回避しつつ、データの永続化を実現。

## 📄 各ファイルの詳細説明

### 1. `main.py`
**役割：APIサーバーのエントリーポイント**
* FastAPI フレームワークを使用してWebサーバーを立ち上げます。
* **CORS設定**: 環境変数 `CORS_ORIGINS` による許可に加え、正規表現 `https://stock-trading-tool-.*\.vercel\.app` を用いてVercelのプレビュー環境URLを動的に許可します。
* **認証エンドポイント**:
  * `/api/signup`: 新規ユーザー登録。
  * `/api/login`: ログインとJWTトークンの発行。
  * `/api/me`: 現在のログインユーザー情報取得。
  * `/api/user` (DELETE): ユーザーアカウントの削除（退会）。関連する履歴も自動的に削除されます。
* **分析・履歴エンドポイント**:
  * `/api/analyze`: 銘柄判定の実行。
  * `/api/search`: 企業名や銘柄コードからシンボル候補を検索。
    * **優先表示ロジック**: 日本市場（東証、名証、福証、札証）の銘柄を検索結果の最上位に表示。`.T` (東京) などのサフィックスや、取引所名に含まれる「Tokyo, Osaka, Nagoya, Sapporo, Fukuoka」等のキーワードを基に動的に判定・ソートします。
  * `/api/history` (POST): 分析結果の永続化。
  * `/api/history` (GET): 保存された履歴の取得（検索・ソート対応）。
  * `/api/history/{history_id}` (DELETE): 特定の履歴の削除。

### 2. `db_models.py` / `database.py`
**役割：データベース層**
* SQLAlchemy を使用して `stock_trading.db` (SQLite) を操作。
* 詳細なテーブル定義やER図については、**[データベース仕様書](./db_spec.md)** を参照してください。
* **User**: ユーザー名とハッシュ化されたパスワードを保持。
* **AnalysisHistory**: ユーザーに紐付いた分析結果（銘柄、スタイル、判定、スコア、結果の詳細JSON）を保持。

### 3. `auth_utils.py`
**役割：セキュリティ・認証**
* `passlib` (bcrypt) を使用したパスワードのハッシュ化と検証。
* `python-jose` を使用したJWTトークンの生成とデコード。
* `get_current_user` 依存関係により、保護されたエンドポイントへのアクセスを制限。

### 4. `analyzer.py`
**役割：コア分析アルゴリズムとスコアリング**
* 銘柄データを取得し、スタイル（長期/スイング/デイトレ）に合わせた重み付けでスコアリングを実施。
* **Layer 1-6**: マクロ、ファンダメンタル、テクニカル、定性、配当インカムに加え、先回り検知（L6）を統合分析。
* **統合シグナリング**: `Layer 6` と `Layer 3` を中心とした重み付け合算スコアに基づき、ストッパー条件（決算日、200MA等）を最優先適用して最終シグナルを判定。

### 5. `data_fetcher.py`
**役割：データ収集**
* `yfinance`: 株価履歴、ニュース、基本財務データの取得。
* `J-Quants API`: 日本株の高度な財務データの取得（APIキー設定時）。

### 6. `models.py`
**役割：データスキーマ定義**
* フロントエンドとのインターフェースとなるPydanticモデル。
* `AnalysisResult` にはチャートデータから各レイヤーの詳細スコアまで全てが含まれます。

### 7. `requirements.txt`
* APIサーバー (`fastapi`, `uvicorn`)
* データ処理・解析 (`pandas`, `numpy`)
* 外部連携 (`yfinance`, `requests`, `google-generativeai`)
* などのパッケージ依存関係を定義しています。

### 8. `start.bat`
* Windows環境向けに、仮想環境の作成、依存関係のインストール、APIサーバーの起動を自動化するスクリプトです。

## 🧪 ユニットテスト
* **フレームワーク**: `pytest`
* **テスト実行**: `pytest backend/tests`
* **テスト対象**: `analyzer.py` のロジック, `main.py` のエンドポイント
* **CI/CD**: GitHub Actions (`.github/workflows/test.yml`) でプッシュ時に自動実行
