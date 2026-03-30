# TradeAlgo Pro バックエンド仕様書

このドキュメントでは、TradeAlgo Pro（株式自動判定ツール）のバックエンド側のディレクトリ構成、および各プログラムファイルの役割について解説します。

## 📁 バックエンド ディレクトリ構成

```text
backend/
├── main.py            # APIサーバーのエントリーポイント (FastAPI)
├── models.py          # Pydanticデータモデル (リクエスト/レスポンス型)
├── db_models.py       # SQLAlchemyデータベースモデル (User, History)
├── database.py        # データベース接続設定 (SQLite)
├── auth_utils.py      # 認証ユーティリティ (JWT, パスワードハッシュ)
├── analyzer.py        # 判定アルゴリズム・スコアリングロジックコア
├── data_fetcher.py    # 外部API（yfinance, J-Quants）データ収集
├── requirements.txt   # Python パッケージ依存関係
└── stock_trading.db   # ローカルデータベース (自動生成)
```

## 📄 各ファイルの詳細説明

### 1. `main.py`
**役割：APIサーバーのエントリーポイント**
* FastAPI フレームワークを使用してWebサーバーを立ち上げます。
* **認証エンドポイント**:
  * `/api/signup`: 新規ユーザー登録。
  * `/api/login`: ログインとJWTトークンの発行。
  * `/api/me`: 現在のログインユーザー情報取得。
* **分析・履歴エンドポイント**:
  * `/api/analyze`: 銘柄判定の実行。
  * `/api/history` (POST): 分析結果の永続化。
  * `/api/history` (GET): 保存された履歴の取得（検索・ソート対応）。

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
* **Layer 1-5**: マクロ、ファンダメンタル、テクニカル、定性、配当インカムの各レイヤーを独立して分析。
* マクロ環境（VIX等）に基づき、最終的なシグナルを動的に調整。

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
