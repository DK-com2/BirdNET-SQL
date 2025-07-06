# BirdNet Database Viewer (Streamlit)

BirdNetの検出結果を検索・再生・分析するWebアプリケーション

## 🚀 クイックスタート

### 1. 仮想環境構築（推奨）
```bash
# BirdNet-winのルートディレクトリで実行
cd S:\python\BirdNet-win

# 仮想環境作成
python -m venv streamlit_env

# 仮想環境有効化
# Windows
streamlit_env\Scripts\activate
# Linux/Mac  
source streamlit_env/bin/activate
```

### 2. 依存関係インストール
```bash
cd streamlit_viewer
pip install -r requirements.txt
```

### 3. アプリケーション起動
```bash
streamlit run app.py
```

### 4. ブラウザでアクセス
自動的にブラウザが開きます（通常 `http://localhost:8501`）

## 🌟 主な機能

### 📊 データベース検索・フィルタリング
- **種名検索**: 日本語・英語・学名での検索
- **信頼度フィルタ**: スライダーによる信頼度範囲指定
- **種選択**: 特定の鳥種のみに絞り込み
- **場所フィルタ**: 録音場所による絞り込み
- **件数制限**: 表示件数の制限設定

### 🎵 音声再生・分析
- **セグメント再生**: 検出された時間範囲の音声再生
- **音声正規化**: レベル調整による聞きやすさ向上
- **フェード処理**: 開始・終了時のスムーズな再生
- **波形表示**: リアルタイムの音声波形可視化
- **スペクトログラム**: インタラクティブな周波数分析

### 📈 統計分析・可視化
- **信頼度分布**: ヒストグラムによる信頼度の分布表示
- **種別統計**: 検出数・平均信頼度などの種別統計
- **時系列分析**: 日別・時間別の検出推移
- **散布図分析**: 信頼度と時間の相関分析

### 📥 データエクスポート
- **CSV出力**: フィルタリング結果のCSVダウンロード
- **条件保存**: 検索条件の保存・再利用

## 🏗️ プロジェクト構造

```
streamlit_viewer/
├── app.py                  # メインアプリケーション
├── requirements.txt        # 依存関係
├── utils/                  # ユーティリティモジュール
│   ├── __init__.py
│   ├── db_utils.py        # データベース操作
│   ├── audio_utils.py     # 音声処理
│   └── plot_utils.py      # 可視化
└── README.md              # このファイル
```

## 🔧 設定・カスタマイズ

### データベースパス
デフォルトでは `../database/result.db` を参照します。
異なる場所のデータベースを使用する場合は、`utils/db_utils.py` の `get_default_database_path()` を修正してください。

### 音声処理パラメータ
`utils/audio_utils.py` で以下の設定を調整できます：
- 正規化レベル（デフォルト: -20dB）
- フェード時間（デフォルト: 0.1秒）
- サンプリングレート設定

### 表示設定
`app.py` の以下の部分で表示をカスタマイズ：
- 最大表示件数の選択肢
- ソート項目の設定
- グラフの色設定

## 🐛 トラブルシューティング

### データベース接続エラー
```
❌ データベースに接続できませんでした
```
**解決方法:**
1. `../database/result.db` ファイルの存在確認
2. ファイルの読み取り権限確認
3. SQLiteファイルの破損チェック

### 音声ファイルエラー
```
❌ 音声ファイルにアクセスできません
```
**解決方法:**
1. データベース内の `file_path` が正しいか確認
2. 音声ファイルの存在確認
3. ファイルの読み取り権限確認
4. 対応音声形式の確認（WAV, MP3, FLAC, AAC, OGG, M4A）

### ライブラリインストールエラー
```
ERROR: Could not install packages
```
**解決方法:**
1. Python バージョン確認（3.8+ 推奨）
2. pip の最新化: `pip install --upgrade pip`
3. 個別インストール: `pip install streamlit plotly librosa`

### メモリエラー
```
MemoryError: Unable to allocate array
```
**解決方法:**
1. 表示件数制限を小さくする
2. 信頼度フィルタで結果を絞り込む
3. 大容量音声ファイルの分割

### Streamlit起動エラー
```
command not found: streamlit
```
**解決方法:**
1. 仮想環境の有効化確認
2. Streamlitの再インストール: `pip install streamlit`
3. パスの確認: `which streamlit`

## 📚 使用ライブラリ

| ライブラリ | バージョン | 用途 |
|-----------|------------|------|
| streamlit | >=1.28.0 | Webアプリフレームワーク |
| plotly | >=5.15.0 | インタラクティブ可視化 |
| librosa | >=0.10.0 | 音声処理・分析 |
| soundfile | >=0.12.0 | 音声ファイル読み書き |
| pandas | >=1.5.0 | データ操作 |
| numpy | >=1.21.0 | 数値計算 |
| matplotlib | >=3.5.0 | 基本的な可視化 |
| scipy | >=1.9.0 | 科学計算 |

## 🎯 使用例

### 基本的な検索
1. サイドバーで「シジュウカラ」と検索
2. 信頼度を0.5以上に設定
3. 「🔍 検索実行」をクリック
4. 結果テーブルから興味のある検出を選択

### 音声分析ワークフロー
1. 検索結果から音声を選択
2. 「🎵 音声プレイヤー」タブに移動
3. 音声処理オプションを設定
4. 「🔄 音声を読み込み」をクリック
5. 波形・スペクトログラムで分析

### データエクスポート
1. 必要な条件でフィルタリング
2. 「🔍 検索結果」タブで結果確認
3. 「📥 CSV ダウンロード」でエクスポート

## 🚧 開発者向け情報

### カスタム機能の追加
新しい機能を追加する場合：

1. **新しい分析機能**: `utils/plot_utils.py` に関数追加
2. **音声処理機能**: `utils/audio_utils.py` に関数追加
3. **データベース機能**: `utils/db_utils.py` に関数追加
4. **UI機能**: `app.py` に新しい関数・タブ追加

### デバッグモード
```bash
# デバッグ情報を表示
streamlit run app.py --logger.level=debug

# 開発者モードで起動
streamlit run app.py --server.runOnSave=true
```

### テスト
```bash
# 基本動作テスト
python -c "from utils.db_utils import load_database; print('DB OK:', load_database() is not None)"

# 音声処理テスト
python -c "from utils.audio_utils import load_audio_segment; print('Audio OK')"
```

## 🤝 コントリビューション

バグ報告や機能提案は Issues で受け付けています。

### 開発環境セットアップ
```bash
# 開発用依存関係インストール
pip install -r requirements.txt
pip install black flake8 pytest  # 開発ツール

# コード整形
black .

# リンターチェック
flake8 .
```

## 📄 ライセンス

このプロジェクトは BirdNet-win プロジェクトの一部として開発されています。

---

## 🆘 サポート

問題が解決しない場合：

1. **ログ確認**: ブラウザの開発者ツールでエラーログ確認
2. **環境確認**: Python バージョン、ライブラリバージョン確認
3. **再起動**: Streamlit サーバーの再起動
4. **クリーンインストール**: 仮想環境の再作成

**トラブル時のチェックリスト:**
- [ ] Python 3.8+ がインストールされている
- [ ] 仮想環境が有効化されている
- [ ] 必要なライブラリがインストールされている
- [ ] データベースファイル（result.db）が存在する
- [ ] 音声ファイルにアクセス可能
- [ ] ポート8501が利用可能

**高速セットアップコマンド:**
```bash
# ワンライナーセットアップ
cd S:\python\BirdNet-win\streamlit_viewer && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && streamlit run app.py
```
