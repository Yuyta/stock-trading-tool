# TradeAlgo Pro フロントエンド仕様書

このドキュメントでは、TradeAlgo Pro（株式自動判定ツール）のフロントエンド側（React）のディレクトリ構成、および各プログラムファイルの役割について解説します。

## 📁 フロントエンド ディレクトリ構成

```text
src/
├── App.tsx             # メインアプリケーションコンポーネント (UI・ロジック統括)
├── History.tsx         # 分析履歴表示コンポーネント (検索・ソート機能)
├── SettingsModal.tsx   # APIキー設定（LocalStorage保存）モーダル
├── AuthModal.tsx       # ログイン・新規登録用モーダル
├── AuthContext.tsx     # 認証状態（JWTトークン・ユーザー情報）管理
├── types.ts            # TypeScript型定義
├── App.css             # グローバルおよびコンポーネント用スタイルシート
├── index.css           # デザインシステム、カラー、グラスモーフィズム定義
├── main.tsx            # Reactアプリケーションの起動・マウントポイント
└── vite-env.d.ts       # Vite用型定義
```

## 📄 各ファイルの詳細説明

### 1. `App.tsx`
**役割：メインのUI表示とアプリケーションの状態管理**
* ユーザーインターフェースの中核であり、以下の機能を持ちます：
  * **ナビゲーション**: ハンバーガーメニューによる「分析画面」「履歴画面」「設定」の切り替え。
  * **分析フォーム**: 銘柄コード、時間軸、トレードスタイル（長期/スイング/デイトレ）の入力。
  * **結果の表示**: バックエンドから返ってきた `AnalysisResult` を可視化。
    * マクロ、ファンダメンタル、テクニカル、定性、配当・インカムの各セクション。
  * **チャート機能**: `recharts` を使用。EMAやボリンジャーバンドなどのテクニカル指標を動的に表示。
  * **自動保存**: ログイン時は分析完了後にバックエンドの `/api/history` へ自動で結果を保存。

### 2. `History.tsx`
**役割：保存された分析履歴の閲覧・検索**
* `/api/history` (GET) からデータを取得し、リスト形式で表示。
* **検索**: 銘柄コードによるフィルタリング。
* **ソート**: 分析日時、銘柄名での並び替え。
* **詳細復元**: 過去の判定結果をクリックすることで、`App.tsx` の表示状態を当時のデータで上書きし、詳細を再現。

### 3. `AuthContext.tsx` / `AuthModal.tsx`
**役割：ユーザー認証の管理**
* JWT（JSON Web Token）を `localStorage` に保持し、APIリクエストの `Authorization` ヘッダーに自動付与。
* ログイン、新規登録、ログアウトのUIとロジックを提供。

### 4. `SettingsModal.tsx`
**役割：APIキーの設定管理**
* J-Quants API連携用リフレッシュトークンとGoogle Gemini APIキーを管理。

### 5. `types.ts`
**役割：型定義**
* `AnalysisResult`, `AnalysisHistory`, `User`, `MacroResult` 等のインターフェース定義。
* バックエンドのPydanticモデルと完全に対応。

### 6. `index.css`
**役割：デザイン基盤**
* 全体のカラーパレット (Vibrant Green, Dark Slate, Glass effect)。
* アニメーション（slide-in, fade-in, spin）の定義。
* レスポンシブ設計のためのメディアクエリ。
