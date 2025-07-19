#!/usr/bin/env python3
"""
音声詳細ページ（拡張版）
選択されたレコードの詳細情報を表示 + 音声切り取り再生機能
"""

import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime
import numpy as np

def format_seconds_to_time(seconds):
    """秒数を分秒形式に変換"""
    if seconds == 0:
        return "0s"
    
    total_seconds = int(round(seconds))
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    
    if minutes > 0:
        return f"{minutes}m{remaining_seconds:02d}s"
    else:
        return f"{remaining_seconds}s"

def parse_time_string(time_str):
    """時間文字列を秒数に変換"""
    if time_str is None:
        return 0.0
    
    # 既に数値の場合
    if isinstance(time_str, (int, float)):
        return float(time_str)
    
    # 文字列の場合
    if isinstance(time_str, str):
        time_str = time_str.strip()
        
        # 空文字列の場合
        if not time_str:
            return 0.0
        
        # 数値のみの文字列の場合
        try:
            return float(time_str)
        except ValueError:
            pass
        
        # 'm' と 's' を含むフォーマットの場合
        total_seconds = 0.0
        
        # 分を検索
        if 'm' in time_str:
            parts = time_str.split('m')
            try:
                minutes = float(parts[0])
                total_seconds += minutes * 60
                # 'm' 以降の部分を取得
                remaining = parts[1] if len(parts) > 1 else ''
            except (ValueError, IndexError):
                remaining = time_str
        else:
            remaining = time_str
        
        # 秒を検索
        if 's' in remaining:
            remaining = remaining.replace('s', '')
        
        if remaining.strip():
            try:
                seconds = float(remaining)
                total_seconds += seconds
            except ValueError:
                pass
        
        return total_seconds
    
    return 0.0

# パス設定
sys.path.append(str(Path(__file__).parent.parent))
from config import DatabaseConfig, AppConfig, AudioConfig

# 親ディレクトリのlibをパスに追加
project_root = Path(__file__).parent.parent.parent
lib_path = project_root / "lib"
sys.path.append(str(lib_path))

# 新しい音声処理ユーティリティをインポート
try:
    from utils.audio_processor import AudioProcessor, AudioPlayerComponent, format_time_display, validate_time_range, handle_audio_errors
except ImportError as e:
    st.error(f"音声処理ユーティリティの読み込みに失敗: {e}")
    st.stop()

try:
    from db.database import BirdNetSimpleDB
except ImportError as e:
    st.error(f"データベースモジュールの読み込みに失敗: {e}")
    st.stop()

# ページ設定
st.set_page_config(
    page_title="音声詳細 - BirdNet",
    page_icon="🎵",
    layout="wide"
)

# カスタムCSS
st.markdown(AppConfig.get_custom_css(), unsafe_allow_html=True)

@st.cache_data
def load_and_process_audio(audio_path_str: str, sample_rate: int = 22050):
    """音声ファイルを読み込んで基本処理を実行（キャッシュ付き）"""
    try:
        processor = AudioProcessor(sample_rate=sample_rate)
        audio_data, sr = processor.load_audio(audio_path_str)
        
        # 基本統計情報を計算
        stats = processor.calculate_audio_statistics(audio_data)
        
        return audio_data, sr, stats, None
    except Exception as e:
        return None, None, None, str(e)

def get_audio_file_path(record):
    """音声ファイルのパスを解決"""
    audio_base = AudioConfig.get_audio_base_path()
    
    # 複数の可能性を試す
    possible_paths = []
    
    # 1. file_pathがある場合
    if record.get('file_path'):
        possible_paths.append(Path(record['file_path']))
    
    # 2. completed, failed, inboxフォルダを検索
    filename = record.get('filename', '')
    for subfolder in ['completed', 'failed', 'inbox']:
        for ext in AudioConfig.get_supported_formats():
            possible_paths.append(audio_base / subfolder / f"{filename}{ext}")
    
    # 3. 直接audio フォルダ内を検索
    for ext in AudioConfig.get_supported_formats():
        possible_paths.append(audio_base / f"{filename}{ext}")
    
    # 存在するファイルを探す
    for path in possible_paths:
        if path.exists():
            return path
    
    return None

def show_record_details(record):
    """レコード詳細情報を表示"""
    
    # ヘッダー
    st.markdown(f"""
    <div class="header">
        <h1>🎵 音声詳細</h1>
        <p>{record.get('common_name', '不明')} - {record.get('filename', '')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 基本情報
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("""
        <div class="card">
            <h3>🐦 検出情報</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.write(f"**和名:** {record.get('common_name', 'N/A')}")
        st.write(f"**学名:** {record.get('scientific_name', 'N/A')}")
        
        # 信頼度の安全な表示
        confidence_raw = record.get('confidence', 0)
        try:
            confidence = float(confidence_raw) if confidence_raw is not None else 0
            st.write(f"**信頼度:** {confidence:.3f}")
        except (ValueError, TypeError):
            confidence = 0
            st.write(f"**信頼度:** N/A")
        
        # 信頼度バー
        try:
            confidence_for_bar = float(record.get('confidence', 0)) if record.get('confidence') is not None else 0
            st.progress(confidence_for_bar, text=f"信頼度: {confidence_for_bar:.1%}")
        except (ValueError, TypeError):
            st.progress(0, text="信頼度: N/A")
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>⏱️ 時間情報</h3>
        </div>
        """, unsafe_allow_html=True)
        
        start_time = record.get('start_time_seconds', 0)
        end_time = record.get('end_time_seconds', 0)
        
        # 時間文字列を秒数に変換
        try:
            start_time = parse_time_string(start_time)
            end_time = parse_time_string(end_time)
            duration = end_time - start_time
        except Exception:
            start_time = 0
            end_time = 0
            duration = 0
        
        st.write(f"**開始時間:** {format_seconds_to_time(start_time)}")
        st.write(f"**終了時間:** {format_seconds_to_time(end_time)}")
        st.write(f"**継続時間:** {format_seconds_to_time(duration)}")
        
        # 時間範囲表示
        st.info(f"📍 {format_seconds_to_time(start_time)} - {format_seconds_to_time(end_time)} ({format_seconds_to_time(duration)}間)")
    
    with col3:
        st.markdown("""
        <div class="card">
            <h3>📁 ファイル情報</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.write(f"**ファイル名:** {record.get('filename', 'N/A')}")
        st.write(f"**セッション:** {record.get('session_name', 'N/A')}")
        st.write(f"**モデル:** {record.get('model_name', 'N/A')}")

def show_enhanced_audio_player(audio_path, record):
    """拡張された音声プレイヤーを表示"""
    st.markdown("""
    <div class="card">
        <h3>🎵 音声再生（拡張版）</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if not audio_path or not audio_path.exists():
        st.error("❌ 音声ファイルが見つかりません")
        return
    
    # 音声データを読み込み
    with st.spinner("音声データを読み込み中..."):
        audio_data, sample_rate, stats, error = load_and_process_audio(str(audio_path))
    
    if error:
        st.error(f"音声読み込みエラー: {error}")
        return
    
    if audio_data is None:
        st.error("音声データの読み込みに失敗しました")
        return
    
    # 基本情報表示
    st.success(f"✅ 音声ファイル読み込み完了: `{audio_path.name}`")
    
    # 音声統計情報
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("総時間", format_time_display(stats['duration']))
    with col2:
        st.metric("最大振幅", f"{stats['max_amplitude']:.3f}")
    with col3:
        st.metric("RMS振幅", f"{stats['rms_amplitude']:.3f}")
    with col4:
        st.metric("サンプルレート", f"{sample_rate} Hz")
    
    # 検出時間情報を取得
    start_time = parse_time_string(record.get('start_time_seconds', 0))
    end_time = parse_time_string(record.get('end_time_seconds', 0))
    
    # タブで機能を分ける
    tab1, tab2, tab3 = st.tabs(["🎵 音声切り取り再生", "📊 波形表示", "🎧 完全ファイル再生"])
    
    with tab1:
        show_segment_player(audio_data, sample_rate, start_time, end_time, stats['duration'])
    
    with tab2:
        show_waveform_display(audio_data, sample_rate, start_time, end_time)
    
    with tab3:
        show_full_audio_player(audio_path)

@handle_audio_errors
def show_segment_player(audio_data, sample_rate, detection_start, detection_end, total_duration):
    """音声セグメント切り取り再生機能"""
    st.subheader("🎯 指定範囲での音声再生")
    
    # コンテキスト設定
    col1, col2 = st.columns(2)
    with col1:
        context_seconds = st.slider(
            "前後のコンテキスト（秒）",
            min_value=0.0,
            max_value=10.0,
            value=2.0,
            step=0.5,
            help="検出範囲の前後に含める時間"
        )
    
    with col2:
        # カスタム時間範囲設定
        custom_range = st.checkbox("カスタム時間範囲を設定", help="検出範囲とは異なる時間範囲を指定")
    
    if custom_range:
        # カスタム範囲入力
        st.write("**カスタム時間範囲**")
        col_start, col_end = st.columns(2)
        
        with col_start:
            custom_start = st.number_input(
                "開始時間（秒）",
                min_value=0.0,
                max_value=total_duration,
                value=max(0, detection_start - context_seconds),
                step=0.1
            )
        
        with col_end:
            custom_end = st.number_input(
                "終了時間（秒）",
                min_value=0.0,
                max_value=total_duration,
                value=min(total_duration, detection_end + context_seconds),
                step=0.1
            )
        
        # 妥当性チェック
        is_valid, message = validate_time_range(custom_start, custom_end, total_duration)
        if not is_valid:
            st.error(message)
            return
        
        segment_start, segment_end = custom_start, custom_end
    else:
        # デフォルト: 検出範囲 + コンテキスト
        segment_start = max(0, detection_start - context_seconds)
        segment_end = min(total_duration, detection_end + context_seconds)
    
    # 切り取り範囲の表示
    st.info(f"再生範囲: {segment_start:.1f}s ～ {segment_end:.1f}s ({segment_end - segment_start:.1f}秒間)")
    
    # 音声セグメント抽出ボタン
    if st.button("🎵 音声セグメントを生成", type="primary"):
        try:
            processor = AudioProcessor(sample_rate=sample_rate)
            
            # セグメント抽出
            with st.spinner("音声セグメントを抽出中..."):
                segment, actual_start, actual_end = processor.extract_segment(
                    audio_data, 
                    segment_start, 
                    segment_end, 
                    sample_rate, 
                    context_seconds=0  # 既にコンテキストは考慮済み
                )
            
            # セグメントをバイト列に変換
            with st.spinner("音声ファイルを生成中..."):
                segment_bytes = processor.save_segment_as_bytes(segment, sample_rate, 'wav')
            
            # プレイヤーコンポーネントでレンダリング
            detection_info = {
                'start': actual_start,
                'end': actual_end,
                'duration': actual_end - actual_start,
                'detection_start': detection_start,
                'detection_end': detection_end
            }
            
            AudioPlayerComponent.render_segment_player(
                segment_bytes,
                title="🎵 切り取り音声セグメント",
                format="wav",
                detection_info=detection_info
            )
            
            # 検出範囲のハイライト表示
            if not custom_range:
                st.success(f"🎯 検出範囲: {detection_start:.1f}s ～ {detection_end:.1f}s がハイライトされた範囲です")
            
        except Exception as e:
            st.error(f"音声セグメント生成エラー: {e}")

@handle_audio_errors
def show_waveform_display(audio_data, sample_rate, detection_start, detection_end):
    """波形表示機能"""
    st.subheader("📊 音声波形")
    
    try:
        processor = AudioProcessor(sample_rate=sample_rate)
        
        # 波形データ生成
        plot_data = processor.generate_waveform_plot_data(
            audio_data, 
            sample_rate,
            detection_start,
            detection_end
        )
        
        # 波形をレンダリング
        AudioPlayerComponent.render_waveform(plot_data)
        
        # 波形統計
        with st.expander("📈 波形統計情報"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**総サンプル数:** {len(audio_data):,}")
                st.write(f"**サンプリングレート:** {sample_rate} Hz")
                st.write(f"**ビット深度:** 32-bit float")
            
            with col2:
                st.write(f"**ダイナミックレンジ:** {np.max(audio_data) - np.min(audio_data):.3f}")
                st.write(f"**平均値:** {np.mean(audio_data):.6f}")
                st.write(f"**標準偏差:** {np.std(audio_data):.6f}")
        
    except Exception as e:
        st.error(f"波形表示エラー: {e}")

def show_full_audio_player(audio_path):
    """完全ファイル再生"""
    st.subheader("📻 完全なファイルを再生")
    
    try:
        with open(audio_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format=f'audio/{audio_path.suffix[1:]}')
        
        st.info("💡 上記は元の音声ファイル全体です。「音声切り取り再生」タブで特定範囲のみを再生できます。")
        
    except Exception as e:
        st.error(f"音声ファイル読み込みエラー: {e}")

def main():
    # 選択されたレコードの確認
    if 'selected_record' not in st.session_state:
        st.error("❌ レコードが選択されていません")
        st.write("メインページに戻って、レコードを選択してください。")
        
        if st.button("🏠 メインページに戻る"):
            st.switch_page("db_viewer.py")
        return
    
    record = st.session_state.selected_record
    
    # 戻るボタン
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ メインページに戻る", use_container_width=True):
            st.switch_page("db_viewer.py")
    
    # レコード詳細表示
    show_record_details(record)
    
    # 音声ファイルパスを解決
    audio_path = get_audio_file_path(record)
    
    # 拡張音声プレイヤー表示
    show_enhanced_audio_player(audio_path, record)
    
    # デバッグ情報（開発時のみ）
    with st.expander("🔧 デバッグ情報", expanded=False):
        st.json(record)
        if audio_path:
            st.write(f"音声ファイルパス: `{audio_path}`")

if __name__ == "__main__":
    main()
