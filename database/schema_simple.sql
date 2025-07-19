-- BirdNet Simple Database Schema
-- シンプルな1テーブル構造

CREATE TABLE IF NOT EXISTS bird_detections (
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
    
    -- ========== 品質評価関連カラム（最小構成） ==========
    
    -- 品質評価ステータス（pending/approved/rejected）
    quality_status TEXT DEFAULT 'pending' CHECK(quality_status IN ('pending', 'approved', 'rejected')),
    
    -- レビュー実施日時
    reviewed_at TIMESTAMP,
    
    -- 簡潔なメモ（必要時のみ）
    review_notes TEXT,
    
    -- ========== 音声セグメント機能（フェーズ1） ==========
    
    -- 切り取り音声ファイルの相対パス
    audio_segment_path TEXT,
    
    -- スペクトログラム画像の相対パス
    spectrogram_path TEXT
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_session_name ON bird_detections(session_name);
CREATE INDEX IF NOT EXISTS idx_species ON bird_detections(scientific_name, common_name);
CREATE INDEX IF NOT EXISTS idx_confidence ON bird_detections(confidence);
CREATE INDEX IF NOT EXISTS idx_location ON bird_detections(location);

-- 品質評価用のインデックス
CREATE INDEX IF NOT EXISTS idx_quality_status ON bird_detections(quality_status);

-- 音声セグメント機能用のインデックス
CREATE INDEX IF NOT EXISTS idx_audio_segment_path ON bird_detections(audio_segment_path);
CREATE INDEX IF NOT EXISTS idx_spectrogram_path ON bird_detections(spectrogram_path);

-- ビュー: 評価待ちのレコード
CREATE VIEW IF NOT EXISTS pending_review AS
SELECT *
FROM bird_detections
WHERE quality_status = 'pending'
ORDER BY created_at ASC;

-- ビュー: 承認済みのレコード
CREATE VIEW IF NOT EXISTS approved_detections AS
SELECT *
FROM bird_detections
WHERE quality_status = 'approved'
ORDER BY reviewed_at DESC;

-- ========== 音声セグメント機能関連ビュー ==========

-- ビュー: セグメント未処理のレコード
CREATE VIEW IF NOT EXISTS pending_segments AS
SELECT id, session_name, filename, start_time_seconds, end_time_seconds,
       confidence, common_name, scientific_name, created_at
FROM bird_detections
WHERE audio_segment_path IS NULL
ORDER BY created_at ASC;

-- ビュー: セグメント処理済みのレコード
CREATE VIEW IF NOT EXISTS processed_segments AS
SELECT id, session_name, common_name, confidence,
       audio_segment_path, spectrogram_path, created_at
FROM bird_detections
WHERE audio_segment_path IS NOT NULL
ORDER BY created_at DESC;

-- ビュー: セグメント処理統計
CREATE VIEW IF NOT EXISTS segment_stats AS
SELECT 
    COUNT(*) as total_detections,
    COUNT(audio_segment_path) as processed_segments,
    COUNT(*) - COUNT(audio_segment_path) as pending_segments,
    ROUND(CAST(COUNT(audio_segment_path) AS FLOAT) / COUNT(*) * 100, 2) as processing_percentage
FROM bird_detections;
