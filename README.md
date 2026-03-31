# TradeAlgo Pro 📈
AI 搭載型 多角化株式分析ツール

TradeAlgo Pro は、Gemini AI とマクロ経済データ、企業の財務データ（J-Quants / yfinance）、およびテクニカル指標を組み合わせた三層構造の株式分析プラットフォームです。

---

## 主な機能
- **多層分析エンジン**:
  - **Layer 1 (マクロ)**: VIX、金利、為替、セクターローテーション等の市場リスク評価。
  - **Layer 2 (ファンダメンタル)**: PER、PBR、ROE、および営業利益成長率に基づく健全性評価。
  - **Layer 3 (テクニカル)**: EMA、RSI、MACD、ボリンジャーバンド、VWAP、出来高比による売買タイミング判定。
  - **Layer 6 (先回り検知/アキュムレーション)**: ダイバージェンス、BBスクイーズ、出来高増加トレンド等による「上昇前」の蓄積状態をスコアリング。
- **AI 定性分析**: Gemini AI による最新ニュースの感情分析と投資判断の要約。
- **マルチ投資スタイル**:
  - **長期（配当・インカム）**: 高利回り・割安性を重視した判定。
  - **スイング（中長期）**: 上昇トレンドとファンダメンタルのバランスを重視。
  - **デイトレ（短期）**: ボラティリティと需給重視のリアルタイム分析。
- **履歴管理・検索**: 過去の分析結果を自動保存し、ソートや検索が可能。
- **ユーザー認証**: 履歴の永続化と他デバイス間での同期。

---

## 技術スタック
- **フロントエンド**: React (TypeScript), Vite, Recharts, Lucide React
- **バックエンド**: FastAPI (Python), SQLAlchemy, Pydantic
- **データベース**: SQLite (Local) / PostgreSQL (Supabase for Production)
- **外部 API**: Gemini API, J-Quants API, yfinance

---

## 分析の仕組み
TradeAlgo Pro は以下の 5 つの詳細レイヤーで銘柄を多角的に評価します。

1.  **マクロ環境レイヤー (Market Risk)**
    - VIX指数による市場のパニック度判定。
    - 米10年債利回り、ドル円、原油・金価格（コモディティ）のボラティリティ監視。
    - 主要指数（日経・NASDAQ）の75日移動平均線によるトレンド確認。
2.  **ファンダメンタルレイヤー (Fundamental Score)**
    - 収益性・成長性・割安性を数値化。
    - ROE、営業利益成長率、PER/PBR の適正度をスタイル別に評価。
3.  **テクニカルレイヤー (Technical Momentum)**
    - EMA（5/20/75/200日）、RSI、MACD、ボリンジャーバンドを使用。
    - 出来高比（RVOL）による資金流入の検知。
4.  **定性・ニュースレイヤー (Sentiment Analysis)**
    - 最新ニュース 10 件を解析。
    - Gemini AI が投資家の感情を 0〜10 スコアで算出。
5.  **先回り検知レイヤー (Accumulation Detection)**
    - アキュムレーション（蓄積）状態を 6 要素で複合判定。
    - 「これから上がりそう」な銘柄を 0〜40 点の独立スコアで評価。

---

## 投資スタイルと推奨設定
自身の投資戦略に合わせてスタイルを選択してください：

- **長期 (配当・インカム)**:
  - **重視項目**: 配当利回り、配当性向、グレアム指数、ROE
  - **推奨時間軸**: `1d`（日足）以上
- **中長期投資 (スイング)**:
  - **重視項目**: 上昇トレンド、決算成長性、MACD
  - **推奨時間軸**: `1d`（日足）
- **短期・デイトレード**:
  - **重視項目**: RVOL（出来高）、ボラティリティ、VWAP、RSI
  - **推奨時間軸**: `5m`, `15m`（分足）
  - ※ 財務分析はスコアから除外され、需給に特化した判定を行います。

---

## API 設定と分析精度
アプリ内の「設定」から以下のキーを登録することで、分析の信頼性が向上します。

- **Gemini API キー (推奨)**:
  - 未設定の場合、キーワード照合による簡易ニュース分析に切り替わります。
- **J-Quants リフレッシュトークン**:
  - 日本株の正確な財務データ取得に使用します。
  - 未設定の場合、yfinance からの取得を試みますが精度が低下する場合があります。

---

## 開発環境のセットアップ (Local)

### 1. バックエンドの準備
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### 2. フロントエンドの準備
```bash
npm install
npm run dev
```
ブラウザで `http://localhost:5173` にアクセスします。

---

## 本番環境へのデプロイガイド

### アーキテクチャ
- **フロントエンド**: **Vercel**
- **バックエンド**: **Render**
- **データベース**: **Supabase (PostgreSQL)**

### 0. データベースの準備 (Supabase)
1. [Supabase](https://supabase.com/) でプロジェクトを作成。
2. **Project Settings > Database** にて **Transaction モード (Port 6543)** の URI をコピー。
3. パスワードを埋めて `DATABASE_URL` として控える。

### 1. バックエンドのデプロイ (Render)
1. [Render](https://render.com/) で **New > Web Service** を作成。
2. **Root Directory**: `backend` に設定。
3. **Build Command**: `pip install -r requirements.txt`
4. **Environment Variables**:
   - `DATABASE_URL`: Supabase の接続先 URI
   - `CORS_ORIGINS`: Vercel のデプロイ先 URL (例: `https://your-app.vercel.app`)

### 2. フロントエンドのデプロイ (Vercel)
1. [Vercel](https://vercel.com/) にリポジトリを接続。
2. **Environment Variables**:
   - `VITE_API_URL`: Render のサービス URL

---

## セキュリティとAPIキー
Gemini API キーおよび J-Quants トークンは、アプリ内の **設定（Settings）** からユーザーがそれぞれ入力します。これらのキーは**ユーザーのブラウザ (localStorage)** にのみ保存され、各分析リクエストの際にヘッダーとして送信されます。サーバー側での永続的な保存は行われません。

---

## 免責事項
本アプリケーションが提供する情報は投資勧誘を目的としたものではありません。投資に関する最終決定は、利用者ご自身の判断において行われるようお願いいたします。ツールの判定はデータに基づく推測であり、利益を保証するものではありません。
