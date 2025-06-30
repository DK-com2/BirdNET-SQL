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
    species TEXT,
    analysis_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_session_name ON bird_detections(session_name);
CREATE INDEX IF NOT EXISTS idx_species ON bird_detections(scientific_name, common_name);
CREATE INDEX IF NOT EXISTS idx_confidence ON bird_detections(confidence);
CREATE INDEX IF NOT EXISTS idx_location ON bird_detections(location);
CREATE INDEX IF NOT EXISTS idx_analysis_date ON bird_detections(analysis_date);
