#!/usr/bin/env python3
"""
音声詳細ページ（シンプル版）
スペクトログラム表示と音声再生機能に特化
"""

import streamlit as st
import sys
import os
from pathlib import Path
import sqlite3

# パス設定
sys.path.append(str(Path(__file__).parent.parent))
from config import DatabaseConfig, AppConfig

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

# シンプルなCSS
st.markdown("""
<style>
.compact-card {
    background: white;
    padding: 0.8rem;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    margin: 0.5rem 0;
    border-left: 3px solid #667eea;
}

.status-info {
    background: #f8f9fa;
    padding: 0.5rem;
    border-radius: 5px;
    font-size: 0.9rem;
    margin: 0.5rem 0;
}

.main-content {
    max-width: 1000px;
    margin: 0 auto;
}
</style>
""", unsafe_allow_html=True)

def get_processing_info(detection_id):
    """データベースから処理情報を取得"""
    try:
        db_path = DatabaseConfig.get_database_path()
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 音声セグメントとスペクトログラムのパス情報を取得
            cursor.execute("""
                SELECT 
                    audio_segment_path,
                    spectrogram_path
                FROM bird_detections 
                WHERE id = ?
            """, (detection_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'audio_segment_path': result[0],
                    'spectrogram_path': result[1]
                }
            return None
    except Exception as e:
        st.error(f"処理情報取得エラー: {e}")
        return None

def get_file_paths(detection_id, session_name):
    """生成ファイルの実際のパスを構築"""
    database_root = project_root / "database"
    
    # データベースから処理情報を取得
    processing_info = get_processing_info(detection_id)
    
    file_paths = {
        'audio_segment': None,
        'spectrogram': None,
        'audio_exists': False,
        'spectrogram_exists': False,
        'processing_info': processing_info
    }
    
    if processing_info and processing_info['audio_segment_path']:
        # データベースのパス情報を使用
        audio_path = database_root / processing_info['audio_segment_path']
        if audio_path.exists():
            file_paths['audio_segment'] = audio_path
            file_paths['audio_exists'] = True
    
    if processing_info and processing_info['spectrogram_path']:
        # データベースのパス情報を使用
        spectrogram_path = database_root / processing_info['spectrogram_path']
        if spectrogram_path.exists():
            file_paths['spectrogram'] = spectrogram_path
            file_paths['spectrogram_exists'] = True
    
    # パスが見つからない場合は推測で検索
    if not file_paths['audio_exists'] or not file_paths['spectrogram_exists']:
        audio_segments_dir = database_root / "audio_segments" / session_name
        spectrograms_dir = database_root / "spectrograms" / session_name
        
        # detection_ID形式のファイルを検索
        if audio_segments_dir.exists():
            for audio_file in audio_segments_dir.glob(f"detection_{detection_id:03d}_*.wav"):
                file_paths['audio_segment'] = audio_file
                file_paths['audio_exists'] = True
                break
        
        if spectrograms_dir.exists():
            for spectrogram_file in spectrograms_dir.glob(f"detection_{detection_id:03d}_*.png"):
                file_paths['spectrogram'] = spectrogram_file
                file_paths['spectrogram_exists'] = True
                break
    
    return file_paths

def show_main_content(record, file_paths):
    """メインコンテンツを表示"""
    
    # コンパクトなヘッダー
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 1rem;">
        <h2>🎵 {record.get('common_name', '不明')}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # メインエリア - スペクトログラムと音声プレイヤー
    if file_paths['spectrogram_exists']:
        # スペクトログラム表示
        st.image(str(file_paths['spectrogram']), use_column_width=True)
        
        # 音声プレイヤーと操作ボタンをスペクトログラムの下に配置
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if file_paths['audio_exists']:
                # 音声プレイヤー
                try:
                    with open(file_paths['audio_segment'], 'rb') as audio_file:
                        audio_bytes = audio_file.read()
                        st.audio(audio_bytes, format='audio/wav')
                    
                    # ダウンロードボタン
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.download_button(
                            label="🎵 音声DL",
                            data=audio_bytes,
                            file_name=file_paths['audio_segment'].name,
                            mime="audio/wav",
                            use_container_width=True
                        )
                    
                    with col_b:
                        with open(file_paths['spectrogram'], 'rb') as img_file:
                            img_bytes = img_file.read()
                        st.download_button(
                            label="📊 画像DL",
                            data=img_bytes,
                            file_name=file_paths['spectrogram'].name,
                            mime="image/png",
                            use_container_width=True
                        )
                        
                except Exception as e:
                    st.error(f"音声ファイル読み込みエラー: {e}")
            else:
                st.warning("🎵 音声セグメントが生成されていません")
                
    elif file_paths['audio_exists']:
        # 音声のみの場合
        st.markdown("""
        <div class="compact-card">
            <h4>🎵 音声セグメント</h4>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            with open(file_paths['audio_segment'], 'rb') as audio_file:
                audio_bytes = audio_file.read()
                st.audio(audio_bytes, format='audio/wav')
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                st.download_button(
                    label="📥 音声ダウンロード",
                    data=audio_bytes,
                    file_name=file_paths['audio_segment'].name,
                    mime="audio/wav",
                    use_container_width=True
                )
                
        except Exception as e:
            st.error(f"音声ファイル読み込みエラー: {e}")
    else:
        # ファイルが生成されていない場合
        st.markdown("""
        <div class="compact-card">
            <h4>🔧 ファイル未生成</h4>
            <p>音声セグメントやスペクトログラムのファイルが生成されていません。</p>
        </div>
        """, unsafe_allow_html=True)

def show_status_footer(record, file_paths):
    """下部に処理状況を小さく表示"""
    
    # 処理状況
    audio_status = "✅" if file_paths['audio_exists'] else "❌"
    spectrogram_status = "✅" if file_paths['spectrogram_exists'] else "❌"
    
    # 信頼度
    try:
        confidence = float(record.get('confidence', 0))
        confidence_text = f"{confidence:.1%}"
    except:
        confidence_text = "N/A"
    
    st.markdown(f"""
    <div class="status-info">
        <small>
            <strong>処理状況:</strong> 音声 {audio_status} | スペクトログラム {spectrogram_status} | 
            <strong>信頼度:</strong> {confidence_text} | 
            <strong>ファイル:</strong> {record.get('filename', 'N/A')[:30]}{'...' if len(record.get('filename', '')) > 30 else ''}
        </small>
    </div>
    """, unsafe_allow_html=True)

def main():
    # 選択されたレコードの確認
    if 'selected_record' not in st.session_state:
        st.error("❌ レコードが選択されていません")
        st.write("メインページに戻って、レコードを選択してください。")
        
        if st.button("🏠 メインページに戻る"):
            st.switch_page("db_viewer.py")
        return
    
    record = st.session_state.selected_record
    
    # 戻るボタンをコンパクトに
    if st.button("⬅️ 戻る", use_container_width=False):
        st.switch_page("db_viewer.py")
    
    # メインコンテンツ
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # ファイルパスを取得
    detection_id = record.get('id')
    session_name = record.get('session_name', 'default')
    file_paths = get_file_paths(detection_id, session_name)
    
    # メインコンテンツ表示
    show_main_content(record, file_paths)
    
    # ステータスフッター
    show_status_footer(record, file_paths)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # デバッグ情報（開発時のみ、コンパクト）
    with st.expander("🔧 デバッグ", expanded=False):
        st.json({
            'id': record.get('id'),
            'session': record.get('session_name'),
            'audio_exists': file_paths['audio_exists'],
            'spectrogram_exists': file_paths['spectrogram_exists'],
            'audio_path': str(file_paths['audio_segment']) if file_paths['audio_segment'] else None,
            'spectrogram_path': str(file_paths['spectrogram']) if file_paths['spectrogram'] else None
        })

if __name__ == "__main__":
    main()