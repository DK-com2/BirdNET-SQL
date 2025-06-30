# BirdNet-Colab Windows ローカル版

鳥の鳴き声を自動識別するAIシステムのWindowsローカル版です。

## 対象鳥種
- オオタカ (Northern Goshawk)
- サシバ (Gray-faced Buzzard) 
- ミゾゴイ (Japanese Night Heron)
- フクロウ (Ural Owl)
- ヨタカ (Gray Nightjar)

## 🚀 使用方法（簡単2ステップ）

### 1. 初回セットアップ
コマンドプロンプト（cmd）で実行：
```cmd
cd "S:\python\birdnet-colab"
setup.bat
```

### 2. 音声解析
```cmd
start_analysis.bat
```

## 📁 基本的な使い方

1. **音声ファイルの準備**
   - `data\audio\test\` フォルダにMP3またはWAVファイルを配置

2. **解析実行**
   - `start_analysis.bat` をダブルクリック
   - メニューから「1」を選択

3. **結果確認**
   - 同じフォルダに `.csv` ファイルが生成されます

### 結果ファイル例
```csv
Start (s),End (s),Scientific name,Common name,Confidence
0.0,3.0,Accipiter gentilis,Northern Goshawk,0.85
3.0,6.0,,background,0.12
6.0,9.0,Butastur indicus,Gray-faced Buzzard,0.73
```

## 📊 データベースビューアー（新機能）

解析結果をデータベースで管理・確認できます。

### 🎯 簡単な使い方

#### PowerShell
```powershell
.\view_database.ps1
```

#### コマンドプロンプト
```cmd
view_database.bat
```

#### Python直接実行
```cmd
python launch_viewer.py
```

### 🔍 利用可能な機能

1. **セッション管理** - インポートした解析結果の一覧表示
2. **検出結果確認** - 詳細な鳥類検出情報の表示
3. **統計分析** - 検出種数、信頼度、上位検出種の統計
4. **CSVエクスポート** - 結果をCSV形式で再出力
5. **データベース管理** - スキーマやテーブル情報の確認

### 📈 主な表示内容

- **セッション情報**: セッション名、検出数、作成日時
- **検出結果**: 開始/終了時間、学名/一般名、信頼度
- **統計情報**: 総検出数、検出種数、平均信頼度、上位検出種

### 💻 コマンドライン例

```cmd
# 全情報表示
python lib\view_database.py

# 特定セッションの詳細
python lib\view_database.py --detections --stats --session-name "ヨタカ解析結果（修正版）"

# CSVエクスポート
python lib\view_database.py --export "results.csv" --session-name "セッション名"

# セッション一覧のみ
python lib\view_database.py --sessions
```

詳細な使い方は `database_viewer_guide.md` を参照してください。

## 🔧 トラブルシューティング

### PowerShellでエラーが出る場合
コマンドプロンプト（cmd）を使用してください：
1. Windowsキー + R
2. `cmd` と入力してEnter
3. `cd "S:\python\birdnet-colab"` でディレクトリ移動
4. `setup.bat` を実行

### よくあるエラー

**音声ファイル読み込みエラー**
- ffmpegをインストール: https://ffmpeg.org/

**TensorFlowエラー**
```cmd
set CUDA_VISIBLE_DEVICES=""
```

**データベースビューアーの文字化け**
```cmd
chcp 65001
```

## 📂 ファイル構成

- `setup.bat` - 初回セットアップ（これだけ実行すればOK）
- `start_analysis.bat` - 音声解析ツール
- `view_database.bat` - データベースビューアー（CMD用）
- `view_database.ps1` - データベースビューアー（PowerShell用）
- `launch_viewer.py` - データベースビューアー（Python用）
- `requirements.txt` - 必要なパッケージ一覧
- `data\audio\test\` - 音声ファイルを置く場所
- `database\birdnet.db` - 解析結果データベース

## 🛠️ 高度な使用方法

### コマンドライン実行
```cmd
call venv\Scripts\activate.bat
call set_env.bat
task analyze_with_default_model
```

### カスタムモデル作成
詳細は `訓練用プログラム使い方.md` を参照

### データベース直接操作
```cmd
# 結果をデータベースにインポート
python lib\import_results.py "CSVファイルパス" --session "セッション名"

# データベース内容確認
python lib\view_database.py --all
```

---

**迷ったら:**
1. `setup.bat` を実行
2. 音声ファイルを `data\audio\test\` に配置
3. `start_analysis.bat` を実行
4. `view_database.bat` で結果確認
