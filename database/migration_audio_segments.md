# 音声セグメント機能 - データベース設計・実装完了

## 🎯 概要

BirdNET解析結果に音声セグメントとスペクトログラムファイルのパス情報を追加する機能の設計と実装状況。
**フェーズ1実装完了済み** - 新規データベース作成時に音声セグメント機能が自動的に含まれます。

## 📋 要件

### 新機能の目的
- **全ての検出結果**の音声セグメント自動生成（解析段階でconfidence >= 0.8に絞り込み済み）
- 対応するスペクトログラム画像の自動生成  
- 生成されたファイルのパス情報をデータベースで管理

### 対象データ
- データベース内の**全ての検出結果**（解析時に信頼度0.8以上で絞り込み済み）
- 前後5秒のコンテキストを含む音声切り取り（**MP3形式**）
- 対応するスペクトログラム画像（PNG形式）

## 🗄️ データベース設計

### 実装済みテーブル構造

**フェーズ1実装完了**。`schema_simple.sql`に音声セグメント機能が組み込み済み。

現在の`bird_detections`テーブル（フェーズ1実装後）：

```sql
CREATE TABLE bird_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_name TEXT NOT NULL,
    model_name TEXT,
    model_type TEXT DEFAULT 'default',
    filename TEXT NOT NULL,
    file_path TEXT,
    start_time_seconds REAL NOT NULL,
    end_time_seconds REAL NOT NULL,
    scientific_name TEXT,
    common_name TEXT,
    confidence REAL NOT NULL,
    location TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quality_status TEXT DEFAULT 'pending',
    reviewed_at TIMESTAMP,
    review_notes TEXT,
    
    -- 音声セグメント機能（フェーズ1実装済み）
    audio_segment_path TEXT,
    spectrogram_path TEXT
);
```

#### 新規カラム詳細

| カラム名 | データ型 | 用途 | 例 |
|----------|----------|------|-----|
| **audio_segment_path** | TEXT | 切り取り音声ファイルの相対パス | `audio_segments/20250719_session1/detection_001_オオタカ_0.85.mp3` |
| **spectrogram_path** | TEXT | スペクトログラム画像の相対パス | `spectrograms/20250719_session1/detection_001_オオタカ_0.85.png` |

## 📁 ディレクトリ構造

```
database/
├── result.db                    # SQLiteデータベース（フェーズ1実装後）
├── audio_segments/              # 実装済み: 音声セグメント保存（MP3）
│   ├── 20250719_143022_session1/
│   │   ├── detection_001_オオタカ_0.85.mp3
│   │   ├── detection_002_ノスリ_0.92.mp3
│   │   └── ...
│   └── 20250720_090512_session2/
├── spectrograms/               # 実装済み: スペクトログラム保存（PNG）  
│   ├── 20250719_143022_session1/
│   │   ├── detection_001_オオタカ_0.85.png
│   │   ├── detection_002_ノスリ_0.92.png
│   │   └── ...
│   └── 20250720_090512_session2/
├── schema_simple.sql           # フェーズ1更新済み（音声セグメント機能含む）
└── audio/                      # 既存
    ├── inbox/
    ├── completed/              # 元MP3ファイル保存先
    └── failed/
```

## ✅ フェーズ1実装完了状況

### ✅ 実装済み項目

**2025年7月19日実装完了**

1. **データベーススキーマ更新** ✅
   - `schema_simple.sql`に音声セグメントカラム追加済み
   - `audio_segment_path`, `spectrogram_path`カラム組み込み

2. **ディレクトリ構造作成** ✅
   - `database/audio_segments/`ディレクトリ作成済み
   - `database/spectrograms/`ディレクトリ作成済み

3. **インデックスとビュー** ✅
   - セグメント未処理レコード用ビュー (`pending_segments`)
   - セグメント処理済みビュー (`processed_segments`)
   - 処理統計ビュー (`segment_stats`)

### 🚀 自動適用
次回`start_analysis.py`実行時に、更新されたスキーマから音声セグメント機能組み込みデータベースが自動作成されます。

## 🔍 データ管理

### ファイル命名規則（フェーズ2実装予定）

#### 音声セグメント（MP3形式）
```
detection_{id:03d}_{species}_{confidence:.2f}.mp3

例: detection_001_オオタカ_0.85.mp3
```

#### スペクトログラム（PNG形式）
```
detection_{id:03d}_{species}_{confidence:.2f}.png

例: detection_001_オオタカ_0.85.png
```

### パス管理方針

#### 相対パス使用
```sql
-- ✅ 推奨: 相対パス
audio_segment_path: 'audio_segments/20250719_session1/detection_001.wav'
spectrogram_path: 'spectrograms/20250719_session1/detection_001.png'

-- ❌ 非推奨: 絶対パス
audio_segment_path: 'D:\Documents\BirdNET-SQL\database\audio_segments\...'
```

**相対パスの利点:**
- プロジェクト移動時のポータビリティ
- データベースサイズの削減
- パス解決ロジックの一元化

## 📊 基本的なクエリ

### 未処理レコードの検索
```sql
-- セグメント未生成の全レコード（解析時に既に信頼度で絞り込み済み）
SELECT id, session_name, filename, start_time_seconds, end_time_seconds, 
       confidence, common_name
FROM bird_detections 
WHERE audio_segment_path IS NULL
ORDER BY created_at DESC;
```

### 処理済みレコードの確認
```sql
-- セグメント生成済みレコード
SELECT id, session_name, common_name, confidence,
       audio_segment_path, spectrogram_path
FROM bird_detections 
WHERE audio_segment_path IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

### 統計情報
```sql
-- セグメント処理の進捗状況
SELECT 
    CASE 
        WHEN audio_segment_path IS NOT NULL THEN 'processed'
        ELSE 'pending'
    END as status,
    COUNT(*) as count
FROM bird_detections
GROUP BY status;
```

## 🎯 実装予定の機能

### 1. 自動セグメント生成
- 解析・DB保存後に全検出結果を自動処理
- 音声切り取り（前後5秒コンテキスト付き）
- スペクトログラム画像生成

### 2. 未処理レコードの一括処理
- 既存データの後処理機能
- バッチ処理による効率的な生成
- 進捗表示機能

## ⚠️ 注意事項

### ストレージ要件（フェーズ2実装後）
- 音声セグメント（MP3）: 1検出あたり約300KB-1MB（WAVより小さい）
- スペクトログラム（PNG）: 1検出あたり約200-500KB
- 合計: 検出1件あたり約500KB-1.5MB（全検出結果が対象）

### バックアップ推奨
- マイグレーション前の必須バックアップ
- 定期的なデータベースバックアップ
- 生成ファイルのバックアップ計画

## 📝 実装スケジュール

### Phase 1: データベース準備 ✅ **完了**
- [x] スキーマファイル更新 (2025/07/19)
- [x] ディレクトリ構造作成 (2025/07/19)
- [x] ビューとインデックス追加 (2025/07/19)

### Phase 2: セグメント処理機能開発 🔄 **次回実装**
- [ ] MP3音声処理モジュール作成
- [ ] スペクトログラム生成機能
- [ ] ファイルパス管理機能
- [ ] データベース連携機能

### Phase 3: start_analysis.py統合 🔄 **最終統合**
- [ ] 自動処理機能追加
- [ ] 未処理レコード一括処理
- [ ] エラーハンドリング強化
- [ ] パフォーマンス最適化

---

**実装日**: 2025年7月19日 (フェーズ1完了)  
**担当**: BirdNET-SQL プロジェクト  
**バージョン**: Phase 1 Complete - MP3 Audio Segment Support  
**ステータス**: ✅ フェーズ1完了 / 🔄 フェーズ2準備中

## 🎯 フェーズ2で実装予定の機能

### 🎵 音声処理仕様
- **入力**: MP3ファイル (元ファイルと同じ形式)
- **出力セグメント**: MP3形式 (一貫性と容量効率)
- **セグメント長**: 検出区間 + 前後5秒
- **サンプリングレート**: 元ファイルと同じ (おそらく48kHz)

### 📈 スペクトログラム
- **形式**: PNG画像
- **サイズ**: 800x600ピクセル
- **種類**: mel-spectrogram
- **自動生成**: 音声セグメントと同時作成
