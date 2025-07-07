# BirdNet Audio Analysis Tool

鳥の鳴き声を自動識別するAIシステムのWindowsローカル版です。対話型メニューと自動化の両方に対応しています。

## 🚀 クイックスタート

### 1. 環境構築（初回のみ）

**コマンドプロンプト（CMD）の場合:**
```cmd
# 仮想環境作成・有効化
python -m venv venv
venv\Scripts\activate

# パッケージインストール
pip install -r requirements.txt
```

**PowerShellの場合:**
```powershell
# 仮想環境作成・有効化
python -m venv venv
venv\Scripts\Activate.ps1

# パッケージインストール
pip install -r requirements.txt
```

> **PowerShellでエラーが出る場合:**
> ```powershell
> # 実行ポリシーを一時的に変更
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> またはコマンドプロンプト（CMD）を使用してください。

**仮想環境を使わない場合:**
```cmd
# 直接インストール（非推奨）
pip install -r requirements.txt
```

### 2. 音声解析の実行
```cmd
python start_analysis.py
```

## 📖 使用方法

### 対話モード（メニュー形式）

引数なしで実行すると、従来通りのメニューが表示されます：

```cmd
python start_analysis.py
```

```
==================================================
[BirdNet] Audio Analysis Tool
==================================================

[FILES] 音声ファイル:
   - sample_audio.wav
   - morning_birds.mp3

[MODELS] 利用可能なモデル:
   - default (BirdNET標準モデル)
   - custom_model_1 (カスタムモデル)

[MENU] オプション:
  [1] デフォルトモデルで解析 + DB保存
  [2] カスタムモデルで解析 + DB保存
  [3] inboxフォルダを開く
  [4] 解析結果を表示
  [0] 終了

オプションを選択してください (0-4):
```

### 自動モード（コマンドライン）

自動化やスケジュール実行に適したモードです：

#### 基本的な使い方

```bash
# デフォルトモデルで解析
python start_analysis.py --auto --action analyze --model default

# カスタムモデルで解析
python start_analysis.py --auto --action analyze --model custom_model_1

# 解析結果を表示
python start_analysis.py --auto --action view_results

# inboxフォルダを開く
python start_analysis.py --auto --action open_inbox
```

#### オプション指定

```bash
# セッション名を指定
python start_analysis.py --auto --action analyze --model default --session "morning_birds"

# 静謐モード（ログを最小限に）
python start_analysis.py --auto --action analyze --model default --quiet

# 複合例
python start_analysis.py --auto --action analyze --model custom_model_1 --session "evening_detection" --quiet
```

## 📋 コマンドライン引数

| 引数 | 説明 | 必須 | デフォルト |
|------|------|------|------------|
| `--auto` | 自動モードを有効化 | ◯（自動モード時） | - |
| `--action` | 実行する処理<br>`analyze`, `view_results`, `open_inbox` | ◯（自動モード時） | - |
| `--model` | 使用するモデル名 | - | `default` |
| `--session` | セッション名 | - | 自動生成 |
| `--quiet` | 静謐モード | - | `False` |

## 🗂️ ファイル構成

```
S:\python\BirdNet-win\
├── start_analysis.py          # メイン解析ツール
├── setup.bat                  # 初回セットアップ
├── database/
│   ├── audio/
│   │   ├── inbox/             # 解析対象音声ファイル
│   │   ├── completed/         # 解析完了ファイル
│   │   └── failed/            # 解析失敗ファイル
│   ├── analysis_results/      # CSV解析結果
│   └── result.db             # SQLiteデータベース
├── model/                     # カスタムモデル
├── lib/                      # ライブラリ
│   ├── birdnet/              # BirdNet解析エンジン
│   └── db/                   # データベース操作
└── venv/                     # Python仮想環境
```

## 🎯 音声ファイルの配置

解析したい音声ファイルを以下のフォルダに配置してください：

```
database/audio/inbox/
```

対応形式：`.wav`, `.mp3`, `.flac`, `.m4a`

## 📊 セッション名の生成規則

### 自動生成される場合

セッション名を省略すると、以下の形式で自動生成されます：

```
auto_{model_name}_{timestamp}
```

**例：**
- `auto_default_20250707_143022`
- `auto_custom_model_1_20250707_090015`

### タイムスタンプ形式
- **年月日**: `YYYYMMDD`
- **時分秒**: `HHMMSS`
- **区切り**: アンダースコア `_`

## 🔄 自動化での活用

### Windows タスクスケジューラー

```batch
# scheduled_analysis.bat
@echo off
cd "S:\python\BirdNet-win"
call venv\Scripts\activate

echo [%date% %time%] 自動解析開始 >> logs\auto.log

python start_analysis.py --auto --action analyze --model default --quiet
set RESULT=%ERRORLEVEL%

if %RESULT% EQU 0 (
    echo [%date% %time%] 解析成功 >> logs\auto.log
) else if %RESULT% EQU 2 (
    echo [%date% %time%] ファイルなし（正常） >> logs\auto.log
) else (
    echo [%date% %time%] 解析失敗（コード:%RESULT%） >> logs\auto.log
)
```

### Python スクリプトから

```python
import subprocess
from datetime import datetime

def run_birdnet_analysis(model="default"):
    result = subprocess.run([
        "python", "start_analysis.py",
        "--auto", "--action", "analyze",
        "--model", model,
        "--session", f"auto_{model}_{datetime.now().strftime('%Y%m%d_%H%M')}"
    ])
    
    if result.returncode == 0:
        print("✅ 解析成功")
    elif result.returncode == 2:
        print("ℹ️ ファイルなし")
    else:
        print(f"❌ 解析失敗（コード: {result.returncode}）")

# 実行例
run_birdnet_analysis("default")
run_birdnet_analysis("custom_model_1")
```

### 複数モデルでの一括処理

```python
import subprocess

models = ["default", "custom_model_1", "custom_model_2"]

for model in models:
    print(f"モデル {model} で解析中...")
    
    result = subprocess.run([
        "python", "start_analysis.py",
        "--auto", "--action", "analyze",
        "--model", model,
        "--quiet"
    ])
    
    if result.returncode == 0:
        print(f"✅ {model}: 解析成功")
    elif result.returncode == 2:
        print(f"ℹ️ {model}: ファイルなし")
    else:
        print(f"❌ {model}: 解析失敗")
```

## 🔧 終了コード

自動モードでは、以下の終了コードで結果を通知します：

| コード | 意味 | 対応 |
|--------|------|------|
| 0 | 正常終了 | 処理が成功しました |
| 1 | 一般的なエラー | ログを確認してください |
| 2 | 音声ファイルなし | 正常（ファイル待ち状態） |
| 3 | モデルエラー | モデル名を確認してください |
| 4 | 環境エラー | setup.batを実行してください |

## 🛠️ トラブルシューティング

### PowerShellで仮想環境が有効化できない場合

**エラー例:**
```
venv\Scripts\Activate.ps1 を読み込めません。ファイル venv\Scripts\Activate.ps1 はデジタル署名されていません。
```

**解決方法:**
```powershell
# 方法1: 実行ポリシーを変更
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 方法2: コマンドプロンプトを使用
# Windowsキー + R → "cmd" → Enter
```

### 会社のPCでSSL証明書エラーが出る場合

**エラー例:**
```
SSL: CERTIFICATE_VERIFY_FAILED
Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None))
```

**解決方法:**
```cmd
# SSL証明書検証をスキップしてインストール
pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

# 仮想環境での例
venv\Scripts\activate
pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
```

**永続的な設定（一度だけ実行）:**
```cmd
mkdir %APPDATA%\pip
echo [global] > %APPDATA%\pip\pip.conf
echo trusted-host = pypi.org >> %APPDATA%\pip\pip.conf
echo                pypi.python.org >> %APPDATA%\pip\pip.conf
echo                files.pythonhosted.org >> %APPDATA%\pip\pip.conf
```

### 環境エラー（終了コード: 4）
```cmd
# Pythonがインストールされているか確認
python --version

# 仮想環境を再作成
rmdir /s venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### モデルエラー（終了コード: 3）
```cmd
# 利用可能なモデルを確認
python start_analysis.py --auto --action view_results
```

### 一般的なエラー（終了コード: 1）
```cmd
# 詳細ログで確認（--quietを外す）
python start_analysis.py --auto --action analyze --model default
```

### ファイルなし（終了コード: 2）
```cmd
# inboxフォルダを開いてファイルを配置
python start_analysis.py --auto --action open_inbox
```

## 📈 データベースビューアー

解析結果は自動的にSQLiteデータベースに保存されます。

### Streamlit Web Viewer（推奨）
```cmd
start_streamlit_viewer.bat
```

高度な検索、音声再生、統計分析などが可能なWebアプリケーションです。

## 🎵 対象鳥種（カスタムモデル）

- オオタカ (Northern Goshawk)
- サシバ (Gray-faced Buzzard)
- ミゾゴイ (Japanese Night Heron) 
- フクロウ (Ural Owl)
- ヨタカ (Gray Nightjar)

> **カスタムモデルの詳細情報:**
> - 各モデルの対応鳥種: `model/{model_name}/models_Labels.txt`
> - モデルパラメータ: `model/{model_name}/models_Params.csv`
> - モデル設定: `model/{model_name}/config.json`
> 
> 例: `model/1/models_Labels.txt` で対応鳥種を確認できます。
> 
> **利用可能なモデルの確認:**
> ```cmd
> # 対話モードでモデル一覧を表示
> python start_analysis.py
> 
> # モデルフォルダを直接確認
> dir model
> ```

**注意**: デフォルトモデルは全世界の鳥種（約6,000種）に対応しています。

## 📝 使用例

### 定期的な自動解析
```cmd
# 毎日朝6時に実行（タスクスケジューラー設定）
python start_analysis.py --auto --action analyze --model default --session "morning_routine" --quiet
```

### 手動での詳細解析
```cmd
# 対話モードで詳細確認
python start_analysis.py
# メニューから「1」または「2」を選択
```

### 結果の確認
```cmd
# 最新の解析結果を表示
python start_analysis.py --auto --action view_results
```

---

**困ったときは:**
1. `python --version` でPythonがインストールされているか確認
2. `database/audio/inbox/` に音声ファイルを配置
3. `python start_analysis.py` で対話モード実行
4. `start_streamlit_viewer.bat` で結果を確認