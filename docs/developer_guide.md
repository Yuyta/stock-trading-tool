# 開発者ガイド：Vercel & Render デプロイ

このドキュメントでは、TradeAlgo Pro を本番環境（フロントエンド：Vercel、バックエンド：Render）にデプロイする手順を説明します。

---

## アーキテクチャ構成
- **フロントエンド**: Vite + React (TypeScript) → Vercel
- **バックエンド**: FastAPI (Python) → Render

---

## 1. バックエンドのデプロイ (Render)

バックエンドは `backend` ディレクトリをルートとしてデプロイします。

### 手順
1. [Render](https://render.com/) にログインし、**New > Web Service** を選択します。
2. GitHub リポジトリを接続します。
3. 以下の設定を入力します：
   - **Name**: `trade-algo-pro-api` (任意)
   - **Runtime**: `Python 3`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Environment Variables** に以下を設定します：
   - `CORS_ORIGINS`: Vercel のデプロイ先URL（例: `https://your-app.vercel.app`）
     ※ 開発中は `*` に設定しても動作しますが、セキュリティ上制限を推奨します。

---

## 2. フロントエンドのデプロイ (Vercel)

フロントエンドはリポジトリのルートを基準にデプロイします。

### 手順
1. [Vercel](https://vercel.com/) にログインし、**Add New > Project** を選択します。
2. GitHub リポジトリをインポートします。
3. **Framework Preset** で `Vite` が選択されていることを確認します。
4. **Environment Variables** に以下を設定します：
   - `VITE_API_URL`: Render の Web Service URL（例: `https://trade-algo-pro-api.onrender.com`）
     ※ 末尾に `/` を入れないでください。
5. **Deploy** をクリックします。

---

## 3. 本番環境での注意点

### APIキーの管理
Gemini API キーおよび J-Quants Refresh Token は、バックエンド側ではなく**フロントエンドの localStorage** に保存され、リクエストごとに送信されます。
- これにより、ホスティング環境側に機密情報を保存する必要がなく、各ユーザーが自身のキーを使用できます。

### 通信制限
Render の無料プラン（Free tier）を使用している場合、一定期間アクセスがないとインスタンスがスリープします。最初の分析リクエスト時に時間がかかることがありますが、これは正常な挙動です。

---

## 4. 開発環境 (Local) の起動方法

ローカルで開発を行う際の起動手順です。

### バックエンドの起動
1. ターミナルで `backend/` ディレクトリに移動します。
2. 仮想環境を有効化します。
   - Windows: `.\.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`
3. サーバーを起動します:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### フロントエンドの起動
1. プロジェクトのルートディレクトリで新しいターミナルを開きます。
2. 開発用サーバーを起動します:
   ```bash
   npm run dev
   ```
3. 表示されたURL（通常は `http://localhost:5173`）にブラウザでアクセスします。

> [!TIP]
> **ローカル開発時のAPI通信**:
> `VITE_API_URL` を設定せずに起動した場合、`vite.config.ts` のプロキシ設定（`localhost:8000`）が自動的に使用されます。
