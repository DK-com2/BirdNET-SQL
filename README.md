# BirdNET-SQL

BirdNETを使用した鳥の鳴き声解析・データベース管理システム

## 機能

- 音声ファイルの自動解析（BirdNET AI）
- 解析結果のデータベース保存
- セッション管理
- カスタムモデル対応

## セットアップ

1. 必要なライブラリをインストール:
```bash
pip install -r requirements.txt
```

2. 解析実行:
```bash
python main.py
```

## 使用方法

### 対話モード（メニュー形式）
1. 音声ファイルを `database/audio/inbox/` に配置
2. `python main.py` でプログラム起動
3. メニューから解析方法を選択:
   - `[1]` デフォルトモデルで解析
   - `[2]` カスタムモデルで解析
4. セッション名を入力して結果をデータベースに保存

### 自動モード（コマンドライン）

```bash
# デフォルトモデルで解析
python main.py --auto --action analyze --model default

# カスタムモデルで解析
python main.py --auto --action analyze --model custom_model_1

# 解析結果を表示
python main.py --auto --action view_results

# inboxフォルダを開く
python main.py --auto --action open_inbox

# セッション名を指定
python main.py --auto --action analyze --model default --session "morning_birds"

# 静謐モード（ログを最小限に）
python main.py --auto --action analyze --model default --quiet
```

### コマンドラインオプション

| オプション | 説明 | 必須 | デフォルト |
|-----------|------|------|------------|
| `--auto` | 自動モードを有効化 | ◯（自動モード時） | - |
| `--action` | 実行する処理<br>`analyze`, `view_results`, `open_inbox` | ◯（自動モード時） | - |
| `--model` | 使用するモデル名 | - | `default` |
| `--session` | セッション名 | - | 自動生成 |
| `--quiet` | 静謐モード | - | `False` |

## 設定

`analysis.conf` で解析設定をカスタマイズ:

```
# BirdNET Analysis Configuration
overlap=2
rtype=csv
sensitivity=1.5
min_conf=0.7
threads=12
```

- `overlap`: オーバーラップ時間（秒）
- `sensitivity`: 検出感度（1.0-2.0）
- `min_conf`: 最小信頼度（0.1-1.0）
- `threads`: 並列処理数

## 対応形式

音声ファイル: MP3, WAV, FLAC, M4A

## 終了コード

自動モードでは、以下の終了コードで結果を通知します：

| コード | 意味 | 対応 |
|--------|------|------|
| 0 | 正常終了 | 処理が成功しました |
| 1 | 一般的なエラー | ログを確認してください |
| 2 | 音声ファイルなし | 正常（ファイル待ち状態） |
| 3 | モデルエラー | モデル名を確認してください |
| 4 | 環境エラー | セットアップを確認してください |

## ファイル構成

```
BirdNET-SQL/
├── main.py              # メインプログラム
├── analysis.conf        # 解析設定
├── requirements.txt     # 依存ライブラリ
├── database/
│   ├── audio/
│   │   ├── inbox/       # 解析対象ファイル配置
│   │   ├── completed/   # 解析済みファイル
│   │   └── failed/      # 解析失敗ファイル
│   └── analysis_results/ # 解析結果CSV
├── lib/
│   ├── birdnet/         # BirdNET解析エンジン
│   └── db/              # データベース管理
└── model/               # カスタムモデル格納
```