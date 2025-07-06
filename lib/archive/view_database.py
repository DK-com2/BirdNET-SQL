#!/usr/bin/env python3
"""
BirdNet Database Viewer
データベースの内容を確認するためのツール
"""

import os
import sys
import sqlite3
import pandas as pd
import argparse
from pathlib import Path

def get_database_path():
    """データベースパスを取得"""
    script_dir = Path(__file__).parent.parent
    return script_dir / "database" / "birdnet.db"

def connect_database(db_path):
    """データベースに接続"""
    if not db_path.exists():
        print(f"❌ データベースが見つかりません: {db_path}")
        return None
    
    try:
        conn = sqlite3.connect(str(db_path))
        print(f"✅ データベースに接続しました: {db_path}")
        return conn
    except Exception as e:
        print(f"❌ データベース接続エラー: {e}")
        return None

def show_tables(conn):
    """テーブル一覧を表示"""
    print("\n📋 テーブル一覧:")
    print("-" * 50)
    
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for table in tables:
        print(f"  • {table[0]}")
    
    return [table[0] for table in tables]

def show_schema(conn, table_name=None):
    """スキーマを表示"""
    if table_name:
        print(f"\n🏗️  テーブル '{table_name}' のスキーマ:")
        print("-" * 50)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"  {col[1]} ({col[2]}) {'- PRIMARY KEY' if col[5] else ''}")
    else:
        print(f"\n🏗️  全テーブルのスキーマ:")
        print("-" * 50)
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
        schemas = cursor.fetchall()
        
        for schema in schemas:
            if schema[0]:
                print(f"{schema[0]}\n")

def show_sessions(conn):
    """セッション一覧を表示"""
    print("\n📁 セッション一覧:")
    print("-" * 50)
    
    try:
        df = pd.read_sql_query("""
            SELECT 
                s.id,
                s.session_name,
                s.created_at,
                s.total_files,
                s.total_detections,
                COUNT(af.id) as actual_files,
                COUNT(d.id) as actual_detections
            FROM sessions s
            LEFT JOIN audio_files af ON s.id = af.session_id
            LEFT JOIN detections d ON af.id = d.audio_file_id
            GROUP BY s.id, s.session_name, s.created_at, s.total_files, s.total_detections
            ORDER BY s.created_at DESC
        """, conn)
        
        if df.empty:
            print("  セッションがありません")
        else:
            for _, row in df.iterrows():
                print(f"  ID: {row['id']} | {row['session_name']} | 検出数: {row['actual_detections']} | ファイル数: {row['actual_files']} | 作成日: {row['created_at']}")
    except Exception as e:
        print(f"❌ セッション取得エラー: {e}")

def show_detections(conn, session_id=None, session_name=None, limit=10):
    """検出結果を表示"""
    print(f"\n🐦 検出結果 (最大{limit}件):")
    print("-" * 80)
    
    try:
        if session_id:
            query = """
                SELECT 
                    d.id,
                    d.start_time_seconds as start_time,
                    d.end_time_seconds as end_time,
                    d.scientific_name,
                    d.common_name,
                    d.confidence,
                    s.session_name,
                    af.filename
                FROM detections d
                JOIN audio_files af ON d.audio_file_id = af.id
                JOIN sessions s ON af.session_id = s.id
                WHERE s.id = ?
                ORDER BY af.filename, d.start_time_seconds
                LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(session_id, limit))
        elif session_name:
            query = """
                SELECT 
                    d.id,
                    d.start_time_seconds as start_time,
                    d.end_time_seconds as end_time,
                    d.scientific_name,
                    d.common_name,
                    d.confidence,
                    s.session_name,
                    af.filename
                FROM detections d
                JOIN audio_files af ON d.audio_file_id = af.id
                JOIN sessions s ON af.session_id = s.id
                WHERE s.session_name = ?
                ORDER BY af.filename, d.start_time_seconds
                LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(session_name, limit))
        else:
            query = """
                SELECT 
                    d.id,
                    d.start_time_seconds as start_time,
                    d.end_time_seconds as end_time,
                    d.scientific_name,
                    d.common_name,
                    d.confidence,
                    s.session_name,
                    af.filename
                FROM detections d
                JOIN audio_files af ON d.audio_file_id = af.id
                JOIN sessions s ON af.session_id = s.id
                ORDER BY af.filename, d.start_time_seconds
                LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(limit,))
        
        if df.empty:
            print("  検出結果がありません")
        else:
            # パンダスの表示オプションを設定
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 30)
            
            print(df.to_string(index=False))
            
            if len(df) == limit:
                print(f"\n  ⚠️  表示制限により{limit}件のみ表示しています")
    except Exception as e:
        print(f"❌ 検出結果取得エラー: {e}")

def show_statistics(conn, session_id=None, session_name=None):
    """統計情報を表示"""
    print(f"\n📊 統計情報:")
    print("-" * 50)
    
    try:
        # セッション指定がある場合
        where_clause = ""
        params = []
        
        if session_id:
            where_clause = "WHERE s.id = ?"
            params = [session_id]
        elif session_name:
            where_clause = "WHERE s.session_name = ?"
            params = [session_name]
        
        # 基本統計
        query = f"""
            SELECT 
                COUNT(d.id) as total_detections,
                COUNT(DISTINCT d.scientific_name) as unique_species,
                AVG(d.confidence) as avg_confidence,
                MIN(d.confidence) as min_confidence,
                MAX(d.confidence) as max_confidence,
                COUNT(DISTINCT af.id) as total_files
            FROM detections d
            JOIN audio_files af ON d.audio_file_id = af.id
            JOIN sessions s ON af.session_id = s.id
            {where_clause}
        """
        
        stats = pd.read_sql_query(query, conn, params=params)
        
        if stats.iloc[0]['total_detections'] > 0:
            print(f"  総検出数: {stats.iloc[0]['total_detections']}")
            print(f"  検出種数: {stats.iloc[0]['unique_species']}")
            print(f"  対象ファイル数: {stats.iloc[0]['total_files']}")
            print(f"  平均信頼度: {stats.iloc[0]['avg_confidence']:.3f}")
            print(f"  信頼度範囲: {stats.iloc[0]['min_confidence']:.3f} - {stats.iloc[0]['max_confidence']:.3f}")
            
            # 種別統計
            query = f"""
                SELECT 
                    d.common_name,
                    d.scientific_name,
                    COUNT(*) as detection_count,
                    AVG(d.confidence) as avg_confidence
                FROM detections d
                JOIN audio_files af ON d.audio_file_id = af.id
                JOIN sessions s ON af.session_id = s.id
                {where_clause}
                GROUP BY d.scientific_name, d.common_name
                ORDER BY detection_count DESC
                LIMIT 10
            """
            
            species_stats = pd.read_sql_query(query, conn, params=params)
            
            if not species_stats.empty:
                print(f"\n  🏆 上位検出種 (上位10種):")
                for _, row in species_stats.iterrows():
                    common_name = row['common_name'] if row['common_name'] else 'Unknown'
                    scientific_name = row['scientific_name'] if row['scientific_name'] else 'Unknown'
                    print(f"    {common_name} ({scientific_name}): {row['detection_count']}件 (平均信頼度: {row['avg_confidence']:.3f})")
        else:
            print("  検出結果がありません")
        
    except Exception as e:
        print(f"❌ 統計情報取得エラー: {e}")

def export_csv(conn, session_id=None, session_name=None, output_file=None):
    """検出結果をCSVにエクスポート"""
    try:
        if session_id:
            query = """
                SELECT 
                    d.start_time_seconds as 'Start (s)',
                    d.end_time_seconds as 'End (s)',
                    d.scientific_name as 'Scientific name',
                    d.common_name as 'Common name',
                    d.confidence as 'Confidence',
                    s.session_name as 'Session',
                    af.filename as 'Filename'
                FROM detections d
                JOIN audio_files af ON d.audio_file_id = af.id
                JOIN sessions s ON af.session_id = s.id
                WHERE s.id = ?
                ORDER BY af.filename, d.start_time_seconds
            """
            df = pd.read_sql_query(query, conn, params=(session_id,))
        elif session_name:
            query = """
                SELECT 
                    d.start_time_seconds as 'Start (s)',
                    d.end_time_seconds as 'End (s)',
                    d.scientific_name as 'Scientific name',
                    d.common_name as 'Common name',
                    d.confidence as 'Confidence',
                    s.session_name as 'Session',
                    af.filename as 'Filename'
                FROM detections d
                JOIN audio_files af ON d.audio_file_id = af.id
                JOIN sessions s ON af.session_id = s.id
                WHERE s.session_name = ?
                ORDER BY af.filename, d.start_time_seconds
            """
            df = pd.read_sql_query(query, conn, params=(session_name,))
        else:
            query = """
                SELECT 
                    d.start_time_seconds as 'Start (s)',
                    d.end_time_seconds as 'End (s)',
                    d.scientific_name as 'Scientific name',
                    d.common_name as 'Common name',
                    d.confidence as 'Confidence',
                    s.session_name as 'Session',
                    af.filename as 'Filename'
                FROM detections d
                JOIN audio_files af ON d.audio_file_id = af.id
                JOIN sessions s ON af.session_id = s.id
                ORDER BY af.filename, d.start_time_seconds
            """
            df = pd.read_sql_query(query, conn)
        
        if output_file is None:
            output_file = "detections_export.csv"
        
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ CSVエクスポート完了: {output_file} ({len(df)}件)")
        
    except Exception as e:
        print(f"❌ CSVエクスポートエラー: {e}")

def main():
    parser = argparse.ArgumentParser(description='BirdNet Database Viewer')
    parser.add_argument('--db', help='データベースファイルパス（省略時は自動検出）')
    parser.add_argument('--tables', action='store_true', help='テーブル一覧を表示')
    parser.add_argument('--schema', help='指定テーブルのスキーマを表示（allで全テーブル）')
    parser.add_argument('--sessions', action='store_true', help='セッション一覧を表示')
    parser.add_argument('--detections', action='store_true', help='検出結果を表示')
    parser.add_argument('--stats', action='store_true', help='統計情報を表示')
    parser.add_argument('--session-id', type=int, help='特定セッションID')
    parser.add_argument('--session-name', help='特定セッション名')
    parser.add_argument('--limit', type=int, default=10, help='表示件数制限（デフォルト: 10）')
    parser.add_argument('--export', help='CSVファイルにエクスポート')
    parser.add_argument('--all', action='store_true', help='全ての情報を表示')
    
    args = parser.parse_args()
    
    # データベースパス取得
    if args.db:
        db_path = Path(args.db)
    else:
        db_path = get_database_path()
    
    # データベース接続
    conn = connect_database(db_path)
    if not conn:
        sys.exit(1)
    
    try:
        # 引数に応じて処理実行
        if args.all or (not any([args.tables, args.schema, args.sessions, args.detections, args.stats, args.export])):
            # デフォルトまたは--allの場合、全ての情報を表示
            show_tables(conn)
            show_sessions(conn)
            show_detections(conn, args.session_id, args.session_name, args.limit)
            show_statistics(conn, args.session_id, args.session_name)
        else:
            if args.tables:
                show_tables(conn)
            
            if args.schema:
                if args.schema.lower() == 'all':
                    show_schema(conn)
                else:
                    show_schema(conn, args.schema)
            
            if args.sessions:
                show_sessions(conn)
            
            if args.detections:
                show_detections(conn, args.session_id, args.session_name, args.limit)
            
            if args.stats:
                show_statistics(conn, args.session_id, args.session_name)
            
            if args.export:
                export_csv(conn, args.session_id, args.session_name, args.export)
    
    finally:
        conn.close()
        print(f"\n✅ データベース接続を閉じました")

if __name__ == "__main__":
    main()
