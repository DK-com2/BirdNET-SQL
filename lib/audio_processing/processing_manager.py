"""
統合処理管理クラス
音声セグメントとスペクトログラムの生成を統合管理
"""

import sqlite3
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

# プロジェクトのlibディレクトリをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from .segment_generator import AudioSegmentGenerator
from .spectrogram_generator import SpectrogramGenerator
from .file_manager import AudioFileManager

# ロガー設定
logger = logging.getLogger(__name__)

class ProcessingManager:
    """音声セグメント処理統合管理クラス"""
    
    def __init__(self, db_path: str = None, enable_spectrogram: bool = True):
        """
        初期化
        
        Args:
            db_path: データベースファイルパス
            enable_spectrogram: スペクトログラム生成を有効にするか
        """
        # データベースパス設定
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "database" / "result.db"
        
        self.db_path = Path(db_path)
        self.enable_spectrogram = enable_spectrogram
        
        # 各コンポーネント初期化
        self.segment_generator = AudioSegmentGenerator()
        self.spectrogram_generator = SpectrogramGenerator() if enable_spectrogram else None
        self.file_manager = AudioFileManager()
        
        # 処理統計
        self.stats = {
            "processed_count": 0,
            "success_count": 0,
            "audio_success": 0,
            "spectrogram_success": 0,
            "error_count": 0,
            "errors": []
        }
    
    def process_all_pending_detections(self, batch_size: int = 100) -> Dict:
        """
        未処理の全検出結果を一括処理
        
        Args:
            batch_size: バッチサイズ
            
        Returns:
            処理結果統計
        """
        logger.info("未処理検出結果の一括処理を開始")
        
        try:
            # 未処理レコード取得
            pending_detections = self._get_pending_detections()
            total_count = len(pending_detections)
            
            if total_count == 0:
                logger.info("処理対象の未処理レコードはありません")
                return self.stats
            
            logger.info(f"処理対象レコード数: {total_count}")
            
            # バッチ処理
            for i in range(0, total_count, batch_size):
                batch = pending_detections[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_count + batch_size - 1) // batch_size
                
                logger.info(f"バッチ {batch_num}/{total_batches} 処理中 ({len(batch)}件)")
                
                for detection in batch:
                    self._process_single_detection(detection)
                
                # 進捗表示
                processed_so_far = min(i + batch_size, total_count)
                progress = (processed_so_far / total_count) * 100
                logger.info(f"進捗: {processed_so_far}/{total_count} ({progress:.1f}%)")
            
            # 最終統計
            self.stats["total_pending"] = total_count
            success_rate = (self.stats["success_count"] / total_count * 100) if total_count > 0 else 0
            
            logger.info(f"一括処理完了 - 成功: {self.stats['success_count']}/{total_count} ({success_rate:.1f}%)")
            
            return self.stats
            
        except Exception as e:
            error_msg = f"一括処理エラー: {str(e)}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
            return self.stats
    
    def process_single_detection(self, detection_id: int) -> Tuple[bool, str]:
        """
        単一検出結果を処理
        
        Args:
            detection_id: 検出ID
            
        Returns:
            (成功フラグ, メッセージ)
        """
        try:
            # 検出データ取得
            detection = self._get_detection_by_id(detection_id)
            if not detection:
                return False, f"検出ID {detection_id} が見つかりません"
            
            # 処理実行
            return self._process_single_detection(detection)
            
        except Exception as e:
            error_msg = f"単一処理エラー (ID:{detection_id}): {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _process_single_detection(self, detection: Dict) -> Tuple[bool, str]:
        """
        単一検出データの処理実行
        
        Args:
            detection: 検出データ辞書
            
        Returns:
            (成功フラグ, メッセージ)
        """
        detection_id = detection['id']
        self.stats["processed_count"] += 1
        
        try:
            # データ検証
            is_valid, errors = self.file_manager.validate_file_paths(detection)
            if not is_valid:
                error_msg = f"検証エラー (ID:{detection_id}): {'; '.join(errors)}"
                logger.warning(error_msg)
                self.stats["error_count"] += 1
                self.stats["errors"].append(error_msg)
                return False, error_msg
            
            # 元音声ファイル検索
            source_audio_path = self.file_manager.find_source_audio_file(detection['filename'])
            if not source_audio_path:
                error_msg = f"元音声ファイル未発見 (ID:{detection_id}): {detection['filename']}"
                logger.warning(error_msg)
                self.stats["error_count"] += 1
                self.stats["errors"].append(error_msg)
                return False, error_msg
            
            # セッションディレクトリ名生成
            session_dir_name = self.file_manager.generate_session_directory_name(detection['session_name'])
            
            audio_path = None
            spectrogram_path = None
            
            # 音声セグメント生成
            audio_success, audio_rel_path, audio_error = self.segment_generator.generate_segment(
                source_audio_path=source_audio_path,
                start_time=self.file_manager._parse_time_value(detection['start_time_seconds']),
                end_time=self.file_manager._parse_time_value(detection['end_time_seconds']),
                session_name=session_dir_name,
                detection_id=detection_id,
                species_name=detection.get('common_name', 'Unknown'),
                confidence=detection['confidence']
            )
            
            if audio_success:
                audio_path = audio_rel_path
                self.stats["audio_success"] += 1
                logger.debug(f"音声セグメント生成成功 (ID:{detection_id})")
            else:
                logger.warning(f"音声セグメント生成失敗 (ID:{detection_id}): {audio_error}")
            
            # スペクトログラム生成（有効な場合のみ）
            if self.enable_spectrogram and audio_success:
                # 音声セグメントの絶対パス取得（MP3統一）
                audio_abs_path = self.file_manager.resolve_relative_path(audio_rel_path)
                
                spec_success, spec_rel_path, spec_error = self.spectrogram_generator.generate_spectrogram(
                    audio_segment_path=audio_abs_path,
                    session_name=session_dir_name,
                    detection_id=detection_id,
                    species_name=detection.get('common_name', 'Unknown'),
                    confidence=detection['confidence']
                )
                
                if spec_success:
                    spectrogram_path = spec_rel_path
                    self.stats["spectrogram_success"] += 1
                    logger.debug(f"スペクトログラム生成成功 (ID:{detection_id})")
                else:
                    logger.warning(f"スペクトログラム生成失敗 (ID:{detection_id}): {spec_error}")
            
            # データベース更新
            update_success = self._update_detection_paths(
                detection_id, audio_path, spectrogram_path
            )
            
            if update_success:
                if audio_success:
                    self.stats["success_count"] += 1
                    message = f"処理完了 (ID:{detection_id}) - 音声: {audio_success}, スペクトログラム: {spectrogram_path is not None}"
                    logger.debug(message)
                    return True, message
                else:
                    error_msg = f"音声セグメント生成失敗 (ID:{detection_id})"
                    self.stats["error_count"] += 1
                    self.stats["errors"].append(error_msg)
                    return False, error_msg
            else:
                error_msg = f"データベース更新失敗 (ID:{detection_id})"
                self.stats["error_count"] += 1
                self.stats["errors"].append(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"処理実行エラー (ID:{detection_id}): {str(e)}"
            logger.error(error_msg)
            self.stats["error_count"] += 1
            self.stats["errors"].append(error_msg)
            return False, error_msg
    
    def _get_pending_detections(self) -> List[Dict]:
        """
        未処理検出結果を取得
        
        Returns:
            未処理検出データのリスト
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM bird_detections 
                    WHERE audio_segment_path IS NULL
                    ORDER BY created_at ASC
                """)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"未処理レコード取得エラー: {e}")
            return []
    
    def _get_detection_by_id(self, detection_id: int) -> Optional[Dict]:
        """
        ID指定で検出データを取得
        
        Args:
            detection_id: 検出ID
            
        Returns:
            検出データ辞書またはNone
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM bird_detections 
                    WHERE id = ?
                """, (detection_id,))
                
                row = cursor.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"検出データ取得エラー (ID:{detection_id}): {e}")
            return None
    
    def _update_detection_paths(self, detection_id: int, audio_path: Optional[str], spectrogram_path: Optional[str]) -> bool:
        """
        検出レコードのファイルパス情報を更新
        
        Args:
            detection_id: 検出ID
            audio_path: 音声セグメントパス
            spectrogram_path: スペクトログラムパス
            
        Returns:
            更新成功フラグ
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE bird_detections 
                    SET audio_segment_path = ?, spectrogram_path = ?
                    WHERE id = ?
                """, (audio_path, spectrogram_path, detection_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.debug(f"パス情報更新完了 (ID:{detection_id})")
                    return True
                else:
                    logger.warning(f"更新対象レコードなし (ID:{detection_id})")
                    return False
                    
        except Exception as e:
            logger.error(f"パス情報更新エラー (ID:{detection_id}): {e}")
            return False
    
    def get_processing_statistics(self) -> Dict:
        """
        処理統計情報を取得
        
        Returns:
            統計情報辞書
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 基本統計
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_detections,
                        COUNT(audio_segment_path) as processed_audio,
                        COUNT(spectrogram_path) as processed_spectrogram,
                        COUNT(*) - COUNT(audio_segment_path) as pending_audio
                    FROM bird_detections
                """)
                
                row = cursor.fetchone()
                stats = {
                    "total_detections": row[0],
                    "processed_audio": row[1], 
                    "processed_spectrogram": row[2],
                    "pending_audio": row[3]
                }
                
                # 進捗率計算
                if stats['total_detections'] > 0:
                    stats['audio_progress_percent'] = (stats['processed_audio'] / stats['total_detections']) * 100
                    stats['spectrogram_progress_percent'] = (stats['processed_spectrogram'] / stats['total_detections']) * 100
                else:
                    stats['audio_progress_percent'] = 0
                    stats['spectrogram_progress_percent'] = 0
                
                # ストレージ使用量
                storage_stats = self.file_manager.get_storage_usage()
                stats.update(storage_stats)
                
                # 現在の処理セッション統計
                stats.update(self.stats)
                
                return stats
                
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            return self.stats
    
    def reset_processing_stats(self):
        """
        処理統計をリセット
        """
        self.stats = {
            "processed_count": 0,
            "success_count": 0,
            "audio_success": 0,
            "spectrogram_success": 0,
            "error_count": 0,
            "errors": []
        }
        logger.debug("処理統計をリセットしました")
