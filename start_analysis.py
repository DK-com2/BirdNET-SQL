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

# プロジェクトのlibディレクトリをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

from session_manager import LocationSpeciesDateManager


class BirdNetAnalyzer:
    """BirdNet音声解析クラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_folder = self.project_root / "data" / "audio" / "test"
        self.model_folder = self.project_root / "model"
        self.database_folder = self.project_root / "database"
        self.results_folder = self.database_folder / "analysis_results"
        
        # 結果保存フォルダを作成
        self.results_folder.mkdir(parents=True, exist_ok=True)
    
    def check_environment(self):
        """環境チェック"""
        print("[INFO] 環境をチェックしています...")
        
        # 仮想環境の確認
        if not (self.project_root / "venv").exists():
            print("[ERROR] 仮想環境が見つかりません。setup.batを実行してください。")
            return False
        
        # テストフォルダの確認
        if not self.test_folder.exists():
            print(f"[INFO] テストフォルダを作成しています: {self.test_folder}")
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
        print("  [3] テストフォルダを開く")
        print("  [4] 解析結果を表示")
        print("  [5] データベース統計")
        print("  [6] データベースビューアー")
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
        
        # 解析コマンド構築
        cmd = [
            sys.executable,
            str(self.project_root / "lib" / "birdnet" / "analyze.py"),
            "--i", str(self.test_folder),
            "--o", str(self.results_folder),  # 常にdatabase/analysis_resultsに出力
            "--overlap", "2",
            "--rtype", "csv",
            "--sensitivity", "1.5",
            "--min_conf", "0.01"
        ]
        
        # カスタムモデルの場合
        if model_path:
            cmd.extend(["--classifier", str(model_path)])
            cmd.extend(["--min_conf", "0.1"])  # カスタムモデル用の閾値
            print(f"[INFO] カスタムモデル使用: {model_path.parent.name}")
        else:
            print("[INFO] デフォルトモデル使用")
        
        print(f"[INFO] 出力先: {self.results_folder}")
        print()
        
        try:
            # 解析実行（文字エンコーディング対策）
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True, 
                                  encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                print("[OK] 解析が完了しました！")
                return str(self.results_folder)  # database/analysis_resultsを返す
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
            str(self.project_root / "lib" / "import_results_simple.py"),
            str(source_dir),
            "--session", session_name
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
            else:
                print("[WARNING] 解析は完了しましたが、DB保存に失敗しました")
                print(f"   結果は {output_dir} で確認できます")
        
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
                    else:
                        print("[WARNING] 解析は完了しましたが、DB保存に失敗しました")
                        print(f"   結果は {output_dir} で確認できます")
            else:
                print("[ERROR] 無効な選択です")
                
        except ValueError:
            print("[ERROR] 数字を入力してください")
        except KeyboardInterrupt:
            print("\n[WARNING] キャンセルされました")
        
        input("\nEnterキーを押してメニューに戻る...")
    
    def open_test_folder(self):
        """テストフォルダを開く"""
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
    
    def show_database_stats(self):
        """データベース統計を表示"""
        print()
        print("[INFO] データベース統計:")
        print("=" * 40)
        
        try:
            cmd = [sys.executable, str(self.project_root / "lib" / "import_results_simple.py"), "--stats"]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("[ERROR] 統計取得エラー:")
                print(result.stderr)
        
        except Exception as e:
            print(f"[ERROR] 統計表示エラー: {e}")
        
        print()
        print("[INFO] セッション一覧:")
        print("=" * 40)
        
        try:
            cmd = [sys.executable, str(self.project_root / "lib" / "import_results_simple.py"), "--list"]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("[ERROR] セッション一覧取得エラー:")
                print(result.stderr)
        
        except Exception as e:
            print(f"[ERROR] セッション一覧表示エラー: {e}")
        
        input("\nEnterキーを押してメニューに戻る...")
    
    def open_database_viewer(self):
        """データベースビューアーを開く"""
        print()
        print("🗃️ データベースビューアーを起動しています...")
        
        try:
            cmd = [sys.executable, str(self.project_root / "lib" / "view_database_simple.py")]
            subprocess.run(cmd, cwd=self.project_root)
        
        except Exception as e:
            print(f"[ERROR] ビューアー起動エラー: {e}")
            input("\nEnterキーを押してメニューに戻る...")
    
    def run(self):
        """メインループ"""
        if not self.check_environment():
            input("Enterキーを押して終了...")
            return
        
        while True:
            self.display_menu()
            
            try:
                choice = input("オプションを選択してください (0-6): ").strip()
                
                if choice == "1":
                    self.analyze_default()
                elif choice == "2":
                    self.analyze_custom()
                elif choice == "3":
                    self.open_test_folder()
                elif choice == "4":
                    self.view_results()
                elif choice == "5":
                    self.show_database_stats()
                elif choice == "6":
                    self.open_database_viewer()
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
    analyzer = BirdNetAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()
