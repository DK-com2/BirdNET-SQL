"""
BirdNet Results Database Manager
Phase 1: 基本的な結果管理機能
"""

import sqlite3
import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd


class BirdNetDB:
    def __init__(self, db_path: str = None):
        if db_path is None:
            project_path = os.getenv("PROJECT_PATH", os.getcwd())
            # パスの前後の空白を除去
            project_path = project_path.strip()
            db_path = os.path.join(project_path, "database", "birdnet.db")
        
        self.db_path = db_path
        print(f"Database path: {self.db_path}")
        self.init_database()
    
    def init_database(self):
        """データベースの初期化"""
        db_dir = os.path.dirname(self.db_path)
        print(f"Creating database directory: {db_dir}")
        
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory: {e}")
            # フォールバック: カレントディレクトリに作成
            self.db_path = os.path.join(os.getcwd(), "database", "birdnet.db")
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            print(f"Fallback database path: {self.db_path}")
        
        # スキーマファイルを読み込んで実行
        schema_path = os.path.join(db_dir, "schema.sql")
        
        with sqlite3.connect(self.db_path) as conn:
            if os.path.exists(schema_path):
                print(f"Loading schema from: {schema_path}")
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                conn.executescript(schema_sql)
            else:
                print("Schema file not found, creating basic schema...")
                # 基本スキーマを直接作成
                basic_schema = """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_name TEXT NOT NULL,
                    model_name TEXT,
                    model_type TEXT DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    total_files INTEGER DEFAULT 0,
                    total_detections INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS audio_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_path TEXT,
                    duration_seconds REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audio_file_id INTEGER NOT NULL,
                    start_time_seconds REAL NOT NULL,
                    end_time_seconds REAL NOT NULL,
                    scientific_name TEXT,
                    common_name TEXT,
                    confidence REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (audio_file_id) REFERENCES audio_files (id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_detections_species ON detections(scientific_name);
                CREATE INDEX IF NOT EXISTS idx_detections_confidence ON detections(confidence);
                CREATE INDEX IF NOT EXISTS idx_detections_time ON detections(start_time_seconds, end_time_seconds);
                CREATE INDEX IF NOT EXISTS idx_audio_files_session ON audio_files(session_id);

                INSERT OR IGNORE INTO sessions (id, session_name, model_name, model_type, description)
                VALUES (1, 'Default Session', 'BirdNET Default', 'default', 'Default analysis session for uncategorized results');
                """
                conn.executescript(basic_schema)
            
            conn.commit()
        
        print(f"Database initialized successfully: {self.db_path}")
    
    def parse_time_to_seconds(self, time_str: str) -> float:
        """時間文字列を秒数に変換"""
        if pd.isna(time_str) or time_str == '' or time_str is None:
            return 0.0
        
        time_str = str(time_str).strip()
        
        # 既に数値の場合はそのまま返す
        try:
            return float(time_str)
        except:
            pass
        
        # 0m0s 形式の解析
        pattern = r'(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?'
        match = re.match(pattern, time_str)
        
        if match:
            minutes = int(match.group(1)) if match.group(1) else 0
            seconds = float(match.group(2)) if match.group(2) else 0
            return minutes * 60 + seconds
        
        # 00:00 形式の解析
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                try:
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
                except:
                    pass
        
        print(f"Warning: Could not parse time '{time_str}', using 0.0")
        return 0.0
    
    def create_session(self, session_name: str, model_name: str = "BirdNET Default", 
                      model_type: str = "default", description: str = "") -> int:
        """新しい解析セッションを作成"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (session_name, model_name, model_type, description)
                VALUES (?, ?, ?, ?)
            """, (session_name, model_name, model_type, description))
            session_id = cursor.lastrowid
            conn.commit()
            return session_id
    
    def get_sessions(self) -> List[Dict]:
        """全セッション一覧を取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, 
                       COUNT(DISTINCT af.id) as file_count,
                       COUNT(d.id) as detection_count
                FROM sessions s
                LEFT JOIN audio_files af ON s.id = af.session_id
                LEFT JOIN detections d ON af.id = d.audio_file_id
                GROUP BY s.id
                ORDER BY s.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_audio_file(self, session_id: int, filename: str, 
                      file_path: str = "", duration_seconds: float = 0) -> int:
        """音声ファイル情報を追加"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audio_files (session_id, filename, file_path, duration_seconds)
                VALUES (?, ?, ?, ?)
            """, (session_id, filename, file_path, duration_seconds))
            audio_file_id = cursor.lastrowid
            conn.commit()
            return audio_file_id
    
    def import_csv_results(self, csv_file_path: str, session_id: int = None) -> Dict:
        """CSVファイルから結果をインポート"""
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
        
        # CSVファイル名から音声ファイル名を推定
        csv_filename = os.path.basename(csv_file_path)
        audio_filename = csv_filename.replace('.BirdNET.results.csv', '')
        
        # デフォルトセッションを使用
        if session_id is None:
            session_id = 1
        
        # 音声ファイル情報を追加
        audio_file_id = self.add_audio_file(
            session_id=session_id,
            filename=audio_filename,
            file_path=csv_file_path.replace('.BirdNET.results.csv', '')
        )
        
        # CSVを読み込み
        try:
            df = pd.read_csv(csv_file_path)
            detection_count = 0
            
            print(f"CSV columns: {df.columns.tolist()}")
            print(f"CSV shape: {df.shape}")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for idx, row in df.iterrows():
                    # 空の行をスキップ
                    scientific_name = row.get('Scientific name', '')
                    common_name = row.get('Common name', '')
                    
                    if pd.isna(scientific_name) and pd.isna(common_name):
                        continue
                    
                    # 時間の変換
                    start_time = self.parse_time_to_seconds(row.get('Start (s)', 0))
                    end_time = self.parse_time_to_seconds(row.get('End (s)', 0))
                    
                    # 信頼度の処理
                    confidence = row.get('Confidence', 0)
                    if pd.isna(confidence):
                        confidence = 0.0
                    else:
                        confidence = float(confidence)
                    
                    # データベースに挿入
                    cursor.execute("""
                        INSERT INTO detections 
                        (audio_file_id, start_time_seconds, end_time_seconds, 
                         scientific_name, common_name, confidence)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        audio_file_id,
                        start_time,
                        end_time,
                        str(scientific_name) if not pd.isna(scientific_name) else '',
                        str(common_name) if not pd.isna(common_name) else '',
                        confidence
                    ))
                    detection_count += 1
                
                conn.commit()
            
            return {
                'success': True,
                'audio_file_id': audio_file_id,
                'detections_imported': detection_count,
                'filename': audio_filename
            }
            
        except Exception as e:
            print(f"Import error details: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'filename': audio_filename
            }
    
    def get_detections(self, session_id: int = None, 
                      audio_file_id: int = None, 
                      species: str = None,
                      min_confidence: float = 0.0) -> List[Dict]:
        """検出結果を取得（フィルタ対応）"""
        query = """
            SELECT d.*, af.filename, af.file_path, s.session_name, s.model_name
            FROM detections d
            JOIN audio_files af ON d.audio_file_id = af.id
            JOIN sessions s ON af.session_id = s.id
            WHERE 1=1
        """
        params = []
        
        if session_id:
            query += " AND s.id = ?"
            params.append(session_id)
        
        if audio_file_id:
            query += " AND af.id = ?"
            params.append(audio_file_id)
        
        if species:
            query += " AND (d.scientific_name LIKE ? OR d.common_name LIKE ?)"
            params.extend([f"%{species}%", f"%{species}%"])
        
        if min_confidence > 0:
            query += " AND d.confidence >= ?"
            params.append(min_confidence)
        
        query += " ORDER BY af.filename, d.start_time_seconds"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self, session_id: int = None) -> Dict:
        """統計情報を取得"""
        query = """
            SELECT 
                COUNT(DISTINCT s.id) as session_count,
                COUNT(DISTINCT af.id) as file_count,
                COUNT(d.id) as detection_count,
                COUNT(DISTINCT d.scientific_name) as species_count,
                AVG(d.confidence) as avg_confidence,
                MAX(d.confidence) as max_confidence,
                MIN(d.confidence) as min_confidence
            FROM sessions s
            LEFT JOIN audio_files af ON s.id = af.session_id
            LEFT JOIN detections d ON af.id = d.audio_file_id
        """
        params = []
        
        if session_id:
            query += " WHERE s.id = ?"
            params.append(session_id)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = dict(cursor.fetchone())
            
            # 種別集計
            species_query = """
                SELECT d.scientific_name, d.common_name, 
                       COUNT(*) as detection_count,
                       AVG(d.confidence) as avg_confidence
                FROM detections d
                JOIN audio_files af ON d.audio_file_id = af.id
                JOIN sessions s ON af.session_id = s.id
                WHERE d.scientific_name IS NOT NULL AND d.scientific_name != ''
            """
            if session_id:
                species_query += " AND s.id = ?"
            
            species_query += """
                GROUP BY d.scientific_name, d.common_name
                ORDER BY detection_count DESC
                LIMIT 10
            """
            
            cursor.execute(species_query, params)
            result['top_species'] = [dict(row) for row in cursor.fetchall()]
            
            return result
    
    def export_to_csv(self, output_path: str, session_id: int = None) -> bool:
        """結果をCSVにエクスポート"""
        try:
            detections = self.get_detections(session_id=session_id)
            df = pd.DataFrame(detections)
            
            if not df.empty:
                # 列名を整理
                columns_mapping = {
                    'start_time_seconds': 'Start (s)',
                    'end_time_seconds': 'End (s)',
                    'scientific_name': 'Scientific name',
                    'common_name': 'Common name',
                    'confidence': 'Confidence',
                    'filename': 'Audio File',
                    'session_name': 'Session',
                    'model_name': 'Model'
                }
                
                df = df.rename(columns=columns_mapping)
                df = df[list(columns_mapping.values())]
                
                df.to_csv(output_path, index=False)
                return True
            return False
            
        except Exception as e:
            print(f"Export error: {e}")
            return False


# 使用例とテスト関数
def test_database():
    """データベースのテスト"""
    print("Testing BirdNet Database...")
    
    try:
        db = BirdNetDB()
        print("✓ Database initialized successfully")
        
        # セッション作成
        session_id = db.create_session(
            session_name="Test Session",
            model_name="Custom Model 1",
            model_type="custom",
            description="Test analysis session"
        )
        
        print(f"✓ Created session: {session_id}")
        
        # セッション一覧
        sessions = db.get_sessions()
        print(f"✓ Found {len(sessions)} sessions")
        
        # 統計情報
        stats = db.get_statistics()
        print(f"✓ Statistics: {stats['detection_count']} detections, {stats['species_count']} species")
        
        print("Database test completed successfully!")
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_database()
