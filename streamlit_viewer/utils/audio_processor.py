#!/usr/bin/env python3
"""
音声処理ユーティリティ
音声切り取り、波形生成、フォーマット変換などを担当
"""

import librosa
import soundfile as sf
import numpy as np
import io
import tempfile
from pathlib import Path
from typing import Tuple, Optional, Union
import streamlit as st


class AudioProcessor:
    """音声処理クラス"""
    
    def __init__(self, sample_rate: int = 22050):
        """
        初期化
        
        Args:
            sample_rate: サンプリングレート（デフォルト: 22050Hz）
        """
        self.sample_rate = sample_rate
    
    def load_audio(self, file_path: Union[str, Path]) -> Tuple[np.ndarray, int]:
        """
        音声ファイルを読み込み
        
        Args:
            file_path: 音声ファイルのパス
            
        Returns:
            Tuple[音声データ, サンプリングレート]
        """
        try:
            audio_data, sr = librosa.load(str(file_path), sr=self.sample_rate)
            return audio_data, sr
        except Exception as e:
            raise Exception(f"音声ファイルの読み込みに失敗: {e}")
    
    def extract_segment(
        self, 
        audio_data: np.ndarray, 
        start_time: float, 
        end_time: float, 
        sample_rate: int,
        context_seconds: float = 2.0
    ) -> Tuple[np.ndarray, float, float]:
        """
        指定時間範囲の音声セグメントを抽出
        
        Args:
            audio_data: 音声データ
            start_time: 開始時間（秒）
            end_time: 終了時間（秒）
            sample_rate: サンプリングレート
            context_seconds: 前後に含めるコンテキスト時間（秒）
            
        Returns:
            Tuple[抽出された音声データ, 実際の開始時間, 実際の終了時間]
        """
        # 音声の全長を計算
        total_duration = len(audio_data) / sample_rate
        
        # コンテキストを含めた開始・終了時間を計算
        context_start = max(0, start_time - context_seconds)
        context_end = min(total_duration, end_time + context_seconds)
        
        # サンプルインデックスに変換
        start_sample = int(context_start * sample_rate)
        end_sample = int(context_end * sample_rate)
        
        # セグメントを抽出
        segment = audio_data[start_sample:end_sample]
        
        return segment, context_start, context_end
    
    def save_segment_as_bytes(
        self, 
        audio_segment: np.ndarray, 
        sample_rate: int, 
        format: str = 'wav'
    ) -> bytes:
        """
        音声セグメントをバイトデータとして保存
        
        Args:
            audio_segment: 音声セグメントデータ
            sample_rate: サンプリングレート
            format: 出力フォーマット（'wav', 'mp3'など）
            
        Returns:
            音声データのバイト列
        """
        buffer = io.BytesIO()
        
        try:
            # 一時ファイルを使用してフォーマット変換
            with tempfile.NamedTemporaryFile(suffix=f'.{format}') as temp_file:
                sf.write(temp_file.name, audio_segment, sample_rate, format=format.upper())
                
                # ファイルを読み込んでバイトデータとして返す
                with open(temp_file.name, 'rb') as f:
                    return f.read()
                    
        except Exception as e:
            # WAVフォーマットでの直接保存にフォールバック
            sf.write(buffer, audio_segment, sample_rate, format='WAV')
            return buffer.getvalue()
    
    def generate_waveform_plot_data(
        self, 
        audio_data: np.ndarray, 
        sample_rate: int,
        detection_start: float = None,
        detection_end: float = None
    ) -> dict:
        """
        波形プロット用のデータを生成
        
        Args:
            audio_data: 音声データ
            sample_rate: サンプリングレート
            detection_start: 検出開始時間（秒）
            detection_end: 検出終了時間（秒）
            
        Returns:
            プロット用データの辞書
        """
        # 時間軸を生成
        duration = len(audio_data) / sample_rate
        time_axis = np.linspace(0, duration, len(audio_data))
        
        # ダウンサンプリング（表示用）
        downsample_factor = max(1, len(audio_data) // 2000)  # 最大2000ポイント
        time_downsampled = time_axis[::downsample_factor]
        audio_downsampled = audio_data[::downsample_factor]
        
        plot_data = {
            'time': time_downsampled,
            'amplitude': audio_downsampled,
            'duration': duration,
            'sample_rate': sample_rate
        }
        
        # 検出範囲の情報を追加
        if detection_start is not None and detection_end is not None:
            plot_data['detection_start'] = detection_start
            plot_data['detection_end'] = detection_end
        
        return plot_data
    
    def calculate_audio_statistics(self, audio_data: np.ndarray) -> dict:
        """
        音声データの統計情報を計算
        
        Args:
            audio_data: 音声データ
            
        Returns:
            統計情報の辞書
        """
        return {
            'duration': len(audio_data) / self.sample_rate,
            'max_amplitude': float(np.max(np.abs(audio_data))),
            'rms_amplitude': float(np.sqrt(np.mean(audio_data**2))),
            'zero_crossing_rate': float(librosa.feature.zero_crossing_rate(audio_data)[0].mean()),
            'spectral_centroid': float(librosa.feature.spectral_centroid(y=audio_data, sr=self.sample_rate)[0].mean())
        }


class AudioPlayerComponent:
    """Streamlit用音声プレイヤーコンポーネント"""
    
    @staticmethod
    def render_segment_player(
        audio_bytes: bytes, 
        title: str = "音声セグメント",
        format: str = "wav",
        detection_info: dict = None
    ):
        """
        音声セグメントプレイヤーをレンダリング
        
        Args:
            audio_bytes: 音声データのバイト列
            title: プレイヤーのタイトル
            format: 音声フォーマット
            detection_info: 検出情報（開始時間、終了時間など）
        """
        st.subheader(title)
        
        # 検出情報がある場合は表示
        if detection_info:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("開始時間", f"{detection_info.get('start', 0):.1f}s")
            with col2:
                st.metric("終了時間", f"{detection_info.get('end', 0):.1f}s")
            with col3:
                st.metric("継続時間", f"{detection_info.get('duration', 0):.1f}s")
        
        # 音声プレイヤー
        st.audio(audio_bytes, format=f'audio/{format}')
    
    @staticmethod
    def render_waveform(plot_data: dict):
        """
        波形をレンダリング
        
        Args:
            plot_data: generate_waveform_plot_data()からの出力
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            
            fig = go.Figure()
            
            # 波形を追加
            fig.add_trace(go.Scatter(
                x=plot_data['time'],
                y=plot_data['amplitude'],
                mode='lines',
                name='音声波形',
                line=dict(color='blue', width=1)
            ))
            
            # 検出範囲がある場合はハイライト
            if 'detection_start' in plot_data and 'detection_end' in plot_data:
                fig.add_vrect(
                    x0=plot_data['detection_start'],
                    x1=plot_data['detection_end'],
                    fillcolor="red",
                    opacity=0.2,
                    line_width=0,
                    annotation_text="検出範囲",
                    annotation_position="top left"
                )
            
            # レイアウト設定
            fig.update_layout(
                title="音声波形",
                xaxis_title="時間 (秒)",
                yaxis_title="振幅",
                height=300,
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except ImportError:
            st.warning("波形表示にはplotlyが必要です")
        except Exception as e:
            st.error(f"波形表示エラー: {e}")


# ユーティリティ関数
def format_time_display(seconds: float) -> str:
    """秒数を見やすい時間表示に変換"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}分{remaining_seconds:.1f}秒"


def validate_time_range(start: float, end: float, max_duration: float) -> Tuple[bool, str]:
    """時間範囲の妥当性を検証"""
    if start < 0:
        return False, "開始時間は0以上である必要があります"
    
    if end > max_duration:
        return False, f"終了時間は{max_duration:.1f}秒以下である必要があります"
    
    if start >= end:
        return False, "開始時間は終了時間より小さい必要があります"
    
    return True, "OK"


# エラーハンドリング用のデコレータ
def handle_audio_errors(func):
    """音声処理エラーをハンドリングするデコレータ"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"音声処理エラー: {e}")
            return None
    return wrapper
