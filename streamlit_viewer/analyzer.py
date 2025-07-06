"""
BirdNet解析モジュール（最小版）
start_analysis.pyの機能を最小限で実装
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


class SimpleBirdNetAnalyzer:
    """最小限のBirdNet解析クラス"""
    
    def __init__(self):
        # プロジェクトルートを取得
        current_file = Path(__file__).resolve()
        self.project_root = current_file.parent.parent
        
        # 必要なパス
        self.audio_folder = self.project_root / "database" / "audio" / "inbox"
        self.model_folder = self.project_root / "model"
        self.results_folder = self.project_root / "database" / "analysis_results"
        
        # 結果フォルダ作成
        self.results_folder.mkdir(parents=True, exist_ok=True)
    
    def get_audio_files(self) -> List[str]:
        """音声ファイル名一覧を取得"""
        if not self.audio_folder.exists():
            return []
        
        files = []
        for ext in ['*.mp3', '*.wav', '*.flac', '*.m4a']:
            files.extend([f.name for f in self.audio_folder.glob(ext)])
        
        return sorted(files)
    
    def get_custom_models(self) -> List[str]:
        """カスタムモデル一覧を取得"""
        if not self.model_folder.exists():
            return []
        
        models = []
        for model_dir in self.model_folder.iterdir():
            if model_dir.is_dir() and (model_dir / "models.tflite").exists():
                models.append(model_dir.name)
        
        return sorted(models)
    
    def run_analysis(self, model_name: str) -> Tuple[bool, str]:
        """解析実行"""
        # 音声ファイルチェック
        audio_files = self.get_audio_files()
        if not audio_files:
            return False, "音声ファイルがありません"
        
        # コマンド構築
        cmd = [
            sys.executable,
            str(self.project_root / "lib" / "birdnet" / "analyze.py"),
            "--i", str(self.audio_folder),
            "--o", str(self.results_folder),
            "--rtype", "csv",
            "--min_conf", "0.01"
        ]
        
        # カスタムモデル設定
        if model_name != "default":
            model_path = self.model_folder / model_name / "models.tflite"
            if not model_path.exists():
                return False, f"モデルが見つかりません: {model_name}"
            cmd.extend(["--classifier", str(model_path), "--min_conf", "0.1"])
        
        try:
            # 実行
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, 
                                  text=True, encoding='utf-8', errors='replace', env=env)
            
            if result.returncode == 0:
                return True, f"解析完了: {len(audio_files)}件処理"
            else:
                return False, f"解析エラー: {result.stderr[:200]}"
        
        except Exception as e:
            return False, f"実行エラー: {str(e)}"
    
    def save_to_db(self, session_name: str, model_name: str) -> Tuple[bool, str]:
        """データベース保存"""
        model_type = "custom" if model_name != "default" else "default"
        
        cmd = [
            sys.executable,
            str(self.project_root / "lib" / "db" / "import_results_simple.py"),
            str(self.results_folder),
            "--session", session_name,
            "--model", model_name,
            "--model-type", model_type
        ]
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True,
                                  text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                return True, f"DB保存完了: {session_name}"
            else:
                return False, f"DB保存エラー: {result.stderr[:200]}"
        
        except Exception as e:
            return False, f"DB保存エラー: {str(e)}"
    
    def move_files_after_analysis(self, success: bool) -> None:
        """解析後のファイル移動"""
        import shutil
        
        audio_files = [self.audio_folder / f for f in self.get_audio_files()]
        if not audio_files:
            return
        
        # 移動先フォルダを決定
        if success:
            dest_folder = self.project_root / "database" / "audio" / "completed"
        else:
            dest_folder = self.project_root / "database" / "audio" / "failed"
        
        dest_folder.mkdir(exist_ok=True)
        
        # ファイル移動
        for audio_file in audio_files:
            try:
                dest_path = dest_folder / audio_file.name
                shutil.move(str(audio_file), str(dest_path))
            except Exception:
                pass  # Streamlitではエラーを無視
