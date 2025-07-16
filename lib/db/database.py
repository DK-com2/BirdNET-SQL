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
        """データベースの初期化とマイグレーション"""
        schema_path = self.db_path.parent / "schema_simple.sql"
        
        with sqlite3.connect(self.db_path) as conn:
            # 既存テーブルのカラムを確認し、品質評価カラムがない場合は追加
            self._migrate_quality_columns(conn)
            
            if schema_path.exists():
                with open(schema_path, 'r', encoding='utf-8') as f:
                    conn.executescript(f.read())
            else:
                # スキーマファイルがない場合は直接作成（品質評価カラム付き）
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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        -- 品質評価関連カラム（最小構成）
                        quality_status TEXT DEFAULT 'pending' CHECK(quality_status IN ('pending', 'approved', 'rejected')),
                        reviewed_at TIMESTAMP,
                        review_notes TEXT
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_session_name ON bird_detections(session_name);
                    CREATE INDEX IF NOT EXISTS idx_species ON bird_detections(scientific_name, common_name);
                    CREATE INDEX IF NOT EXISTS idx_confidence ON bird_detections(confidence);
                    CREATE INDEX IF NOT EXISTS idx_quality_status ON bird_detections(quality_status);
                    
                    -- 評価待ちレコード用ビュー
                    CREATE VIEW IF NOT EXISTS pending_review AS
                    SELECT * FROM bird_detections WHERE quality_status = 'pending' ORDER BY created_at ASC;
                    
                    -- 承認済みレコード用ビュー
                    CREATE VIEW IF NOT EXISTS approved_detections AS
                    SELECT * FROM bird_detections WHERE quality_status = 'approved' ORDER BY reviewed_at DESC;
                """)
    
    def _migrate_quality_columns(self, conn):
        """品質評価カラムのマイグレーション"""
        cursor = conn.cursor()
        
        # テーブルが存在するか確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bird_detections'")
        if not cursor.fetchone():
            return  # テーブルがない場合は何もしない
        
        # 現在のカラム一覧を取得
        cursor.execute("PRAGMA table_info(bird_detections)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # 品質評価カラムがない場合は追加
        migrations = [
            ('quality_status', "ALTER TABLE bird_detections ADD COLUMN quality_status TEXT DEFAULT 'pending' CHECK(quality_status IN ('pending', 'approved', 'rejected'))"),
            ('reviewed_at', "ALTER TABLE bird_detections ADD COLUMN reviewed_at TIMESTAMP"),
            ('review_notes', "ALTER TABLE bird_detections ADD COLUMN review_notes TEXT")
        ]
        
        for column_name, sql in migrations:
            if column_name not in columns:
                try:
                    cursor.execute(sql)
                    print(f"[INFO] カラムを追加しました: {column_name}")
                except sqlite3.Error as e:
                    print(f"[WARNING] カラム追加エラー {column_name}: {e}")
        
        # インデックスとビューを追加
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_status ON bird_detections(quality_status)")
            cursor.execute("CREATE VIEW IF NOT EXISTS pending_review AS SELECT * FROM bird_detections WHERE quality_status = 'pending' ORDER BY created_at ASC")
            cursor.execute("CREATE VIEW IF NOT EXISTS approved_detections AS SELECT * FROM bird_detections WHERE quality_status = 'approved' ORDER BY reviewed_at DESC")
        except sqlite3.Error as e:
            print(f"[WARNING] インデックス/ビュー作成エラー: {e}")
        
        conn.commit()
    
    def import_csv_results(self, csv_path: str, session_name: str, model_name: str = "BirdNET", model_type: str = "default") -> Dict:
        """CSVファイルから検出結果をインポート"""
        csv_path = Path(csv_path)
        
        if not csv_path.exists():
            return {'success': False, 'error': f'CSV file not found: {csv_path}'}
        
        try:
            # CSVファイルを読み込み
            df = pd.read_csv(csv_path)
            
            # CSVフォーマットの種類を判定
            if 'Begin Path' in df.columns:  # table形式
                required_columns = ['Begin Time (s)', 'End Time (s)', 'Common Name', 'Species Code', 'Confidence', 'Begin Path']
                time_start_col = 'Begin Time (s)'
                time_end_col = 'End Time (s)'
                common_name_col = 'Common Name'
                scientific_name_col = 'Species Code'  # table形式では科学名がない場合がある
                confidence_col = 'Confidence'
                file_path_col = 'Begin Path'
            else:  # csv形式
                required_columns = ['Start (s)', 'End (s)', 'Scientific name', 'Common name', 'Confidence']
                time_start_col = 'Start (s)'
                time_end_col = 'End (s)'
                common_name_col = 'Common name'
                scientific_name_col = 'Scientific name'
                confidence_col = 'Confidence'
                file_path_col = None
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {'success': False, 'error': f'Missing columns: {missing_columns}'}
            
            # セッション名から場所、種名、日付を解析
            location, _, _ = self._parse_session_name(session_name)
            
            # 元の音声ファイル名を推定
            # CSVファイル名から音声ファイル名を推定: xxx.BirdNET.results.csv -> xxx
            original_filename = csv_path.name.replace('.BirdNET.results.csv', '')
            
            # 元の音声ファイルのパスを推定
            # database/audioフォルダ内の音声ファイルパスを構築
            project_root = Path(__file__).parent.parent.parent
            audio_folder = project_root / "database" / "audio"
            
            # 音声ファイルの拡張子を推定
            possible_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']
            original_audio_path = None
            
            for ext in possible_extensions:
                potential_path = audio_folder / (original_filename + ext)
                if potential_path.exists():
                    original_audio_path = str(potential_path)
                    break
            
            # 見つからない場合は推定パスを使用
            if original_audio_path is None:
                original_audio_path = str(audio_folder / (original_filename + '.wav'))
            
            # データベースに挿入
            records = []
            for _, row in df.iterrows():
                # 各行ごとにファイル情報を取得
                if file_path_col and pd.notna(row[file_path_col]):
                    # table形式の場合、Begin Path列からファイルパスを取得
                    row_file_path = str(row[file_path_col])
                    row_filename = Path(row_file_path).name
                    # 拡張子を除去
                    row_filename_stem = Path(row_file_path).stem
                else:
                    # csv形式の場合、推定した情報を使用
                    row_file_path = original_audio_path
                    row_filename = original_filename
                    row_filename_stem = original_filename
                
                record = {
                    'session_name': session_name,
                    'model_name': model_name,
                    'model_type': model_type,
                    'filename': row_filename_stem,  # 拡張子なしのファイル名
                    'file_path': row_file_path,  # 完全なファイルパス
                    'start_time_seconds': row[time_start_col],
                    'end_time_seconds': row[time_end_col],
                    'scientific_name': row[scientific_name_col] if pd.notna(row[scientific_name_col]) else None,
                    'common_name': row[common_name_col] if pd.notna(row[common_name_col]) else None,
                    'confidence': row[confidence_col],
                    'location': location,
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
                        location, created_at
                    ) VALUES (
                        :session_name, :model_name, :model_type, :filename, :file_path,
                        :start_time_seconds, :end_time_seconds, :scientific_name, :common_name, :confidence,
                        :location, :created_at
                    )
                """
                
                cursor.executemany(insert_sql, records)
                conn.commit()
            
            return {
                'success': True,
                'detections_imported': len(records),
                'session_name': session_name,
                'csv_filename': csv_path.name,
                'audio_files_found': len(set(record['filename'] for record in records))
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
                    COUNT(*) as detection_count,
                    COUNT(DISTINCT filename) as file_count,
                    MIN(created_at) as first_created,
                    MAX(created_at) as last_created,
                    AVG(confidence) as avg_confidence
                FROM bird_detections
                GROUP BY session_name, model_name, model_type, location
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
                    'detection_count': row[4],
                    'file_count': row[5],
                    'first_created': row[6],
                    'last_created': row[7],
                    'avg_confidence': row[8]
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
                            location
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
                            location
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
    
    # ========== 品質評価関連メソッド ==========
    
    def get_pending_reviews(self, limit: int = 50) -> List[Dict]:
        """評価待ちのレコードを取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM bird_detections 
                WHERE quality_status = 'pending' 
                ORDER BY created_at ASC 
                LIMIT ?
            """
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_quality_status(self, detection_id: int, status: str, notes: str = None) -> bool:
        """品質評価ステータスを更新"""
        if status not in ['pending', 'approved', 'rejected']:
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE bird_detections 
                    SET quality_status = ?, reviewed_at = ?, review_notes = ?
                    WHERE id = ?
                """, (status, datetime.now().isoformat(), notes, detection_id))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Quality status update error: {e}")
            return False
    
    def get_quality_statistics(self) -> Dict:
        """品質評価統計を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    quality_status,
                    COUNT(*) as count
                FROM bird_detections
                GROUP BY quality_status
            """)
            
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # デフォルト値を設定
            return {
                'pending': status_counts.get('pending', 0),
                'approved': status_counts.get('approved', 0),
                'rejected': status_counts.get('rejected', 0),
                'total': sum(status_counts.values())
            }

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
