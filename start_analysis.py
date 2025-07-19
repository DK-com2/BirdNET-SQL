#!/usr/bin/env python3
"""
BirdNet Audio Analysis Tool (Python版)
start_analysis.batの置き換え版
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import glob
import argparse

# プロジェクトのlibディレクトリをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

from db.session_manager import LocationSpeciesDateManager

# 終了コードの定義
EXIT_SUCCESS = 0        # 正常終了
EXIT_GENERAL_ERROR = 1  # 一般的なエラー
EXIT_NO_FILES = 2       # 音声ファイルなし
EXIT_MODEL_ERROR = 3    # モデルエラー
EXIT_ENV_ERROR = 4      # 環境エラー


class BirdNetAnalyzer:
    """BirdNet音声解析クラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_folder = self.project_root / "database" / "audio" / "inbox"  # 変更: inbox を解析対象に
        self.model_folder = self.project_root / "model"
        self.database_folder = self.project_root / "database"
        self.results_folder = self.database_folder / "analysis_results"
        self.quiet_mode = False  # 静謐モードフラグ
        
        # 結果保存フォルダを作成
        self.results_folder.mkdir(parents=True, exist_ok=True)
    
    def log(self, message):
        """ログ出力（quiet_mode対応）"""
        if not self.quiet_mode:
            print(message)
    
    def check_environment(self):
        """環境チェック"""
        self.log("[INFO] 環境をチェックしています...")
        
        # 仮想環境の確認
        if not (self.project_root / "venv").exists():
            self.log("[ERROR] 仮想環境が見つかりません。setup.batを実行してください。")
            return False
        
        # 音声フォルダの確認
        if not self.test_folder.exists():
            self.log(f"[INFO] 音声フォルダを作成しています: {self.test_folder}")
            self.test_folder.mkdir(parents=True, exist_ok=True)
        
        return True
    
    def get_audio_files(self):
        """音声ファイル一覧を取得"""
        if not self.test_folder.exists():
            return []
        
        audio_files = []
        for ext in ['*.mp3', '*.wav', '*.flac', '*.m4a']:
            audio_files.extend(self.test_folder.glob(ext))
        
        return audio_files
    
    def get_custom_models(self):
        """カスタムモデル一覧を取得"""
        if not self.model_folder.exists():
            return []
        
        custom_models = []
        for model_dir in self.model_folder.iterdir():
            if model_dir.is_dir() and (model_dir / "models.tflite").exists():
                custom_models.append(model_dir.name)
        
        return custom_models
    
    def display_menu(self):
        """メニュー表示"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 50)
        print("[BirdNet] Audio Analysis Tool")
        print("=" * 50)
        print()
        
        # 音声ファイル確認
        audio_files = self.get_audio_files()
        print("[FILES] 音声ファイル:")
        if audio_files:
            for file in audio_files:
                print(f"   - {file.name}")
        else:
            print("   (音声ファイルが見つかりません)")
        
        print()
        
        # モデル確認
        custom_models = self.get_custom_models()
        print("[MODELS] 利用可能なモデル:")
        print("   - default (BirdNET標準モデル)")
        for model in custom_models:
            print(f"   - {model} (カスタムモデル)")
        
        print()
        print("[MENU] オプション:")
        print("  [1] デフォルトモデルで解析 + DB保存")
        print("  [2] カスタムモデルで解析 + DB保存")
        print("  [3] inboxフォルダを開く")
        print("  [4] 解析結果を表示")
        print("  [0] 終了")
        print()
    
    def run_analysis(self, model_path=None, output_dir=None):
        """BirdNet解析実行"""
        if not self.get_audio_files():
            print("[ERROR] 解析する音声ファイルがありません。")
            print(f"   音声ファイルを {self.test_folder} に配置してください。")
            return False
        
        print("[INFO] BirdNet解析を開始しています...")
        print("   (数分かかる場合があります)")
        print()
        
        # 解析コマンド構築（高速化設定）
        cmd = [
            sys.executable,
            str(self.project_root / "lib" / "birdnet" / "analyze.py"),
            "--i", str(self.test_folder),
            "--o", str(self.results_folder),
            "--overlap", "2",
            "--rtype", "csv",
            "--sensitivity", "1.5",
            "--min_conf", "0.8",        # 0.25 → 0.8 (実用重視)
            "--threads", "12"             # 並列処理で高速化
        ]
        
        # カスタムモデルの場合
        if model_path:
            cmd.extend(["--classifier", str(model_path)])
            # カスタムモデル用の闾値を更新（既に設定済みの0.25を使用）
            # cmd.extend(["--min_conf", "0.25"])  # 既に上で設定済み
            print(f"[INFO] カスタムモデル使用: {model_path.parent.name} (信頼度: 0.8)")
        else:
            print("[INFO] デフォルトモデル使用 (信頼度: 0.8)")
        
        print(f"[INFO] 出力先: {self.results_folder}")
        print(f"[INFO] 並列処理: 12スレッド")
        print(f"[DEBUG] 実行コマンド: {' '.join(cmd)}")
        print()
        
        try:
            # 解析実行（文字エンコーディング対策）
            # 環境変数でUTF-8を強制
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            print("[DEBUG] BirdNET解析を開始...")
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True, 
                                  encoding='utf-8', errors='replace', env=env)
            
            print("[DEBUG] BirdNET出力:")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("[DEBUG] BirdNETエラー:")
                print(result.stderr)
            
            if result.returncode == 0:
                print("[OK] 解析が完了しました！")
                return str(self.results_folder)
            else:
                print("[ERROR] 解析中にエラーが発生しました:")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ 解析実行エラー: {e}")
            return False
    
    def move_results_to_database_folder(self, source_dir, session_name):
        """解析結果をdatabase/analysis_resultsに移動"""
        source_path = Path(source_dir)
        
        # CSVファイルを検索
        csv_files = list(source_path.glob("*.BirdNET.results.csv"))
        
        if not csv_files:
            print("[WARNING] CSVファイルが見つかりませんでした")
            return []
        
        moved_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for csv_file in csv_files:
            # 新しいファイル名を生成
            safe_session_name = "".join(c for c in session_name if c.isalnum() or c in (' ', '_', '-')).strip()
            safe_session_name = safe_session_name.replace(' ', '_')
            
            new_filename = f"{timestamp}_{safe_session_name}_{csv_file.name}"
            dest_path = self.results_folder / new_filename
            
            try:
                # ファイルをコピー
                shutil.copy2(csv_file, dest_path)
                moved_files.append(dest_path)
                print(f"[INFO] 保存: {dest_path.name}")
                
            except Exception as e:
                print(f"[ERROR] ファイル移動エラー: {e}")
        
        return moved_files
    
    def save_to_database(self, source_dir, model_name="default"):
        """解析結果をデータベースに保存"""
        print()
        print("[INFO] データベースに保存しています...")
        
        # セッション名の入力
        print()
        session_name = input("セッション名を入力してください (Enterで自動生成): ").strip()
        
        if not session_name:
            # 自動生成
            manager = LocationSpeciesDateManager()
            suggestion = manager.suggest_session_name(str(source_dir))
            session_name = suggestion['suggested_name']
            print(f"[INFO] 自動生成: {session_name}")
        
        # 結果ファイルの確認（すでにdatabase/analysis_resultsにある）
        csv_files = list(Path(source_dir).glob("*.BirdNET.results.csv"))
        
        if not csv_files:
            print("[ERROR] 保存するファイルがありません")
            return False
        
        print(f"[INFO] CSVファイルを確認: {len(csv_files)}件")
        for csv_file in csv_files:
            print(f"  - {csv_file.name}")
        
        # データベースにインポート
        cmd = [
            sys.executable,
            str(self.project_root / "lib" / "db" / "import_results_simple.py"),
            str(source_dir),
            "--session", session_name,
            "--model", model_name,  # モデル名を渡す
            "--model-type", "custom" if model_name != "default" else "default"  # モデルタイプを渡す
        ]
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True, 
                                  encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                print("[OK] データベースへの保存が完了しました！")
                print(f"[INFO] セッション: {session_name}")
                print(f"[INFO] CSVファイル: {len(csv_files)}件を database/analysis_results/ に保存済み")
                print()
                
                # 統計表示
                self.show_import_result(result.stdout)
                return True
            else:
                print("[ERROR] データベース保存中にエラーが発生しました:")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"[ERROR] データベース保存エラー: {e}")
            return False
    
    def show_import_result(self, output):
        """インポート結果を表示"""
        lines = output.split('\n')
        for line in lines:
            # 文字化けしそうな特殊文字をフィルタリング
            if any(keyword in line for keyword in ['Session:', 'Files:', 'Detections:']):
                # 安全な文字だけを抽出
                safe_line = ''.join(c for c in line if ord(c) < 127 or c.isalnum() or c in ' ():,-')
                if safe_line.strip():  # 空でない場合のみ表示
                    print(f"  {safe_line}")
    
    def analyze_default(self):
        """デフォルトモデルで解析"""
        print()
        print("[INFO] デフォルトBirdNETモデルで解析します")
        
        output_dir = self.run_analysis()
        if output_dir:
            if self.save_to_database(output_dir, "default"):
                print("[SUCCESS] 解析とDB保存が完了しました！")
                self.move_files_after_analysis(True, "default_session")
            else:
                print("[WARNING] 解析は完了しましたが、DB保存に失敗しました")
                print(f"   結果は {output_dir} で確認できます")
                self.move_files_after_analysis(False, "default_session")
        else:
            self.move_files_after_analysis(False, "default_session")
        
        input("\nEnterキーを押してメニューに戻る...")
    
    def analyze_custom(self):
        """カスタムモデルで解析"""
        custom_models = self.get_custom_models()
        
        if not custom_models:
            print("[ERROR] カスタムモデルが見つかりません！")
            print("   カスタムモデルを先に作成してください。")
            input("\nEnterキーを押してメニューに戻る...")
            return
        
        print()
        print("[INFO] カスタムモデル一覧:")
        for i, model in enumerate(custom_models, 1):
            print(f"  {i}. {model}")
        
        print()
        try:
            choice = int(input(f"モデルを選択してください (1-{len(custom_models)}): ")) - 1
            
            if 0 <= choice < len(custom_models):
                selected_model = custom_models[choice]
                model_dir = self.model_folder / selected_model
                model_path = model_dir / "models.tflite"
                
                print(f"[INFO] カスタムモデル '{selected_model}' で解析します")
                
                output_dir = self.run_analysis(model_path)
                if output_dir:
                    if self.save_to_database(output_dir, selected_model):
                        print("[SUCCESS] 解析とDB保存が完了しました！")
                        self.move_files_after_analysis(True, f"{selected_model}_session")
                    else:
                        print("[WARNING] 解析は完了しましたが、DB保存に失敗しました")
                        print(f"   結果は {output_dir} で確認できます")
                        self.move_files_after_analysis(False, f"{selected_model}_session")
                else:
                    self.move_files_after_analysis(False, f"{selected_model}_session")
            else:
                print("[ERROR] 無効な選択です")
                
        except ValueError:
            print("[ERROR] 数字を入力してください")
        except KeyboardInterrupt:
            print("\n[WARNING] キャンセルされました")
        
        input("\nEnterキーを押してメニューに戻る...")
    
    def move_files_after_analysis(self, success: bool, session_name: str):
        """解析後のファイル移動"""
        audio_files = self.get_audio_files()
        if not audio_files:
            return
        
        # 移動先フォルダを決定
        if success:
            dest_folder = self.project_root / "database" / "audio" / "completed"
            print(f"[INFO] 解析成功: {len(audio_files)}件のファイルをcompletedフォルダに移動")
        else:
            dest_folder = self.project_root / "database" / "audio" / "failed"
            print(f"[INFO] 解析失敗: {len(audio_files)}件のファイルをfailedフォルダに移動")
        
        dest_folder.mkdir(exist_ok=True)
        
        # ファイル移動
        for audio_file in audio_files:
            try:
                dest_path = dest_folder / audio_file.name
                shutil.move(str(audio_file), str(dest_path))
                print(f"  移動: {audio_file.name}")
            except Exception as e:
                print(f"  [ERROR] ファイル移動エラー {audio_file.name}: {e}")
    
    def open_inbox_folder(self):
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.test_folder)
            else:  # macOS/Linux
                subprocess.run(['open', self.test_folder])
        except Exception as e:
            print(f"[ERROR] フォルダを開けませんでした: {e}")
    
    def view_results(self):
        """解析結果を表示"""
        print()
        print("[INFO] 解析結果:")
        print("=" * 40)
        
        # database/analysis_resultsの結果
        print("\n[INFO] 保存済み解析結果 (database/analysis_results/):")
        result_files = list(self.results_folder.glob("*.csv"))
        
        if result_files:
            for file in sorted(result_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                print(f"   - {file.name} ({mtime.strftime('%Y-%m-%d %H:%M')})")
            
            if len(result_files) > 5:
                print(f"   ... 他 {len(result_files) - 5} 件")
        else:
            print("   (保存済み結果がありません)")
        
        # 最新の解析結果を表示
        print("\n[INFO] 最新の解析結果:")
        latest_files = []
        
        # デフォルトモデル結果
        latest_files.extend(self.test_folder.glob("*.BirdNET.results.csv"))
        
        # カスタムモデル結果
        for model_dir in self.model_folder.glob("*"):
            if model_dir.is_dir():
                latest_files.extend(model_dir.glob("*.BirdNET.results.csv"))
        
        if latest_files:
            # 最新のファイルを表示
            latest_file = max(latest_files, key=lambda x: x.stat().st_mtime)
            print(f"   ファイル: {latest_file.name}")
            print(f"   場所: {latest_file.parent}")
            print(f"   作成日時: {datetime.fromtimestamp(latest_file.stat().st_mtime)}")
            
            print("\n[INFO] 内容のプレビュー:")
            try:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines[:10]):  # 最初の10行
                        print(f"   {i+1:2d}: {line.strip()}")
                    
                    if len(lines) > 10:
                        print(f"   ... (全{len(lines)}行)")
            except Exception as e:
                print(f"   [ERROR] ファイル読み込みエラー: {e}")
        else:
            print("   (解析結果がありません)")
        
        input("\nEnterキーを押してメニューに戻る...")
    
    def run_automated(self, args):
        """自動モード実行"""
        self.quiet_mode = args.quiet
        
        if not self.check_environment():
            return EXIT_ENV_ERROR
        
        try:
            if args.action == "analyze":
                return self.execute_analysis_auto(args.model, args.session)
            elif args.action == "view_results":
                return self.show_results_auto()
            elif args.action == "open_inbox":
                return self.open_inbox_auto()
            else:
                self.log(f"[ERROR] 不明なアクション: {args.action}")
                return EXIT_GENERAL_ERROR
        except Exception as e:
            self.log(f"[ERROR] 予期しないエラー: {e}")
            return EXIT_GENERAL_ERROR
    
    def execute_analysis_auto(self, model_name, session_name):
        """自動解析実行（input()なし版）"""
        try:
            # 音声ファイルの確認
            audio_files = self.get_audio_files()
            if not audio_files:
                self.log("[INFO] 解析対象のファイルがありません")
                return EXIT_NO_FILES
            
            self.log(f"[INFO] 解析開始: {len(audio_files)}件のファイル")
            
            # モデルパスの決定
            model_path = None
            if model_name != "default":
                model_dir = self.model_folder / model_name
                if not model_dir.exists():
                    self.log(f"[ERROR] モデル '{model_name}' が見つかりません")
                    return EXIT_MODEL_ERROR
                model_path = model_dir / "models.tflite"
                if not model_path.exists():
                    self.log(f"[ERROR] モデルファイル '{model_path}' が見つかりません")
                    return EXIT_MODEL_ERROR
            
            # セッション名の決定
            if not session_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                session_name = f"auto_{model_name}_{timestamp}"
            
            # 解析実行
            output_dir = self.run_analysis(model_path)
            if not output_dir:
                self.log("[ERROR] 解析に失敗しました")
                self.move_files_after_analysis(False, session_name)
                return EXIT_GENERAL_ERROR
            
            # データベース保存
            if self.save_to_database_auto(output_dir, model_name, session_name):
                self.log(f"[SUCCESS] 解析完了: セッション '{session_name}'")
                self.move_files_after_analysis(True, session_name)
                return EXIT_SUCCESS
            else:
                self.log("[ERROR] データベース保存に失敗しました")
                self.move_files_after_analysis(False, session_name)
                return EXIT_GENERAL_ERROR
                
        except Exception as e:
            self.log(f"[ERROR] 解析中のエラー: {e}")
            return EXIT_GENERAL_ERROR
    
    def save_to_database_auto(self, source_dir, model_name, session_name):
        """自動実行用のデータベース保存（input()なし）"""
        self.log("[INFO] データベースに保存中...")
        
        csv_files = list(Path(source_dir).glob("*.BirdNET.results.csv"))
        if not csv_files:
            self.log("[ERROR] 保存するCSVファイルがありません")
            return False
        
        self.log(f"[INFO] CSVファイルを確認: {len(csv_files)}件")
        
        # データベースにインポート
        cmd = [
            sys.executable,
            str(self.project_root / "lib" / "db" / "import_results_simple.py"),
            str(source_dir),
            "--session", session_name,
            "--model", model_name,
            "--model-type", "custom" if model_name != "default" else "default"
        ]
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, 
                                  text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                self.log(f"[OK] データベースへの保存が完了しました！")
                self.log(f"[INFO] セッション: {session_name}")
                self.log(f"[INFO] CSVファイル: {len(csv_files)}件を database/analysis_results/ に保存済み")
                return True
            else:
                self.log("[ERROR] データベース保存中にエラーが発生しました:")
                if not self.quiet_mode:
                    self.log(result.stderr)
                return False
                
        except Exception as e:
            self.log(f"[ERROR] データベース保存エラー: {e}")
            return False
    
    def show_results_auto(self):
        """解析結果を表示（自動モード）"""
        self.log("[INFO] 解析結果:")
        self.log("=" * 40)
        
        # database/analysis_resultsの結果
        result_files = list(self.results_folder.glob("*.csv"))
        
        if result_files:
            self.log(f"[INFO] 保存済み解析結果: {len(result_files)}件")
            for file in sorted(result_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                self.log(f"   - {file.name} ({mtime.strftime('%Y-%m-%d %H:%M')})")
            
            if len(result_files) > 5:
                self.log(f"   ... 他 {len(result_files) - 5} 件")
        else:
            self.log("[INFO] 保存済み結果がありません")
        
        return EXIT_SUCCESS
    
    def open_inbox_auto(self):
        """inboxフォルダを開く（自動モード）"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.test_folder)
            else:  # macOS/Linux
                subprocess.run(['open', self.test_folder])
            self.log(f"[INFO] inboxフォルダを開きました: {self.test_folder}")
            return EXIT_SUCCESS
        except Exception as e:
            self.log(f"[ERROR] フォルダを開けませんでした: {e}")
            return EXIT_GENERAL_ERROR
    
    def run_interactive(self):
        """対話モード（従来のrun()メソッド）"""
        if not self.check_environment():
            input("Enterキーを押して終了...")
            return
        
        while True:
            self.display_menu()
            
            try:
                choice = input("オプションを選択してください (0-4): ").strip()
                
                if choice == "1":
                    self.analyze_default()
                elif choice == "2":
                    self.analyze_custom()
                elif choice == "3":
                    self.open_inbox_folder()
                elif choice == "4":
                    self.view_results()
                elif choice == "0":
                    print("[INFO] さようなら！")
                    break
                else:
                    print("[ERROR] 無効な選択です")
                    input("Enterキーを押して続行...")
            
            except KeyboardInterrupt:
                print("\n[INFO] さようなら！")
                break
            except Exception as e:
                print(f"[ERROR] エラーが発生しました: {e}")
                input("Enterキーを押して続行...")


def main():
    """メイン関数"""
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="BirdNet Audio Analysis Tool")
    parser.add_argument('--auto', action='store_true', 
                       help='自動モードで実行（メニューを表示せず直接実行）')
    parser.add_argument('--action', choices=['analyze', 'view_results', 'open_inbox'],
                       help='実行する処理')
    parser.add_argument('--model', default='default',
                       help='使用するモデル名 (default: %(default)s)')
    parser.add_argument('--session', 
                       help='セッション名（省略時は自動生成）')
    parser.add_argument('--quiet', action='store_true',
                       help='静謐モード（ログ出力を最小限に）')
    
    args = parser.parse_args()
    
    analyzer = BirdNetAnalyzer()
    
    # モードによる分岐
    if args.auto:
        # 自動モード: 新機能
        if not args.action:
            print("[ERROR] --auto モードでは --action の指定が必要です")
            parser.print_help()
            sys.exit(EXIT_GENERAL_ERROR)
        
        exit_code = analyzer.run_automated(args)
        sys.exit(exit_code)
    else:
        # 対話モード: 従来の動作
        analyzer.run_interactive()


if __name__ == "__main__":
    main()
