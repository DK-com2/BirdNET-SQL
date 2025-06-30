"""
BirdNet Simple Database Manager
1テーブル構造でシンプルに管理
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import os
import re
from typing import Dict, List, Optional

class BirdNetSimpleDB:
    """シンプルな1テーブル構造のBirdNetデータベース"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # デフォルトのデータベースパス
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "database" / "result.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._initialize_database()
    
    def _initialize_database(self):
        """データベースの初期化"""
        schema_path = self.db_path.parent / "schema_simple.sql"
        
        with sqlite3.connect(self.db_path) as conn:
            if schema_path.exists():
                with open(schema_path, 'r', encoding='utf-8') as f:
                    conn.executescript(f.read())
            else:
                # スキーマファイルがない場合は直接作成
                conn.executescript("""
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
                    
                    CREATE INDEX IF NOT EXISTS idx_session_name ON bird_detections(session_name);
                    CREATE INDEX IF NOT EXISTS idx_species ON bird_detections(scientific_name, common_name);
                    CREATE INDEX IF NOT EXISTS idx_confidence ON bird_detections(confidence);
                """)
    
    def import_csv_results(self, csv_path: str, session_name: str, model_name: str = "BirdNET", model_type: str = "default") -> Dict:
        """CSVファイルから検出結果をインポート"""
        csv_path = Path(csv_path)
        
        if not csv_path.exists():
            return {'success': False, 'error': f'CSV file not found: {csv_path}'}
        
        try:
            # CSVファイルを読み込み
            df = pd.read_csv(csv_path)
            
            # 列名の確認と標準化
            required_columns = ['Start (s)', 'End (s)', 'Scientific name', 'Common name', 'Confidence']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {'success': False, 'error': f'Missing columns: {missing_columns}'}
            
            # セッション名から場所、種名、日付を解析
            location, species, analysis_date = self._parse_session_name(session_name)
            
            # データベースに挿入
            records = []
            for _, row in df.iterrows():
                record = {
                    'session_name': session_name,
                    'model_name': model_name,
                    'model_type': model_type,
                    'filename': csv_path.name,
                    'file_path': str(csv_path),
                    'start_time_seconds': row['Start (s)'],
                    'end_time_seconds': row['End (s)'],
                    'scientific_name': row['Scientific name'] if pd.notna(row['Scientific name']) else None,
                    'common_name': row['Common name'] if pd.notna(row['Common name']) else None,
                    'confidence': row['Confidence'],
                    'location': location,
                    'species': species,
                    'analysis_date': analysis_date,
                    'created_at': datetime.now().isoformat()
                }
                records.append(record)
            
            # データベースに一括挿入
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                insert_sql = """
                    INSERT INTO bird_detections (
                        session_name, model_name, model_type, filename, file_path,
                        start_time_seconds, end_time_seconds, scientific_name, common_name, confidence,
                        location, species, analysis_date, created_at
                    ) VALUES (
                        :session_name, :model_name, :model_type, :filename, :file_path,
                        :start_time_seconds, :end_time_seconds, :scientific_name, :common_name, :confidence,
                        :location, :species, :analysis_date, :created_at
                    )
                """
                
                cursor.executemany(insert_sql, records)
                conn.commit()
            
            return {
                'success': True,
                'detections_imported': len(records),
                'session_name': session_name,
                'filename': csv_path.name
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _parse_session_name(self, session_name: str) -> tuple:
        """セッション名から場所、種名、日付を解析"""
        # パターン: 場所_種名_日付
        pattern = r'^(.+?)_(.+?)_(.+)$'
        match = re.match(pattern, session_name)
        
        if match:
            location = match.group(1)
            species = match.group(2)
            date = match.group(3)
            return location, species, date
        else:
            # 解析できない場合はそのまま格納
            return None, None, None
    
    def get_sessions(self) -> List[Dict]:
        """セッション一覧を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    session_name,
                    model_name,
                    model_type,
                    location,
                    species,
                    analysis_date,
                    COUNT(*) as detection_count,
                    COUNT(DISTINCT filename) as file_count,
                    MIN(created_at) as first_created,
                    MAX(created_at) as last_created,
                    AVG(confidence) as avg_confidence
                FROM bird_detections
                GROUP BY session_name, model_name, model_type, location, species, analysis_date
                ORDER BY MAX(created_at) DESC
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            sessions = []
            for row in rows:
                sessions.append({
                    'session_name': row[0],
                    'model_name': row[1],
                    'model_type': row[2],
                    'location': row[3],
                    'species': row[4],
                    'analysis_date': row[5],
                    'detection_count': row[6],
                    'file_count': row[7],
                    'first_created': row[8],
                    'last_created': row[9],
                    'avg_confidence': row[10]
                })
            
            return sessions
    
    def get_detections(self, session_name: str = None, limit: int = 100) -> List[Dict]:
        """検出結果を取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if session_name:
                query = """
                    SELECT * FROM bird_detections 
                    WHERE session_name = ? 
                    ORDER BY filename, start_time_seconds 
                    LIMIT ?
                """
                cursor.execute(query, (session_name, limit))
            else:
                query = """
                    SELECT * FROM bird_detections 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """
                cursor.execute(query, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 基本統計
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT session_name) as session_count,
                    COUNT(DISTINCT filename) as file_count,
                    COUNT(*) as detection_count,
                    COUNT(DISTINCT scientific_name) as species_count,
                    AVG(confidence) as avg_confidence,
                    MIN(confidence) as min_confidence,
                    MAX(confidence) as max_confidence
                FROM bird_detections
            """)
            
            stats = cursor.fetchone()
            
            # 上位検出種
            cursor.execute("""
                SELECT 
                    common_name,
                    scientific_name,
                    COUNT(*) as detection_count,
                    AVG(confidence) as avg_confidence
                FROM bird_detections
                WHERE common_name IS NOT NULL
                GROUP BY scientific_name, common_name
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            
            top_species = []
            for row in cursor.fetchall():
                top_species.append({
                    'common_name': row[0],
                    'scientific_name': row[1],
                    'detection_count': row[2],
                    'avg_confidence': row[3]
                })
            
            return {
                'session_count': stats[0] or 0,
                'file_count': stats[1] or 0,
                'detection_count': stats[2] or 0,
                'species_count': stats[3] or 0,
                'avg_confidence': stats[4],
                'min_confidence': stats[5],
                'max_confidence': stats[6],
                'top_species': top_species
            }
    
    def export_to_csv(self, output_path: str, session_name: str = None) -> bool:
        """検出結果をCSVにエクスポート"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if session_name:
                    query = """
                        SELECT 
                            start_time_seconds as 'Start (s)',
                            end_time_seconds as 'End (s)',
                            scientific_name as 'Scientific name',
                            common_name as 'Common name',
                            confidence as 'Confidence',
                            session_name,
                            filename,
                            location,
                            species,
                            analysis_date
                        FROM bird_detections 
                        WHERE session_name = ? 
                        ORDER BY filename, start_time_seconds
                    """
                    df = pd.read_sql_query(query, conn, params=(session_name,))
                else:
                    query = """
                        SELECT 
                            start_time_seconds as 'Start (s)',
                            end_time_seconds as 'End (s)',
                            scientific_name as 'Scientific name',
                            common_name as 'Common name',
                            confidence as 'Confidence',
                            session_name,
                            filename,
                            location,
                            species,
                            analysis_date
                        FROM bird_detections 
                        ORDER BY created_at DESC
                    """
                    df = pd.read_sql_query(query, conn)
                
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                return True
                
        except Exception as e:
            print(f"CSV export error: {e}")
            return False
    
    def delete_session(self, session_name: str) -> bool:
        """セッションを削除"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM bird_detections WHERE session_name = ?", (session_name,))
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count > 0
        except Exception as e:
            print(f"Delete session error: {e}")
            return False

def main():
    """テスト用のメイン関数"""
    db = BirdNetSimpleDB()
    print("BirdNet Simple Database initialized")
    
    # 統計情報表示
    stats = db.get_statistics()
    print(f"Sessions: {stats['session_count']}")
    print(f"Detections: {stats['detection_count']}")
    print(f"Species: {stats['species_count']}")

if __name__ == "__main__":
    main()
