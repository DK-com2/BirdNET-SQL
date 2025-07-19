"""
音声ファイル管理クラス
ファイルパス生成、検証、クリーンアップ機能
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# ロガー設定
logger = logging.getLogger(__name__)

class AudioFileManager:
    """音声ファイル管理クラス"""
    
    def __init__(self, project_root: str = None):
        """
        初期化
        
        Args:
            project_root: プロジェクトルートディレクトリ
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        
        self.project_root = Path(project_root)
        self.database_dir = self.project_root / "database"
        self.audio_segments_dir = self.database_dir / "audio_segments"
        self.spectrograms_dir = self.database_dir / "spectrograms"
        self.source_audio_dir = self.database_dir / "audio"
        
        # ディレクトリ存在確認・作成
        self._ensure_directories()
    
    def _ensure_directories(self):
        """必要なディレクトリの存在確認・作成"""
        directories = [
            self.audio_segments_dir,
            self.spectrograms_dir,
            self.source_audio_dir / "completed",
            self.source_audio_dir / "inbox",
            self.source_audio_dir / "failed"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"ディレクトリ確認: {directory}")
    
    def find_source_audio_file(self, filename_stem: str) -> Optional[str]:
        """
        元音声ファイルを検索
        
        Args:
            filename_stem: ファイル名（拡張子なし）
            
        Returns:
            見つかった音声ファイルの絶対パス、またはNone
        """
        # 検索対象ディレクトリ
        search_dirs = [
            self.source_audio_dir / "completed",
            self.source_audio_dir / "inbox"
        ]
        
        # 対応音声形式（WAVを優先）
        audio_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']
        
        for search_dir in search_dirs:
            for ext in audio_extensions:
                potential_path = search_dir / f"{filename_stem}{ext}"
                if potential_path.exists():
                    logger.debug(f"音声ファイル発見: {potential_path}")
                    return str(potential_path)
        
        # プロジェクト全体を検索（最終手段）
        for ext in audio_extensions:
            for audio_file in self.project_root.rglob(f"{filename_stem}{ext}"):
                if audio_file.exists():
                    logger.info(f"音声ファイル発見（全体検索）: {audio_file}")
                    return str(audio_file)
        
        logger.warning(f"音声ファイルが見つかりません: {filename_stem}")
        return None
    
    def generate_session_directory_name(self, session_name: str) -> str:
        """
        セッション名から適切なディレクトリ名を生成
        
        Args:
            session_name: セッション名
            
        Returns:
            サニタイズされたディレクトリ名
        """
        # ファイルシステムに安全な文字のみ残す
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        safe_name = "".join(c if c in safe_chars else "_" for c in session_name)
        
        # 長すぎる場合は短縮
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        return safe_name
    
    def get_relative_path(self, absolute_path: str, base_dir: str = "database") -> str:
        """
        絶対パスから相対パスを生成
        
        Args:
            absolute_path: 絶対パス
            base_dir: ベースディレクトリ名
            
        Returns:
            相対パス
        """
        abs_path = Path(absolute_path)
        
        # database ディレクトリからの相対パスを生成
        try:
            rel_path = abs_path.relative_to(self.database_dir)
            return str(rel_path).replace("\\", "/")  # Unix形式のパス区切り
        except ValueError:
            # database外のファイルの場合
            return str(abs_path).replace("\\", "/")
    
    def resolve_relative_path(self, relative_path: str) -> str:
        """
        相対パスから絶対パスを生成
        
        Args:
            relative_path: 相対パス（database/からの相対）
            
        Returns:
            絶対パス
        """
        # Unix形式パスをWindowsパスに変換
        normalized_path = relative_path.replace("/", os.sep)
        absolute_path = self.database_dir / normalized_path
        return str(absolute_path)
    
    def cleanup_failed_files(self, session_name: str) -> Dict[str, int]:
        """
        失敗したファイルのクリーンアップ
        
        Args:
            session_name: セッション名
            
        Returns:
            クリーンアップ統計
        """
        stats = {"audio_cleaned": 0, "spectrogram_cleaned": 0}
        
        try:
            # セッションディレクトリ
            audio_session_dir = self.audio_segments_dir / session_name
            spec_session_dir = self.spectrograms_dir / session_name
            
            # 不完全な音声ファイルをクリーンアップ
            if audio_session_dir.exists():
                for file_path in audio_session_dir.glob("*.mp3"):
                    if file_path.stat().st_size < 1024:  # 1KB未満のファイル
                        file_path.unlink()
                        stats["audio_cleaned"] += 1
                        logger.debug(f"不完全音声ファイル削除: {file_path}")
            
            # 不完全なスペクトログラムファイルをクリーンアップ
            if spec_session_dir.exists():
                for file_path in spec_session_dir.glob("*.png"):
                    if file_path.stat().st_size < 1024:  # 1KB未満のファイル
                        file_path.unlink()
                        stats["spectrogram_cleaned"] += 1
                        logger.debug(f"不完全スペクトログラム削除: {file_path}")
            
            logger.info(f"クリーンアップ完了: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"クリーンアップエラー: {e}")
            return stats
    
    def get_session_file_counts(self, session_name: str) -> Dict[str, int]:
        """
        セッションのファイル数統計を取得
        
        Args:
            session_name: セッション名
            
        Returns:
            ファイル数統計
        """
        stats = {"audio_segments": 0, "spectrograms": 0}
        
        try:
            # 音声セグメント数
            audio_session_dir = self.audio_segments_dir / session_name
            if audio_session_dir.exists():
                stats["audio_segments"] = len(list(audio_session_dir.glob("*.mp3")))
            
            # スペクトログラム数
            spec_session_dir = self.spectrograms_dir / session_name
            if spec_session_dir.exists():
                stats["spectrograms"] = len(list(spec_session_dir.glob("*.png")))
            
            return stats
            
        except Exception as e:
            logger.error(f"ファイル数統計エラー: {e}")
            return stats
    
    def validate_file_paths(self, detection_data: Dict) -> Tuple[bool, List[str]]:
        """
        検出データのファイルパス検証
        
        Args:
            detection_data: 検出データ辞書
            
        Returns:
            (検証成功フラグ, エラーメッセージリスト)
        """
        errors = []
        
        try:
            # 必須フィールド確認
            required_fields = ['filename', 'session_name', 'start_time_seconds', 'end_time_seconds']
            for field in required_fields:
                if field not in detection_data or detection_data[field] is None:
                    errors.append(f"必須フィールドが不足: {field}")
            
            if errors:
                return False, errors
            
            # 元音声ファイル存在確認
            source_audio = self.find_source_audio_file(detection_data['filename'])
            if source_audio is None:
                errors.append(f"元音声ファイルが見つかりません: {detection_data['filename']}")
            
            # 時刻範囲の妥当性確認（文字列形式も対応）
            try:
                start_time = self._parse_time_value(detection_data['start_time_seconds'])
                end_time = self._parse_time_value(detection_data['end_time_seconds'])
                
                if start_time < 0:
                    errors.append("開始時刻が負の値です")
                
                if end_time <= start_time:
                    errors.append("終了時刻が開始時刻以前です")
                    
            except ValueError as e:
                errors.append(f"時刻変換エラー: {str(e)}")
            
            # セッション名の妥当性確認
            session_name = detection_data['session_name']
            if not session_name or len(session_name.strip()) == 0:
                errors.append("セッション名が空です")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"検証エラー: {str(e)}")
            return False, errors
    
    def _parse_time_value(self, time_value) -> float:
        """
        時刻値を解析してfloat型に変換
        
        Args:
            time_value: 時刻値（float, int, または文字列）
            
        Returns:
            秒単位のfloat値
            
        Raises:
            ValueError: 変換できない場合
        """
        # 既にfloat/intの場合はそのまま返す
        if isinstance(time_value, (int, float)):
            return float(time_value)
        
        # 文字列の場合
        if isinstance(time_value, str):
            time_str = str(time_value).strip()
            
            # パターン1: "10m26s" 形式
            if 'm' in time_str and 's' in time_str:
                try:
                    # "10m26s" -> minutes=10, seconds=26
                    parts = time_str.replace('s', '').split('m')
                    if len(parts) == 2:
                        minutes = int(parts[0])
                        seconds = int(parts[1])
                        return minutes * 60 + seconds
                except (ValueError, IndexError):
                    pass
            
            # パターン2: "626.0" のような数値文字列
            try:
                return float(time_str)
            except ValueError:
                pass
            
            # パターン3: "10:26" のような mm:ss 形式
            if ':' in time_str:
                try:
                    parts = time_str.split(':')
                    if len(parts) == 2:
                        minutes = int(parts[0])
                        seconds = int(parts[1])
                        return minutes * 60 + seconds
                except (ValueError, IndexError):
                    pass
        
        # 変換できない場合
        raise ValueError(f"時刻値を変換できません: {time_value} (型: {type(time_value)})")
    
    def get_storage_usage(self) -> Dict[str, float]:
        """
        ストレージ使用量統計を取得
        
        Returns:
            使用量統計（MB単位）
        """
        stats = {
            "audio_segments_mb": 0.0,
            "spectrograms_mb": 0.0,
            "total_mb": 0.0
        }
        
        try:
            # 音声セグメント使用量（WAV形式）
            if self.audio_segments_dir.exists():
                for file_path in self.audio_segments_dir.rglob("*.wav"):
                    stats["audio_segments_mb"] += file_path.stat().st_size / (1024 * 1024)
            
            # スペクトログラム使用量
            if self.spectrograms_dir.exists():
                for file_path in self.spectrograms_dir.rglob("*.png"):
                    stats["spectrograms_mb"] += file_path.stat().st_size / (1024 * 1024)
            
            stats["total_mb"] = stats["audio_segments_mb"] + stats["spectrograms_mb"]
            
            return stats
            
        except Exception as e:
            logger.error(f"ストレージ使用量取得エラー: {e}")
            return stats
