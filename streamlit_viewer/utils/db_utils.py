"""
データベースユーティリティモジュール
BirdNetデータベースの操作を簡素化
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional


def get_default_database_path() -> str:
    """デフォルトのデータベースパスを取得"""
    current_file = Path(__file__).resolve()
    # utils/db_utils.py から streamlit_viewer/ へ
    streamlit_dir = current_file.parent.parent
    # streamlit_viewer/ から BirdNet-win/ へ
    project_root = streamlit_dir.parent
    db_path = project_root / "database" / "result.db"
    return str(db_path)


def test_database_connection(db_path: str) -> bool:
    """データベース接続をテスト"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            return len(tables) > 0
    except Exception:
        return False


def get_database_info(db_path: str) -> Dict[str, Any]:
    """データベースの基本情報を取得"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # テーブル一覧
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            info = {
                "tables": tables,
                "table_counts": {}
            }
            
            # 各テーブルの行数
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    info["table_counts"][table] = count
                except Exception:
                    info["table_counts"][table] = "エラー"
            
            return info
    except Exception as e:
        return {"error": str(e)}


def load_detections(db_path: str, limit: int = 100, where_clause: str = "") -> List[Dict]:
    """検出結果を読み込み"""
    try:
        with sqlite3.connect(db_path) as conn:
            # 基本的なクエリ
            query = """
            SELECT 
                filename,
                start_time,
                end_time,
                scientific_name,
                common_name,
                confidence,
                date,
                week,
                lat,
                lon
            FROM detections
            """
            
            if where_clause:
                query += f" WHERE {where_clause}"
            
            query += f" ORDER BY confidence DESC LIMIT {limit}"
            
            cursor = conn.cursor()
            cursor.execute(query)
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
    
    except Exception as e:
        print(f"検出結果読み込みエラー: {e}")
        return []


def get_species_list(db_path: str) -> List[Dict[str, str]]:
    """種一覧を取得"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT 
                    scientific_name, 
                    common_name,
                    COUNT(*) as detection_count
                FROM detections 
                WHERE scientific_name IS NOT NULL
                GROUP BY scientific_name, common_name
                ORDER BY detection_count DESC
            """)
            
            return [
                {
                    "scientific_name": row[0],
                    "common_name": row[1] or row[0],
                    "detection_count": row[2]
                }
                for row in cursor.fetchall()
            ]
    except Exception as e:
        print(f"種一覧取得エラー: {e}")
        return []


def search_detections(
    db_path: str,
    species_filter: str = "",
    confidence_min: float = 0.0,
    confidence_max: float = 1.0,
    limit: int = 100
) -> pd.DataFrame:
    """条件に基づいて検出結果を検索"""
    
    conditions = []
    params = []
    
    # 種名フィルター
    if species_filter:
        conditions.append("(common_name LIKE ? OR scientific_name LIKE ?)")
        params.extend([f"%{species_filter}%", f"%{species_filter}%"])
    
    # 信頼度フィルター
    conditions.append("confidence >= ? AND confidence <= ?")
    params.extend([confidence_min, confidence_max])
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    try:
        with sqlite3.connect(db_path) as conn:
            query = f"""
            SELECT 
                filename,
                start_time,
                end_time,
                scientific_name,
                common_name,
                confidence,
                date,
                week,
                lat,
                lon
            FROM detections
            WHERE {where_clause}
            ORDER BY confidence DESC
            LIMIT ?
            """
            
            params.append(limit)
            
            df = pd.read_sql_query(query, conn, params=params)
            return df
    
    except Exception as e:
        print(f"検索エラー: {e}")
        return pd.DataFrame()


def get_statistics(db_path: str) -> Dict[str, Any]:
    """データベースの統計情報を取得"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 基本統計
            cursor.execute("SELECT COUNT(*) FROM detections")
            total_detections = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT scientific_name) FROM detections")
            unique_species = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT filename) FROM detections")
            unique_files = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(confidence) FROM detections")
            avg_confidence = cursor.fetchone()[0]
            
            cursor.execute("SELECT MAX(confidence) FROM detections")
            max_confidence = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(confidence) FROM detections")
            min_confidence = cursor.fetchone()[0]
            
            return {
                "detection_count": total_detections,
                "unique_species": unique_species,
                "unique_files": unique_files,
                "avg_confidence": round(avg_confidence or 0, 3),
                "max_confidence": max_confidence or 0,
                "min_confidence": min_confidence or 0
            }
    
    except Exception as e:
        print(f"統計取得エラー: {e}")
        return {}
