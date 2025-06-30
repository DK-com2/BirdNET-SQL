"""
BirdNet結果インポートツール（拡張版）
場所+種名+日付形式のセッション名管理機能付き
"""

import os
import argparse
from pathlib import Path
import sys

# プロジェクトのlibディレクトリをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from db.database import BirdNetDB
from session_manager import LocationSpeciesDateManager, interactive_session_naming


def import_results_from_directory(directory_path: str, session_name: str = None, interactive: bool = False) -> dict:
    """ディレクトリ内の全CSVファイルをインポート"""
    
    directory = Path(directory_path)
    if not directory.exists():
        return {'success': False, 'error': f'Directory not found: {directory_path}'}
    
    # BirdNET結果CSVファイルを検索
    csv_files = list(directory.glob('*.BirdNET.results.csv'))
    
    if not csv_files:
        return {'success': False, 'error': 'No BirdNET result CSV files found'}
    
    db = BirdNetDB()
    
    # セッション名の決定
    if session_name is None:
        if interactive:
            session_name = interactive_session_naming(str(directory))
        else:
            # 自動生成（新形式）
            manager = LocationSpeciesDateManager()
            suggestion = manager.suggest_session_name(str(directory))
            session_name = suggestion['suggested_name']
            print(f"[INFO] 自動生成されたセッション名: {session_name}")
    
    session_id = db.create_session(
        session_name=session_name,
        model_name="BirdNET",
        model_type="default",
        description=f"Imported from {directory_path} using location+species+date format"
    )
    
    results = {
        'success': True,
        'session_id': session_id,
        'session_name': session_name,
        'total_files': len(csv_files),
        'imported_files': 0,
        'failed_files': 0,
        'total_detections': 0,
        'details': []
    }
    
    print(f"Importing {len(csv_files)} CSV files into session '{session_name}'...")
    
    for csv_file in csv_files:
        print(f"Processing: {csv_file.name}")
        
        try:
            import_result = db.import_csv_results(str(csv_file), session_id)
            
            if import_result['success']:
                results['imported_files'] += 1
                results['total_detections'] += import_result['detections_imported']
                print(f"  [OK] Imported {import_result['detections_imported']} detections")
            else:
                results['failed_files'] += 1
                print(f"  [ERROR] Failed: {import_result.get('error', 'Unknown error')}")
            
            results['details'].append(import_result)
            
        except Exception as e:
            results['failed_files'] += 1
            error_result = {
                'success': False,
                'error': str(e),
                'filename': csv_file.stem
            }
            results['details'].append(error_result)
            print(f"  [ERROR] Exception: {e}")
    
    print(f"\nImport completed:")
    print(f"  Session: '{session_name}' (ID: {session_id})")
    print(f"  Files: {results['imported_files']}/{results['total_files']} successful")
    print(f"  Detections: {results['total_detections']} total")
    
    # セッション名の解析結果を表示
    manager = LocationSpeciesDateManager()
    parsed = manager.parse_session_name(session_name)
    if parsed['valid']:
        print(f"  [INFO] 場所: {parsed['location']}")
        print(f"  [INFO] 種名: {', '.join(parsed['species'])}")
        print(f"  [INFO] 日付: {parsed['date']}")
    
    return results


def import_single_file(csv_file_path: str, session_name: str = None, interactive: bool = False) -> dict:
    """単一CSVファイルをインポート"""
    
    csv_path = Path(csv_file_path)
    if not csv_path.exists():
        return {'success': False, 'error': f'File not found: {csv_file_path}'}
    
    db = BirdNetDB()
    
    # セッション名の決定
    if session_name is None:
        if interactive:
            session_name = interactive_session_naming(csv_file_path)
        else:
            # 自動生成（新形式）
            manager = LocationSpeciesDateManager()
            suggestion = manager.suggest_session_name(csv_file_path)
            session_name = suggestion['suggested_name']
            print(f"[INFO] 自動生成されたセッション名: {session_name}")
    
    session_id = db.create_session(
        session_name=session_name,
        model_name="BirdNET",
        model_type="default",
        description=f"Imported from {csv_file_path} using location+species+date format"
    )
    
    print(f"Importing {csv_path.name} into session '{session_name}'...")
    
    try:
        import_result = db.import_csv_results(csv_file_path, session_id)
        
        if import_result['success']:
            print(f"[OK] Successfully imported {import_result['detections_imported']} detections")
        else:
            print(f"[ERROR] Import failed: {import_result.get('error', 'Unknown error')}")
        
        import_result['session_id'] = session_id
        import_result['session_name'] = session_name
        
        # セッション名の解析結果を表示
        manager = LocationSpeciesDateManager()
        parsed = manager.parse_session_name(session_name)
        if parsed['valid']:
            print(f"[INFO] 場所: {parsed['location']}")
            print(f"[INFO] 種名: {', '.join(parsed['species'])}")
            print(f"[INFO] 日付: {parsed['date']}")
        
        return import_result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'session_id': session_id,
            'session_name': session_name
        }


def create_smart_session_name(location: str, species: str, date: str = None) -> str:
    """場所+種名+日付形式のセッション名を作成するヘルパー"""
    manager = LocationSpeciesDateManager()
    species_list = [s.strip() for s in species.split(',')]
    return manager.create_session_name(location, species_list, date)


def show_sessions():
    """セッション一覧を表示（解析機能付き）"""
    db = BirdNetDB()
    sessions = db.get_sessions()
    manager = LocationSpeciesDateManager()
    
    print("\n[INFO] Database Sessions:")
    print("-" * 80)
    if not sessions:
        print("No sessions found.")
        return
    
    for session in sessions:
        print(f"ID: {session['id']}")
        print(f"Name: {session['session_name']}")
        
        # セッション名を解析
        parsed = manager.parse_session_name(session['session_name'])
        if parsed['valid']:
            print(f"  [INFO] 場所: {parsed['location']}")
            print(f"  [INFO] 種名: {', '.join(parsed['species'])}")
            print(f"  [INFO] 日付: {parsed['date']}")
        
        print(f"Model: {session['model_name']} ({session['model_type']})")
        print(f"Files: {session['file_count']}, Detections: {session['detection_count']}")
        print(f"Created: {session['created_at']}")
        print("-" * 80)


def show_stats():
    """統計情報を表示"""
    db = BirdNetDB()
    stats = db.get_statistics()
    print("\n[INFO] Database Statistics:")
    print("-" * 40)
    print(f"Sessions: {stats['session_count']}")
    print(f"Audio Files: {stats['file_count']}")
    print(f"Detections: {stats['detection_count']}")
    print(f"Species: {stats['species_count']}")
    
    if stats['avg_confidence']:
        print(f"Avg Confidence: {stats['avg_confidence']:.3f}")
    
    if stats['top_species']:
        print("\nTop Species:")
        for species in stats['top_species'][:5]:
            print(f"  {species['common_name']}: {species['detection_count']} detections")
    else:
        print("\nNo detection data found.")


def show_session_name_help():
    """セッション名形式のヘルプを表示"""
    print("\n[INFO] セッション名管理について")
    print("=" * 60)
    print("このツールは「場所+種名+日付」形式でセッション名を管理します。")
    print()
    print("[FORMAT] 形式: 場所_種名_日付")
    print("[EXAMPLE] 例: 奥多摩_ヨタカ_2024年6月29日")
    print()
    print("[USAGE] 使用方法:")
    print("  1. 自動生成: --session オプションを省略")
    print("  2. 対話形式: --interactive フラグを使用")
    print("  3. 手動指定: --session '場所_種名_日付'")
    print("  4. 快速作成: --location, --species, --date オプション")
    print()
    print("[SPECIES] 対応鳥種:")
    manager = LocationSpeciesDateManager()
    for species, (en_name, sci_name, _) in manager.SPECIES_MAP.items():
        print(f"  - {species} ({en_name})")
    print()
    print("[EXAMPLES] 使用例:")
    print("  python lib/import_results.py model/1 --interactive")
    print("  python lib/import_results.py model/1 --location '森林公園' --species 'ヨタカ'")
    print("  python lib/import_results.py model/1 --session '奥多摩_ヨタカ_2024年6月29日'")


def main():
    parser = argparse.ArgumentParser(description='Import BirdNET CSV results with smart session naming')
    parser.add_argument('path', nargs='?', help='CSV file or directory path')
    parser.add_argument('--session', '-s', help='Session name (supports location+species+date format)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive session naming')
    parser.add_argument('--location', '-l', help='Location for auto session naming')
    parser.add_argument('--species', '-sp', help='Species for auto session naming (comma-separated)')
    parser.add_argument('--date', '-d', help='Date for auto session naming')
    parser.add_argument('--list', action='store_true', help='List all sessions with analysis')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--help-naming', action='store_true', help='Show session naming help')
    
    args = parser.parse_args()
    
    # ヘルプ表示
    if args.help_naming:
        show_session_name_help()
        return
    
    # --listまたは--statsオプションの場合、pathは不要
    if args.list:
        show_sessions()
        return
    
    if args.stats:
        show_stats()
        return
    
    # pathが必要な場合のチェック
    if not args.path:
        print("Error: path argument is required when not using --list, --stats, or --help-naming")
        parser.print_help()
        sys.exit(1)
    
    # 場所+種名+日付形式での自動セッション名作成
    if args.location and args.species and not args.session:
        args.session = create_smart_session_name(args.location, args.species, args.date)
        print(f"[INFO] 自動作成されたセッション名: {args.session}")
    
    path = Path(args.path)
    
    if path.is_file():
        result = import_single_file(str(path), args.session, args.interactive)
    elif path.is_dir():
        result = import_results_from_directory(str(path), args.session, args.interactive)
    else:
        print(f"Error: Path not found: {args.path}")
        return
    
    if not result['success']:
        print(f"Import failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
