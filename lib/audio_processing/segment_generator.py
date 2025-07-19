"""
音声セグメント生成クラス
MP3ファイルから検出結果に基づく音声セグメントを生成
"""

import os
import librosa
import soundfile as sf
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import logging

# ロガー設定
logger = logging.getLogger(__name__)

class AudioSegmentGenerator:
    """MP3音声セグメント生成クラス"""
    
    def __init__(self, base_output_dir: str = None):
        """
        初期化
        
        Args:
            base_output_dir: 出力ベースディレクトリ（デフォルト: database/audio_segments）
        """
        if base_output_dir is None:
            # プロジェクトルートからの相対パス
            project_root = Path(__file__).parent.parent.parent
            base_output_dir = project_root / "database" / "audio_segments"
        
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 音声処理設定
        self.context_seconds = 5.0  # 前後5秒のコンテキスト
        self.sample_rate = None  # 元ファイルのサンプリングレートを使用
        
    def generate_segment(
        self, 
        source_audio_path: str,
        start_time: float,
        end_time: float,
        session_name: str,
        detection_id: int,
        species_name: str,
        confidence: float
    ) -> Tuple[bool, str, Optional[str]]:
        """
        音声セグメントを生成
        
        Args:
            source_audio_path: 元音声ファイルパス
            start_time: 検出開始時刻（秒）
            end_time: 検出終了時刻（秒） 
            session_name: セッション名
            detection_id: 検出ID
            species_name: 種名
            confidence: 信頼度
            
        Returns:
            (成功フラグ, 出力ファイルパス, エラーメッセージ)
        """
        try:
            source_path = Path(source_audio_path)
            
            # 元ファイル存在確認
            if not source_path.exists():
                return False, "", f"元音声ファイルが見つかりません: {source_path}"
            
            # 出力ディレクトリ作成
            session_dir = self.base_output_dir / session_name
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # 出力ファイル名生成
            output_filename = self._generate_filename(detection_id, species_name, confidence)
            output_path = session_dir / output_filename
            
            # librosaで音声処理（高品質・安定）
            success, actual_output_path = self._extract_segment_librosa(
                source_path, output_path, start_time, end_time
            )
            
            if success:
                # 相対パス返却（database/からの相対パス）
                # 実際に生成されたファイルパスを使用
                actual_filename = actual_output_path.name
                relative_path = f"audio_segments/{session_name}/{actual_filename}"
                logger.info(f"音声セグメント生成完了: {relative_path}")
                return True, relative_path, None
            else:
                return False, "", "音声セグメント生成に失敗"
                
        except Exception as e:
            error_msg = f"音声セグメント生成エラー: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg
    
    def _extract_segment_pydub(
        self, 
        source_path: Path, 
        output_path: Path, 
        start_time: float, 
        end_time: float
    ) -> bool:
        """
        pydubを使用した効率的なMP3セグメント抽出
        
        Args:
            source_path: 元ファイルパス
            output_path: 出力ファイルパス
            start_time: 開始時刻（秒）
            end_time: 終了時刻（秒）
            
        Returns:
            成功フラグ
        """
        try:
            # 前後のコンテキストを含む時刻計算
            segment_start = max(0, start_time - self.context_seconds)
            segment_end = end_time + self.context_seconds
            
            # ミリ秒に変換
            start_ms = int(segment_start * 1000)
            end_ms = int(segment_end * 1000)
            
            # MP3ファイル読み込み（指定区間のみ）
            audio = AudioSegment.from_mp3(str(source_path))
            
            # 終了時刻がファイル長を超える場合の調整
            if end_ms > len(audio):
                end_ms = len(audio)
            
            # セグメント切り出し
            segment = audio[start_ms:end_ms]
            
            # MP3形式で出力（元ファイルの品質を維持）
            segment.export(
                str(output_path),
                format="mp3",
                bitrate="128k",  # 適度な品質
                parameters=["-ac", "1"]  # モノラル変換
            )
            
            logger.debug(f"セグメント抽出完了: {segment_start:.1f}s-{segment_end:.1f}s")
            return True
            
        except Exception as e:
            logger.error(f"pydubセグメント抽出エラー: {e}")
            return False
    
    def _extract_segment_librosa(
        self, 
        source_path: Path, 
        output_path: Path, 
        start_time: float, 
        end_time: float
    ) -> Tuple[bool, Path]:
        """
        librosaを使用したシンプルなセグメント抽出（WAV形式）
        
        Args:
            source_path: 元ファイルパス
            output_path: 出力ファイルパス
            start_time: 開始時刻（秒）
            end_time: 終了時刻（秒）
            
        Returns:
            (成功フラグ, 実際の出力パス)
        """
        try:
            # 前後のコンテキストを含む時刻計算
            segment_start = max(0, start_time - self.context_seconds)
            segment_duration = (end_time + self.context_seconds) - segment_start
            
            # WAV形式で出力（シンプル統一）
            wav_output = output_path.with_suffix('.wav')
            
            # 既存ファイルがある場合は上書き、ロック時は一意名で保存
            if wav_output.exists():
                try:
                    wav_output.unlink()
                    logger.debug(f"既存WAVファイルを上書き: {wav_output}")
                except PermissionError:
                    import time
                    timestamp = int(time.time())
                    wav_output = wav_output.with_stem(f"{wav_output.stem}_{timestamp}")
                    logger.info(f"ファイルロックのため一意名で保存: {wav_output.name}")
            
            # 音声ファイル読み込み（librosaがMP3を自動変換）
            y, sr = librosa.load(
                str(source_path),
                sr=None,  # 元のサンプリングレートを維持
                offset=segment_start,
                duration=segment_duration,
                mono=True
            )
            
            # WAV形式で直接保存（シンプル！）
            sf.write(str(wav_output), y, sr)
            
            logger.debug(f"WAVセグメント生成完了: {segment_start:.1f}s-{segment_start + segment_duration:.1f}s")
            logger.info(f"[MUSIC] 高品質WAV形式で保存: {wav_output.name}")
            
            return True, wav_output
            
        except Exception as e:
            logger.error(f"WAVセグメント生成エラー: {e}")
            return False, output_path
    
    def _generate_filename(self, detection_id: int, species_name: str, confidence: float) -> str:
        """
        セグメントファイル名を生成
        
        Args:
            detection_id: 検出ID
            species_name: 種名
            confidence: 信頼度
            
        Returns:
            ファイル名
        """
        # 種名のサニタイズ（ファイル名に使用できない文字を除去）
        safe_species = "".join(c for c in species_name if c.isalnum() or c in "ー_-")
        
        return f"detection_{detection_id:03d}_{safe_species}_{confidence:.2f}.wav"
    
    def get_audio_duration(self, audio_path: str) -> Optional[float]:
        """
        音声ファイルの総再生時間を取得
        
        Args:
            audio_path: 音声ファイルパス
            
        Returns:
            再生時間（秒）またはNone
        """
        try:
            # librosaで長さを取得（MP3/WAV両方対応）
            duration = librosa.get_duration(path=audio_path)
            return duration
        except Exception as e:
            logger.error(f"音声長取得エラー: {e}")
            return None
    
    def validate_time_range(self, audio_path: str, start_time: float, end_time: float) -> bool:
        """
        指定時刻範囲が音声ファイル内に収まるかチェック
        
        Args:
            audio_path: 音声ファイルパス
            start_time: 開始時刻
            end_time: 終了時刻
            
        Returns:
            有効フラグ
        """
        duration = self.get_audio_duration(audio_path)
        if duration is None:
            return False
        
        # コンテキストを含む実際の抽出範囲
        actual_start = max(0, start_time - self.context_seconds)
        actual_end = end_time + self.context_seconds
        
        return actual_start < duration and actual_end > 0
