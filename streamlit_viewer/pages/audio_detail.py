#!/usr/bin/env python3
"""
音声詳細ページ
選択されたレコードの詳細情報を表示
"""

import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime

def format_seconds_to_time(seconds):
    """秒数を分秒形式に変換
    
    例:
    - 114.0 -> "1m54s"
    - 45.0 -> "45s"
    - 120.0 -> "2m00s"
    """
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
    """時間文字列を秒数に変換
    
    対応フォーマット:
    - '1m23s' -> 83.0
    - '45s' -> 45.0
    - '2m' -> 120.0
    - '123.45' -> 123.45
    - 123.45 -> 123.45
    """
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
sys.path.append(str(Path(__file__).parent.parent))
from config import DatabaseConfig, AppConfig, AudioConfig

# 親ディレクトリのlibをパスに追加
project_root = Path(__file__).parent.parent.parent
lib_path = project_root / "lib"
sys.path.append(str(lib_path))

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
        
        # 品質評価ステータス（もしあれば）
        if 'quality_status' in record:
            status = record['quality_status']
            if status == 'pending':
                st.warning("⏳ 評価待ち")
            elif status == 'approved':
                st.success("✅ 承認済み")
            elif status == 'rejected':
                st.error("❌ 却下")

def show_audio_player(audio_path, start_time, end_time):
    """音声プレイヤーを表示"""
    st.markdown("""
    <div class="card">
        <h3>🎵 音声再生</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if audio_path and audio_path.exists():
        st.success(f"✅ 音声ファイルが見つかりました: `{audio_path.name}`")
        
        # 全体音声の再生
        st.subheader("📻 完全なファイルを再生")
        with open(audio_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format=f'audio/{audio_path.suffix[1:]}')
        
        # 検出範囲の案内
        st.subheader("🎯 検出された時間範囲")
        
        # 時間文字列を秒数に変換
        try:
            start_float = parse_time_string(start_time)
            end_float = parse_time_string(end_time)
            st.info(f"鳥の鳴き声は {format_seconds_to_time(start_float)} ～ {format_seconds_to_time(end_float)} の間で検出されました")
        except Exception:
            st.info("鳥の鳴き声の検出時間情報が不明です")
        # 今後の機能案内
        st.markdown("""
        ### 🚧 今後実装予定の機能
        - 🎵 指定時間範囲での音声切り取り再生
        - 📊 スペクトログラム表示
        - 🎛️ 音声の品質評価
        """)
        
    else:
        st.error("❌ 音声ファイルが見つかりません")
        st.write("以下の場所を確認してください:")
        
        # 検索したパスを表示
        audio_base = AudioConfig.get_audio_base_path()
        filename = st.session_state.selected_record.get('filename', '')
        
        search_paths = []
        for subfolder in ['completed', 'failed', 'inbox']:
            for ext in AudioConfig.get_supported_formats():
                search_paths.append(f"`{audio_base / subfolder / (filename + ext)}`")
        
        for path in search_paths[:5]:  # 最初の5つのみ表示
            st.code(path)
        
        if len(search_paths) > 5:
            st.write(f"...他 {len(search_paths) - 5} 箇所")

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
    
    # 音声プレイヤー表示
    show_audio_player(
        audio_path, 
        record.get('start_time_seconds', 0), 
        record.get('end_time_seconds', 0)
    )
    
    # デバッグ情報（開発時のみ）
    with st.expander("🔧 デバッグ情報", expanded=False):
        st.json(record)
        if audio_path:
            st.write(f"音声ファイルパス: `{audio_path}`")

if __name__ == "__main__":
    main()
