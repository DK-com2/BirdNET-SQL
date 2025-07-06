# BirdNet Streamlit Viewer セットアップガイド

## 📋 概要

BirdNet-winプロジェクト用のモダンなStreamlit Webアプリケーションです。音声解析の実行とデータベース結果の表示・分析を行うことができます。

## 🚀 クイックセットアップ

### 1. 前提条件の確認

- Python 3.8以上がインストールされている
- BirdNet-winプロジェクトが正常に動作している
- 仮想環境の利用を推奨

### 2. 仮想環境の作成と有効化（推奨）

```bash
# BirdNet-winのルートディレクトリに移動
cd S:\python\BirdNet-win

# 仮想環境作成
python -m venv streamlit_env

# 仮想環境有効化 (Windows)
streamlit_env\Scripts\activate

# 仮想環境有効化 (Linux/Mac)
source streamlit_env/bin/activate
```

### 3. 依存関係のインストール

```bash
# streamlit_viewerディレクトリに移動
cd streamlit_viewer

# 必要なライブラリをインストール
pip install -r requirements.txt
```

### 4. アプリケーションの起動

```bash
# Streamlitアプリを起動
streamlit run app.py
```

### 5. ブラウザでアクセス

ブラウザが自動的に開きます（通常は `http://localhost:8501`）

## 🔧 詳細設定

### データベース設定

アプリケーションは以下の順序でデータベースファイルを検索します：

1. `../database/result.db` (デフォルト)
2. `../database/birdnet_simple.db`
3. `../database/birdnet.db`
4. `../database/birds.db`

カスタムパスを使用する場合は、`app.py`の`get_database_path()`関数を修正してください。

### 音声処理の有効化（オプション）

音声再生・分析機能を使用する場合は、追加ライブラリをインストール：

```bash
pip install librosa soundfile
```

### ディレクトリ構造の確認

正常に動作するために、以下のディレクトリ構造が必要です：

```
BirdNet-win/
├── streamlit_viewer/           # このアプリケーション
│   ├── app.py                 # メインアプリケーション
│   ├── analyzer.py            # 解析モジュール
│   ├── requirements.txt       # 依存関係
│   └── utils/                 # ユーティリティ
├── database/                  # データベースディレクトリ
│   ├── result.db             # メインデータベース
│   └── audio/                # 音声ファイル
│       ├── inbox/            # 解析待ち
│       ├── completed/        # 解析完了
│       └── failed/           # 解析失敗
├── lib/                      # BirdNetライブラリ
└── model/                    # カスタムモデル
```

## 🎯 主な機能

### 解析実行ページ（🚀）

- **音声ファイル解析**: inboxフォルダ内の音声ファイルを自動検出
- **モデル選択**: 標準BirdNetまたはカスタムモデル
- **セッション管理**: 解析結果の識別管理
- **リアルタイム進捗表示**: 解析の進行状況をリアルタイム表示

### データベース表示ページ（📊）

- **検出結果表示**: データベースから検出結果を取得・表示
- **統計情報**: 種数、検出数、信頼度などの統計
- **データフィルタリング**: 件数制限やデバッグモード
- **データエクスポート**: CSV形式でのダウンロード

### システム情報サイドバー

- **音声ファイル数**: 処理待ちファイルの確認
- **カスタムモデル数**: 利用可能モデルの確認
- **データベース接続状況**: DB接続とレコード数の確認

## 🐛 トラブルシューティング

### よくある問題と解決方法

#### 1. データベース接続エラー

```
❌ データベースに接続できませんでした
```

**解決方法:**
- データベースファイル（result.db）の存在確認
- ファイル権限の確認
- パス設定の確認

#### 2. 音声ファイルが見つからない

```
🚨 音声ファイルが見つかりません
```

**解決方法:**
- `database/audio/inbox/` フォルダの存在確認
- 対応音声形式の確認（MP3, WAV, FLAC, M4A）
- ファイル権限の確認

#### 3. モジュールインポートエラー

```
解析モジュールの読み込みに失敗
```

**解決方法:**
- 仮想環境の有効化確認
- 依存関係の再インストール: `pip install -r requirements.txt`
- Python パスの確認

#### 4. Streamlit起動エラー

```
command not found: streamlit
```

**解決方法:**
- 仮想環境の有効化: `streamlit_env\Scripts\activate`
- Streamlitの再インストール: `pip install streamlit`

### デバッグモード

問題の詳細を確認するには：

1. データベースページで「🔧 デバッグモード」を有効化
2. ブラウザの開発者ツールでコンソールエラーを確認
3. Streamlitターミナル出力を確認

### ログの確認

```bash
# 詳細ログ付きで起動
streamlit run app.py --logger.level=debug

# 開発者モードで起動（ファイル変更時自動リロード）
streamlit run app.py --server.runOnSave=true
```

## 📚 使用ライブラリ

### 必須ライブラリ

- **streamlit**: Webアプリケーションフレームワーク
- **pandas**: データ操作・分析
- **numpy**: 数値計算

### オプションライブラリ

- **plotly**: インタラクティブな可視化
- **matplotlib**: 基本的な可視化
- **librosa**: 音声処理・分析
- **soundfile**: 音声ファイル読み書き
- **scipy**: 科学計算

## 🔄 アップデート手順

新しいバージョンに更新する場合：

1. アプリケーションを停止（Ctrl+C）
2. 最新コードをダウンロード
3. 依存関係を更新: `pip install -r requirements.txt --upgrade`
4. アプリケーションを再起動: `streamlit run app.py`

## 🤝 サポート

問題が解決しない場合：

1. エラーメッセージとスクリーンショットを準備
2. 環境情報を確認（Python version, OS, etc.）
3. GitHubのIssuesで報告

## 📄 ライセンス

このプロジェクトはBirdNet-winプロジェクトの一部として開発されています。

---

**クイックコマンド集:**

```bash
# 環境構築から起動まで（ワンライナー）
cd S:\python\BirdNet-win && python -m venv streamlit_env && streamlit_env\Scripts\activate && cd streamlit_viewer && pip install -r requirements.txt && streamlit run app.py

# 依存関係チェック
python -c "import streamlit, pandas, numpy; print('✅ 基本ライブラリOK')"

# 音声処理チェック
python -c "import librosa, soundfile; print('✅ 音声処理OK')" 2>/dev/null || echo "⚠️ 音声処理ライブラリなし"

# データベースチェック
python -c "from pathlib import Path; print('✅ DB存在' if Path('../database/result.db').exists() else '❌ DB不存在')"
```
