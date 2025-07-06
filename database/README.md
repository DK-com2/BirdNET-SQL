# Database Directory Structure

BirdNet-winプロジェクトのデータベースディレクトリ構造説明

## 📁 フォルダ構成

```
database/
├── audio/                      # 音声ファイル管理
│   ├── inbox/                 # 解析待ち音声ファイル
│   │   └── .gitkeep          # フォルダ構造保持
│   ├── completed/            # 解析完了済み音声ファイル
│   │   └── .gitkeep          # フォルダ構造保持
│   └── failed/               # 解析失敗音声ファイル
│       └── .gitkeep          # フォルダ構造保持
├── analysis_results/         # 解析結果ファイル（CSV）
│   └── .gitkeep              # フォルダ構造保持
├── result.db                 # メインデータベースファイル（gitignore対象）
└── schema_simple.sql         # データベーススキーマ（Git管理対象）
```

## 🔄 ワークフロー

### 1. 音声ファイル配置
- 解析したい音声ファイルを `audio/inbox/` に配置

### 2. 解析実行
- BirdNet解析を実行
- 結果は `analysis_results/` にCSV形式で保存
- データベース `result.db` にも保存

### 3. ファイル移動
- 解析成功 → `audio/completed/` に移動
- 解析失敗 → `audio/failed/` に移動

## 🎵 対応音声形式

- MP3 (.mp3)
- WAV (.wav)
- FLAC (.flac)
- M4A (.m4a)
- AAC (.aac)
- OGG (.ogg)

## 📊 データベース

### result.db
- SQLiteデータベース
- 検出された鳥の声の詳細情報を保存
- Streamlit Viewerで閲覧・分析可能

### schema_simple.sql
- データベーススキーマ定義
- テーブル構造の再構築に使用

## ⚠️ 注意事項

### Git管理について
- **音声ファイル**: 容量が大きいため`.gitignore`で除外
- **データベースファイル**: 個人データのため`.gitignore`で除外
- **解析結果CSV**: データを含むため`.gitignore`で除外
- **フォルダ構造**: `.gitkeep`ファイルで保持
- **スキーマファイル**: Git管理対象（データベース再構築用）

### 容量管理
- 定期的に `completed/` フォルダの古い音声ファイルを整理
- 不要な解析結果CSVファイルを削除
- データベースファイルのバックアップを推奨

### バックアップ推奨
重要なデータは定期的にバックアップを取ることを推奨します：

```bash
# データベースバックアップ
cp result.db result_backup_$(date +%Y%m%d).db

# 重要な解析結果CSVのバックアップ
cp analysis_results/important_results.csv backups/
```

## 🚀 セットアップ手順

新しい環境でのセットアップ：

1. **フォルダ構造の確認**
   ```bash
   # フォルダが存在することを確認
   ls -la database/audio/
   ```

2. **データベース初期化**（必要に応じて）
   ```bash
   # スキーマからデータベースを作成
   sqlite3 database/result.db < database/schema_simple.sql
   ```

3. **権限設定**（Linux/Mac）
   ```bash
   # 適切な権限を設定
   chmod 755 database/
   chmod 755 database/audio/
   chmod 755 database/audio/*/
   ```

## 🔧 トラブルシューティング

### フォルダが存在しない場合
```bash
# 必要なフォルダを作成
mkdir -p database/audio/{inbox,completed,failed}
mkdir -p database/analysis_results
```

### データベースファイルが破損した場合
```bash
# スキーマから再構築
rm database/result.db
sqlite3 database/result.db < database/schema_simple.sql
```

### 権限エラーの場合
```bash
# Windows
icacls database /grant %USERNAME%:F /T

# Linux/Mac
chmod -R 755 database/
```
