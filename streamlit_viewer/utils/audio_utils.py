"""
音声処理ユーティリティモジュール
音声ファイルの読み込み、正規化、セグメント抽出など
"""

import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import warnings

# 音声処理ライブラリ（オプション）
try:
    import librosa
    import soundfile as sf
    AUDIO_SUPPORT = True
except ImportError:
    AUDIO_SUPPORT = False
    warnings.warn("音声処理ライブラリ（librosa, soundfile）がインストールされていません。音声機能は無効です。")


def check_audio_support() -> bool:
    """音声処理がサポートされているかチェック"""
    return AUDIO_SUPPORT


def load_audio_file(file_path: str, sr: Optional[int] = None) -> Tuple[np.ndarray, int]:
    """音声ファイルを読み込み"""
    if not AUDIO_SUPPORT:
        raise ImportError("音声処理ライブラリが利用できません")
    
    try:
        audio, sample_rate = librosa.load(file_path, sr=sr)
        return audio, sample_rate
    except Exception as e:
        raise ValueError(f"音声ファイル読み込みエラー: {e}")


def load_audio_segment(
    file_path: str, 
    start_time: float, 
    end_time: float, 
    sr: Optional[int] = None,
    normalize: bool = True,
    fade_duration: float = 0.1
) -> Tuple[np.ndarray, int]:
    """音声ファイルから指定された時間範囲のセグメントを読み込み"""
    if not AUDIO_SUPPORT:
        raise ImportError("音声処理ライブラリが利用できません")
    
    try:
        # 音声全体を読み込み
        audio, sample_rate = librosa.load(file_path, sr=sr)
        
        # 時間をサンプル数に変換
        start_sample = int(start_time * sample_rate)
        end_sample = int(end_time * sample_rate)
        
        # セグメント抽出
        segment = audio[start_sample:end_sample]
        
        # 正規化
        if normalize and len(segment) > 0:
            segment = normalize_audio(segment)
        
        # フェード処理
        if fade_duration > 0 and len(segment) > 0:
            segment = apply_fade(segment, sample_rate, fade_duration)
        
        return segment, sample_rate
    
    except Exception as e:
        raise ValueError(f"音声セグメント読み込みエラー: {e}")


def normalize_audio(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    """音声を指定dBに正規化"""
    if len(audio) == 0:
        return audio
    
    # RMS計算
    rms = np.sqrt(np.mean(audio**2))
    if rms == 0:
        return audio
    
    # 目標レベル計算
    target_linear = 10**(target_db / 20.0)
    gain = target_linear / rms
    
    # ゲイン適用（クリッピング防止）
    normalized = audio * min(gain, 1.0)
    
    return normalized


def apply_fade(audio: np.ndarray, sample_rate: int, fade_duration: float) -> np.ndarray:
    """フェードイン・フェードアウト適用"""
    if len(audio) == 0:
        return audio
    
    fade_samples = int(fade_duration * sample_rate)
    fade_samples = min(fade_samples, len(audio) // 4)  # 最大で音声の1/4まで
    
    if fade_samples <= 0:
        return audio
    
    result = audio.copy()
    
    # フェードイン
    fade_in = np.linspace(0, 1, fade_samples)
    result[:fade_samples] *= fade_in
    
    # フェードアウト
    fade_out = np.linspace(1, 0, fade_samples)
    result[-fade_samples:] *= fade_out
    
    return result


def get_audio_info(file_path: str) -> dict:
    """音声ファイルの基本情報を取得"""
    if not AUDIO_SUPPORT:
        return {"error": "音声処理ライブラリが利用できません"}
    
    try:
        # ファイル情報を取得（高速）
        info = sf.info(file_path)
        
        return {
            "duration": info.duration,
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "format": info.format,
            "subtype": info.subtype,
            "frames": info.frames
        }
    except Exception as e:
        return {"error": str(e)}


def create_spectrogram(audio: np.ndarray, sample_rate: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """スペクトログラムを作成"""
    if not AUDIO_SUPPORT:
        raise ImportError("音声処理ライブラリが利用できません")
    
    try:
        # STFT計算
        stft = librosa.stft(audio)
        magnitude = np.abs(stft)
        
        # デシベル変換
        db = librosa.amplitude_to_db(magnitude, ref=np.max)
        
        # 時間軸と周波数軸
        times = librosa.frames_to_time(np.arange(db.shape[1]), sr=sample_rate)
        freqs = librosa.fft_frequencies(sr=sample_rate)
        
        return db, times, freqs
    
    except Exception as e:
        raise ValueError(f"スペクトログラム作成エラー: {e}")


def save_audio_segment(audio: np.ndarray, sample_rate: int, output_path: str) -> None:
    """音声セグメントをファイルに保存"""
    if not AUDIO_SUPPORT:
        raise ImportError("音声処理ライブラリが利用できません")
    
    try:
        sf.write(output_path, audio, sample_rate)
    except Exception as e:
        raise ValueError(f"音声保存エラー: {e}")


def get_supported_formats() -> list:
    """サポートされている音声フォーマット一覧"""
    if not AUDIO_SUPPORT:
        return []
    
    return ['.wav', '.mp3', '.flac', '.aac', '.ogg', '.m4a']


def is_audio_file(file_path: str) -> bool:
    """ファイルが音声ファイルかどうかチェック"""
    if not AUDIO_SUPPORT:
        return False
    
    supported_formats = get_supported_formats()
    file_ext = Path(file_path).suffix.lower()
    return file_ext in supported_formats
