#!/usr/bin/env python3
"""
BirdNet Database Viewer (Simple版)
シンプル1テーブル構造用
"""

import os
import sys
import sqlite3
import pandas as pd
import argparse
from pathlib import Path

# プロジェクトのlibディレクトリをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from db.database import BirdNetSimpleDB

def get_database_path():
    """データベースパスを取得"""
    script_dir = Path(__file__).parent.parent
    return script_dir / "database" / "birdnet_simple.db"

def show_sessions(db):
    """セッション一覧を表示"""
    print("\n[INFO] セッション一覧:")
    print("-" * 50)
    
    sessions = db.get_sessions()
    
    if not sessions:
        print("  セッションがありません")
    else:
        for session in sessions:
            print(f"  セッション: {session['session_name']}")
            if session['location']:
                print(f"    場所: {session['location']}")
            if session['species']:
                print(f"    種名: {session['species']}")
            if session['analysis_date']:
                print(f"    日付: {session['analysis_date']}")
            print(f"    モデル: {session['model_name']} ({session['model_type']})")
            print(f"    検出数: {session['detection_count']}, ファイル数: {session['file_count']}")
            print(f"    平均信頼度: {session['avg_confidence']:.3f}" if session['avg_confidence'] else "    平均信頼度: N/A")
            print()

def show_detections(db, session_name=None, limit=10):
    """検出結果を表示"""
    print(f"\n[INFO] 検出結果 (最大{limit}件):")
    print("-" * 80)
    
    detections = db.get_detections(session_name, limit)
    
    if not detections:
        print("  検出結果がありません")
    else:
        # パンダスで表示
        df = pd.DataFrame(detections)
        
        # 表示用カラムを選択
        display_columns = [
            'session_name', 'filename', 'start_time_seconds', 'end_time_seconds',
            'scientific_name', 'common_name', 'confidence'
        ]
        
        available_columns = [col for col in display_columns if col in df.columns]
        
        if available_columns:
            # パンダスの表示オプション設定
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 30)
            
            print(df[available_columns].to_string(index=False))
            
            if len(detections) == limit:
                print(f"\n  ⚠️  表示制限により{limit}件のみ表示しています")

def show_statistics(db, session_name=None):
    """統計情報を表示"""
    print(f"\n[INFO] 統計情報:")
    print("-" * 50)
    
    if session_name:
        # 特定セッションの統計
        detections = db.get_detections(session_name, limit=10000)  # 全件取得
        if detections:
            df = pd.DataFrame(detections)
            print(f"  セッション: {session_name}")
            print(f"  総検出数: {len(df)}")
            print(f"  検出種数: {df['scientific_name'].nunique()}")
            print(f"  平均信頼度: {df['confidence'].mean():.3f}")
            print(f"  信頼度範囲: {df['confidence'].min():.3f} - {df['confidence'].max():.3f}")
            
            # 種別統計
            species_stats = df.groupby(['scientific_name', 'common_name']).agg({
                'confidence': ['count', 'mean']
            }).round(3)
            species_stats.columns = ['detection_count', 'avg_confidence']
            species_stats = species_stats.sort_values('detection_count', ascending=False)
            
            print(f"\n  🏆 上位検出種 (上位10種):")
            for (sci_name, common_name), row in species_stats.head(10).iterrows():
                name = common_name if common_name else sci_name
                print(f"    {name}: {row['detection_count']}件 (平均信頼度: {row['avg_confidence']:.3f})")
        else:
            print(f"  セッション '{session_name}' の検出結果がありません")
    else:
        # 全体統計
        stats = db.get_statistics()
        print(f"  総セッション数: {stats['session_count']}")
        print(f"  総検出数: {stats['detection_count']}")
        print(f"  検出種数: {stats['species_count']}")
        print(f"  対象ファイル数: {stats['file_count']}")
        
        if stats['avg_confidence']:
            print(f"  平均信頼度: {stats['avg_confidence']:.3f}")
            print(f"  信頼度範囲: {stats['min_confidence']:.3f} - {stats['max_confidence']:.3f}")
        
        if stats['top_species']:
            print(f"\n  🏆 上位検出種 (上位10種):")
            for species in stats['top_species']:
                print(f"    {species['common_name']}: {species['detection_count']}件 (平均信頼度: {species['avg_confidence']:.3f})")

def export_csv(db, output_file, session_name=None):
    """検出結果をCSVにエクスポート"""
    try:
        if db.export_to_csv(output_file, session_name):
            # ファイルサイズを確認
            file_path = Path(output_file)
            if file_path.exists():
                file_size = file_path.stat().st_size
                print(f"✅ CSVエクスポート完了: {output_file} ({file_size:,} bytes)")
            else:
                print(f"✅ CSVエクスポート完了: {output_file}")
        else:
            print(f"❌ CSVエクスポート失敗: {output_file}")
    except Exception as e:
        print(f"❌ CSVエクスポートエラー: {e}")

def main():
    parser = argparse.ArgumentParser(description='BirdNet Simple Database Viewer')
    parser.add_argument('--db', help='データベースファイルパス（省略時は自動検出）')
    parser.add_argument('--sessions', action='store_true', help='セッション一覧を表示')
    parser.add_argument('--detections', action='store_true', help='検出結果を表示')
    parser.add_argument('--stats', action='store_true', help='統計情報を表示')
    parser.add_argument('--session-name', help='特定セッション名')
    parser.add_argument('--limit', type=int, default=10, help='表示件数制限（デフォルト: 10）')
    parser.add_argument('--export', help='CSVファイルにエクスポート')
    parser.add_argument('--all', action='store_true', help='全ての情報を表示')
    
    args = parser.parse_args()
    
    # データベース接続
    if args.db:
        db = BirdNetSimpleDB(args.db)
    else:
        db = BirdNetSimpleDB()
    
    print(f"✅ データベースに接続しました: {db.db_path}")
    
    try:
        # 引数に応じて処理実行
        if args.all or (not any([args.sessions, args.detections, args.stats, args.export])):
            # デフォルトまたは--allの場合、全ての情報を表示
            show_sessions(db)
            show_detections(db, args.session_name, args.limit)
            show_statistics(db, args.session_name)
        else:
            if args.sessions:
                show_sessions(db)
            
            if args.detections:
                show_detections(db, args.session_name, args.limit)
            
            if args.stats:
                show_statistics(db, args.session_name)
            
            if args.export:
                export_csv(db, args.export, args.session_name)
    
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
    
    print(f"\n✅ 処理完了")

if __name__ == "__main__":
    main()
