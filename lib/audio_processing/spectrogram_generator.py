"""
スペクトログラム生成クラス
音声セグメントからメル・スペクトログラムPNG画像を生成
"""

import os
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import logging

# 非インタラクティブバックエンド設定（サーバー環境対応）
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# librosa関連のインポート
try:
    import librosa
    import librosa.display
    LIBROSA_AVAILABLE = True
except ImportError as e:
    LIBROSA_AVAILABLE = False
    logging.error(f"librosa import error: {e}")

# ロガー設定
logger = logging.getLogger(__name__)

class SpectrogramGenerator:
    """スペクトログラム生成クラス"""
    
    def __init__(self, base_output_dir: str = None):
        """
        初期化
        
        Args:
            base_output_dir: 出力ベースディレクトリ（デフォルト: database/spectrograms）
        """
        if not LIBROSA_AVAILABLE:
            logger.error("librosaが利用できません。pip install librosaを実行してください。")
            raise ImportError("librosa not available")
            
        if base_output_dir is None:
            # プロジェクトルートからの相対パス
            project_root = Path(__file__).parent.parent.parent
            base_output_dir = project_root / "database" / "spectrograms"
        
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        
        # スペクトログラム設定
        self.figure_size = (10, 6)  # 800x600ピクセル相当
        self.dpi = 80
        self.n_mels = 128  # メル周波数ビン数
        self.fmax = 8000   # 最大周波数（鳥類検出に適した範囲）
        
    def generate_spectrogram(
        self,
        audio_segment_path: str,
        session_name: str,
        detection_id: int,
        species_name: str,
        confidence: float
    ) -> Tuple[bool, str, Optional[str]]:
        """
        スペクトログラム画像を生成
        
        Args:
            audio_segment_path: 音声セグメントファイルパス
            session_name: セッション名
            detection_id: 検出ID
            species_name: 種名
            confidence: 信頼度
            
        Returns:
            (成功フラグ, 出力ファイルパス, エラーメッセージ)
        """
        try:
            segment_path = Path(audio_segment_path)
            
            # 音声セグメントファイル存在確認
            if not segment_path.exists():
                return False, "", f"音声セグメントファイルが見つかりません: {segment_path}"
            
            # 出力ディレクトリ作成
            session_dir = self.base_output_dir / session_name
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # 出力ファイル名生成
            output_filename = self._generate_filename(detection_id, species_name, confidence)
            output_path = session_dir / output_filename
            
            # スペクトログラム生成
            success = self._create_melspectrogram(segment_path, output_path, species_name)
            
            if success:
                # 相対パス返却（database/からの相対パス）
                relative_path = f"spectrograms/{session_name}/{output_filename}"
                logger.info(f"スペクトログラム生成完了: {relative_path}")
                return True, relative_path, None
            else:
                return False, "", "スペクトログラム生成に失敗"
                
        except Exception as e:
            error_msg = f"スペクトログラム生成エラー: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg
    
    def _create_melspectrogram(
        self, 
        audio_path: Path, 
        output_path: Path, 
        species_name: str
    ) -> bool:
        """
        メル・スペクトログラム生成
        
        Args:
            audio_path: 音声ファイルパス
            output_path: 出力画像ファイルパス
            species_name: 種名（タイトル用）
            
        Returns:
            成功フラグ
        """
        try:
            # 音声ファイル読み込み
            y, sr = librosa.load(str(audio_path), sr=None, mono=True)
            
            # メル・スペクトログラム計算
            mel_spec = librosa.feature.melspectrogram(
                y=y,
                sr=sr,
                n_mels=self.n_mels,
                fmax=self.fmax,
                hop_length=512,
                n_fft=2048
            )
            
            # デシベルスケールに変換
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
            
            # プロット作成
            plt.figure(figsize=self.figure_size, dpi=self.dpi)
            
            # スペクトログラム表示（librosa.displayの代替方法も含む）
            try:
                # 通常のlibrosa.display.specshow
                librosa.display.specshow(
                    mel_spec_db,
                    sr=sr,
                    x_axis='time',
                    y_axis='mel',
                    fmax=self.fmax,
                    cmap='viridis'  # 元の色合いに戻す
                )
            except AttributeError:
                # librosa.displayが利用できない場合の代替処理
                logger.warning("librosa.display不可。代替処理を使用します。")
                
                # 時間軸とメル周波数軸を手動で計算
                hop_length = 512
                time_frames = librosa.frames_to_time(
                    np.arange(mel_spec_db.shape[1]), 
                    sr=sr, 
                    hop_length=hop_length
                )
                mel_frequencies = librosa.mel_frequencies(
                    n_mels=self.n_mels, 
                    fmax=self.fmax
                )
                
                # imshowを使用してスペクトログラムを表示（元の色合い）
                plt.imshow(
                    mel_spec_db,
                    aspect='auto',
                    origin='lower',
                    cmap='viridis',  # 元の色合いに戻す
                    extent=[time_frames[0], time_frames[-1], 
                           mel_frequencies[0], mel_frequencies[-1]]
                )
                
                plt.xlabel('Time (s)', fontsize=10)
                plt.ylabel('Mel Frequency (Hz)', fontsize=10)
            
            # カラーバーを削除（コメントアウト）
            # plt.colorbar(format='%+2.0f dB')
            
            # タイトルと軸ラベル
            plt.title(f'{species_name} - Mel Spectrogram', fontsize=12, pad=10)
            
            # librosa.displayが使えた場合の軸ラベル
            if hasattr(librosa, 'display'):
                plt.xlabel('Time (s)', fontsize=10)
                plt.ylabel('Mel Frequency', fontsize=10)
            
            # レイアウト調整
            plt.tight_layout()
            
            # PNG形式で保存
            plt.savefig(
                str(output_path),
                format='png',
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none',
                dpi=self.dpi
            )
            
            # メモリ解放
            plt.close()
            
            logger.debug(f"メル・スペクトログラム生成完了: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"メル・スペクトログラム生成エラー: {str(e)}")
            logger.error(f"エラー詳細 - ファイル: {audio_path}, 出力: {output_path}")
            # エラー時もプロットを確実に閉じる
            plt.close('all')
            return False
    
    def _generate_filename(self, detection_id: int, species_name: str, confidence: float) -> str:
        """
        スペクトログラムファイル名を生成
        
        Args:
            detection_id: 検出ID
            species_name: 種名
            confidence: 信頼度
            
        Returns:
            ファイル名
        """
        # 種名のサニタイズ（ファイル名に使用できない文字を除去）
        safe_species = "".join(c for c in species_name if c.isalnum() or c in "ー_-")
        
        return f"detection_{detection_id:03d}_{safe_species}_{confidence:.2f}.png"
    
    def create_overview_spectrogram(
        self,
        audio_path: str,
        output_path: str,
        title: str = "Audio Overview"
    ) -> bool:
        """
        音声ファイル全体のオーバービュー・スペクトログラムを生成
        
        Args:
            audio_path: 音声ファイルパス
            output_path: 出力画像ファイルパス
            title: グラフタイトル
            
        Returns:
            成功フラグ
        """
        try:
            # 音声ファイル読み込み（ダウンサンプリングで高速化）
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            
            # 短時間フーリエ変換
            stft = librosa.stft(y, hop_length=1024, n_fft=2048)
            stft_db = librosa.amplitude_to_db(np.abs(stft), ref=np.max)
            
            # プロット作成（横長のオーバービュー）
            plt.figure(figsize=(16, 6), dpi=80)
            
            try:
                librosa.display.specshow(
                    stft_db,
                    sr=sr,
                    x_axis='time',
                    y_axis='hz',
                    cmap='viridis'  # 元の色合いに戻す
                )
            except AttributeError:
                # 代替処理
                hop_length = 1024
                time_frames = librosa.frames_to_time(
                    np.arange(stft_db.shape[1]), 
                    sr=sr, 
                    hop_length=hop_length
                )
                freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
                
                plt.imshow(
                    stft_db,
                    aspect='auto',
                    origin='lower',
                    cmap='viridis',  # 元の色合いに戻す
                    extent=[time_frames[0], time_frames[-1], 
                           freqs[0], freqs[-1]]
                )
                plt.xlabel('Time (s)', fontsize=12)
                plt.ylabel('Frequency (Hz)', fontsize=12)
            
            # カラーバーを削除（コメントアウト）
            # plt.colorbar(format='%+2.0f dB')
            plt.title(title, fontsize=14, pad=15)
            
            if hasattr(librosa, 'display'):
                plt.xlabel('Time (s)', fontsize=12)
                plt.ylabel('Frequency (Hz)', fontsize=12)
            
            plt.tight_layout()
            
            # 保存
            plt.savefig(
                output_path,
                format='png',
                bbox_inches='tight',
                facecolor='white',
                dpi=80
            )
            
            plt.close()
            
            logger.info(f"オーバービュー・スペクトログラム生成完了: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"オーバービュー・スペクトログラム生成エラー: {e}")
            plt.close('all')
            return False
