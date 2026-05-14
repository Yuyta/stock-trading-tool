# CORS 動作確認用サンプル

このドキュメントでは、バックエンド（FastAPI / Render）の CORS 設定が正しく動作しているかを確認するためのサンプルと手順を説明します。

## 1. CORS 設定の現状確認

現在の設定（`backend/main.py`）は以下の通りです：

- **環境変数**: `CORS_ORIGINS` (Render ではデフォルト `*`)
- **許可対象**:
  - `CORS_ORIGINS` に含まれるドメイン
  - Vercel のプレビュー環境: `https://stock-trading-tool-.*\.vercel\.app` (正規表現)

---

## 2. 検証サンプル

### 方法A: Python スクリプトによるヘッダー検証 (推奨)
ブラウザを介さず、特定の `Origin` ヘッダーをシミュレートしてサーバーの応答を確認します。正規表現によるマッチングをテストするのに最適です。

**ファイル**: [check_cors.py](../backend/tests/check_cors.py)

**実行方法**:
```powershell
# ローカルで実行中のサーバーをテストする場合
python backend/tests/check_cors.py http://localhost:8000

# デプロイ済みの Render サーバーをテストする場合 (Origin を Vercel のプレビューURLに偽装)
python backend/tests/check_cors.py https://your-api.onrender.com https://stock-trading-tool-abc.vercel.app
```

### 方法B: ブラウザによる実動作検証
実際にブラウザのセキュリティ制限（CORSポリシー）が適用された状態で API にアクセスできるかを確認します。

**ファイル**: [cors_test_browser.html](../backend/tests/cors_test_browser.html)

**使用手順**:
1. この HTML ファイルをブラウザで開きます。
2. `API Base URL` に Render の URL または `http://localhost:8000` を入力します。
3. `API 接続テスト実行` をクリックします。

---

## 3. Render での CORS 確認ポイント

Render のダッシュボードで以下の環境変数が正しく設定されているか確認してください。

| 環境変数名 | 推奨値 | 備考 |
| :--- | :--- | :--- |
| `CORS_ORIGINS` | `https://your-frontend.vercel.app` | 本番ドメインをカンマ区切りで指定 |

> [!TIP]
> 開発中は `*` に設定することで全てのオリジンを許可できますが、本番環境ではセキュリティのため特定のドメインに制限することを推奨します。

> [!IMPORTANT]
> Render の「Static Site」機能でヘッダーを設定している場合、FastAPI 側の設定と競合する可能性があります。本プロジェクトは Web Service (Python) であるため、ヘッダーは `main.py` の `CORSMiddleware` で管理するのが正解です。
