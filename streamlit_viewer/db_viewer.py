#!/usr/bin/env python3
"""
BirdNet データベースビューワー（統合表示版）
検索・フィルタ機能 + 選択行の音声・スペクトログラム即座表示
（ファイル生成機能削除版）
"""

import streamlit as st
import pandas as pd
import sys
import os
import sqlite3
from pathlib import Path
from datetime import datetime
import time

# 設定とユーティリティをインポート
from config import DatabaseConfig, AppConfig

# 親ディレクトリのlibをパスに追加
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
lib_path = project_root / "lib"
sys.path.append(str(lib_path))

try:
    from db.database import BirdNetSimpleDB
    from audio_processing import ProcessingManager
except ImportError as e:
    st.error(f"必要なモジュールの読み込みに失敗: {e}")
    st.stop()

# ページ設定
st.set_page_config(
    page_title=AppConfig.PAGE_TITLE,
    page_icon=AppConfig.PAGE_ICON,
    layout=AppConfig.LAYOUT,
    initial_sidebar_state="expanded"
)

# カスタムCSS適用
st.markdown(AppConfig.get_custom_css(), unsafe_allow_html=True)

# 追加CSS（プレビューエリア用）
st.markdown("""
<style>
.preview-card {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 10px;
    border-left: 4px solid #667eea;
    margin: 1rem 0;
}

.compact-info {
    background: white;
    padding: 0.5rem;
    border-radius: 5px;
    margin: 0.5rem 0;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_database():
    """データベースを読み込み（キャッシュ付き）"""
    try:
        db_path = DatabaseConfig.get_database_path()
        
        if not os.path.exists(db_path):
            st.error(f"データベースファイルが見つかりません: {db_path}")
            alternative_paths = DatabaseConfig.get_alternative_paths()
            
            for alt_path in alternative_paths:
                if alt_path.exists():
                    db_path = str(alt_path)
                    break
            else:
                st.error("データベースファイルがどこにも見つかりません")
                return None
        
        db = BirdNetSimpleDB(db_path)
        return db
        
    except Exception as e:
        st.error(f"データベース接続エラー: {e}")
        return None

@st.cache_data
def get_unique_sessions(db_path):
    """ユニークなセッション名を取得"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT session_name FROM bird_detections ORDER BY session_name")
            sessions = [row[0] for row in cursor.fetchall()]
            return sessions
    except Exception as e:
        st.error(f"セッション取得エラー: {e}")
        return []

@st.cache_data
def get_unique_species(db_path):
    """ユニークな種名を取得"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT common_name FROM bird_detections WHERE common_name IS NOT NULL ORDER BY common_name")
            species = [row[0] for row in cursor.fetchall()]
            return species
    except Exception as e:
        st.error(f"種名取得エラー: {e}")
        return []

def get_filtered_data(db_path, session_filter=None, species_filter=None, confidence_min=0.0, quality_filter=None):
    """検索条件に基づいてデータを取得"""
    try:
        required_columns = [
            'id', 'session_name', 'model_name', 'common_name', 'scientific_name',
            'confidence', 'start_time_seconds', 'end_time_seconds', 'filename', 'file_path',
            'audio_segment_path', 'spectrogram_path', 'quality_status'
        ]
        
        with sqlite3.connect(db_path) as conn:
            where_conditions = []
            params = []
            
            if session_filter and session_filter != "すべて":
                where_conditions.append("session_name = ?")
                params.append(session_filter)
            
            if species_filter and species_filter != "すべて":
                where_conditions.append("common_name = ?")
                params.append(species_filter)
            
            if confidence_min > 0.0:
                where_conditions.append("confidence >= ?")
                params.append(confidence_min)
            
            # 品質評価フィルタを追加
            if quality_filter and quality_filter != "すべて":
                quality_mapping = {
                    "⏳ 評価待ち": "pending",
                    "✅ 承認済み": "approved",
                    "❌ 却下": "rejected"
                }
                quality_status = quality_mapping.get(quality_filter)
                if quality_status:
                    where_conditions.append("quality_status = ?")
                    params.append(quality_status)
            
            columns_str = ", ".join(required_columns)
            query = f"SELECT {columns_str} FROM bird_detections"
            
            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)
            
            query += " ORDER BY created_at DESC"
            
            df = pd.read_sql_query(query, conn, params=params)
            return df
            
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return pd.DataFrame()

def get_file_paths(detection_id, session_name, audio_segment_path, spectrogram_path):
    """生成ファイルの実際のパスを構築"""
    database_root = project_root / "database"
    
    file_paths = {
        'audio_segment': None,
        'spectrogram': None,
        'audio_exists': False,
        'spectrogram_exists': False
    }
    
    # データベースのパス情報を使用
    if audio_segment_path:
        audio_path = database_root / audio_segment_path
        if audio_path.exists():
            file_paths['audio_segment'] = audio_path
            file_paths['audio_exists'] = True
    
    if spectrogram_path:
        spectrogram_full_path = database_root / spectrogram_path
        if spectrogram_full_path.exists():
            file_paths['spectrogram'] = spectrogram_full_path
            file_paths['spectrogram_exists'] = True
    
    # パスが見つからない場合は推測で検索
    if not file_paths['audio_exists'] or not file_paths['spectrogram_exists']:
        audio_segments_dir = database_root / "audio_segments" / session_name
        spectrograms_dir = database_root / "spectrograms" / session_name
        
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

def generate_files(detection_id, generation_type):
    """ファイル生成処理を実行"""
    try:
        enable_spectrogram = generation_type in ['both', 'spectrogram']
        manager = ProcessingManager(enable_spectrogram=enable_spectrogram)
        
        with st.spinner(f"生成中... ({generation_type})"):
            success, message = manager.process_single_detection(detection_id)
            
        if success:
            st.success(f"✅ {message}")
            
            # キャッシュをクリアしてデータを強制更新
            st.cache_data.clear()
            
            # 現在の検索条件でデータを再取得
            if 'last_search_params' in st.session_state:
                db_path = DatabaseConfig.get_database_path()
                params = st.session_state.last_search_params
                updated_df = get_filtered_data(
                    db_path, 
                    params.get('session_filter'), 
                    params.get('species_filter'), 
                    params.get('confidence_min', 0.0),
                    params.get('quality_filter')
                )
                if not updated_df.empty:
                    st.session_state.data = updated_df
            
            # 選択状態を復元するフラグを設定
            st.session_state.restore_selection = True
            
            # 短時間待機後に再実行
            time.sleep(0.5)
            st.rerun()
        else:
            st.error(f"❌ {message}")
            
    except Exception as e:
        st.error(f"❌ 生成エラー: {e}")

def update_quality_status(detection_id, new_status):
    """品質評価ステータスを更新"""
    try:
        db = get_database()
        if db is None:
            st.error("データベース接続エラー")
            return False
            
        db_path = DatabaseConfig.get_database_path()
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # テーブル構造を確認
            cursor.execute("PRAGMA table_info(bird_detections)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # quality_statusカラムが存在しない場合は追加
            if 'quality_status' not in columns:
                st.warning("品質評価カラムが存在しません。データベースをアップグレードしています...")
                cursor.execute(
                    "ALTER TABLE bird_detections ADD COLUMN quality_status TEXT DEFAULT 'pending' CHECK(quality_status IN ('pending', 'approved', 'rejected'))"
                )
                cursor.execute(
                    "ALTER TABLE bird_detections ADD COLUMN reviewed_at TIMESTAMP"
                )
                conn.commit()
                st.success("✅ データベースをアップグレードしました")
                time.sleep(1)
            
            # ステータス更新
            if 'reviewed_at' in columns or 'quality_status' not in columns:  # アップグレード後はreviewed_atもある
                cursor.execute(
                    "UPDATE bird_detections SET quality_status = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_status, detection_id)
                )
            else:
                cursor.execute(
                    "UPDATE bird_detections SET quality_status = ? WHERE id = ?",
                    (new_status, detection_id)
                )
            
            conn.commit()
            
            if cursor.rowcount > 0:
                status_labels = {
                    'approved': '承認済み',
                    'rejected': '却下',
                    'pending': '評価待ち'
                }
                st.success(f"✅ 品質評価を「{status_labels.get(new_status, new_status)}」に変更しました")
                
                # キャッシュをクリアしてデータを強制更新
                st.cache_data.clear()
                
                # 現在の検索条件でデータを再取得
                if 'last_search_params' in st.session_state:
                    params = st.session_state.last_search_params
                    updated_df = get_filtered_data(
                        db_path, 
                        params.get('session_filter'), 
                        params.get('species_filter'), 
                        params.get('confidence_min', 0.0),
                        params.get('quality_filter')
                    )
                    if not updated_df.empty:
                        st.session_state.data = updated_df
                
                # 選択状態を復元するフラグを設定
                st.session_state.restore_selection = True
                
                # 短時間待機後に再実行
                time.sleep(0.3)
                st.rerun()
                return True
            else:
                st.error("❌ ステータス更新に失敗しました")
                return False
                
    except Exception as e:
        st.error(f"❌ ステータス更新エラー: {e}")
        return False

def show_preview_area(selected_record):
    """選択されたレコードのプレビューエリアを表示"""
    if not selected_record:
        st.markdown("""
        <div class="preview-card">
            <h4>📋 選択してください</h4>
            <p>テーブルから行を選択すると、ここに音声とスペクトログラムが表示されます。</p>
            <p><strong>⚙️ ファイルがない場合は、生成ボタンで作成できます。</strong></p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # ファイルパスを取得
    detection_id = selected_record.get('id')
    session_name = selected_record.get('session_name', 'default')
    audio_segment_path = selected_record.get('audio_segment_path')
    spectrogram_path = selected_record.get('spectrogram_path')
    
    file_paths = get_file_paths(detection_id, session_name, audio_segment_path, spectrogram_path)
    
    # ヘッダー情報
    try:
        confidence = float(selected_record.get('confidence', 0))
        confidence_text = f"{confidence:.1%}"
    except:
        confidence_text = "N/A"
    
    st.markdown(f"""
    <div class="preview-card">
        <h4>🎵 {selected_record.get('common_name', '不明')}</h4>
        <div class="compact-info">
            <strong>信頼度:</strong> {confidence_text} | 
            <strong>ファイル:</strong> {selected_record.get('filename', 'N/A')[:40]}{'...' if len(selected_record.get('filename', '')) > 40 else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # メインコンテンツ - 2列レイアウト
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # スペクトログラム表示
        if file_paths['spectrogram_exists']:
            st.image(str(file_paths['spectrogram']), use_container_width=True)
        else:
            st.markdown("""
            <div style="background: #e9ecef; padding: 2rem; border-radius: 10px; text-align: center;">
                <h5>📊 スペクトログラム未生成</h5>
                <p>下のボタンで生成できます</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # 音声プレイヤーと操作
        if file_paths['audio_exists']:
            st.markdown("**🎵 音声セグメント**")
            try:
                with open(file_paths['audio_segment'], 'rb') as audio_file:
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format='audio/wav')
                
                # ダウンロードボタン
                if file_paths['spectrogram_exists']:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.download_button(
                            label="🎵 音声",
                            data=audio_bytes,
                            file_name=file_paths['audio_segment'].name,
                            mime="audio/wav",
                            use_container_width=True
                        )
                    with col_b:
                        with open(file_paths['spectrogram'], 'rb') as img_file:
                            img_bytes = img_file.read()
                        st.download_button(
                            label="📊 画像",
                            data=img_bytes,
                            file_name=file_paths['spectrogram'].name,
                            mime="image/png",
                            use_container_width=True
                        )
                else:
                    st.download_button(
                        label="📥 音声ダウンロード",
                        data=audio_bytes,
                        file_name=file_paths['audio_segment'].name,
                        mime="audio/wav",
                        use_container_width=True
                    )
                    
            except Exception as e:
                st.error(f"音声読み込みエラー: {e}")
        else:
            st.markdown("**🎵 音声セグメント**")
            st.info("下のボタンで音声セグメントを生成できます")
        
        # 品質評価エリア
        st.markdown("---")
        st.markdown("**🏆 品質評価**")
        
        current_status = selected_record.get('quality_status', 'pending')
        status_labels = {
            'pending': '⏳ 評価待ち',
            'approved': '✅ 承認済み',
            'rejected': '❌ 却下'
        }
        
        current_label = status_labels.get(current_status, '❓ 不明')
        st.caption(f"現在のステータス: {current_label}")
        
        # 品質評価変更ボタン
        col_q1, col_q2, col_q3 = st.columns(3)
        
        with col_q1:
            if st.button("✅ 承認", 
                        use_container_width=True, 
                        type="primary" if current_status != 'approved' else "secondary",
                        disabled=current_status == 'approved',
                        help="この検出結果を承認します"):
                update_quality_status(detection_id, 'approved')
        
        with col_q2:
            if st.button("❌ 却下", 
                        use_container_width=True,
                        type="primary" if current_status != 'rejected' else "secondary", 
                        disabled=current_status == 'rejected',
                        help="この検出結果を却下します"):
                update_quality_status(detection_id, 'rejected')
        
        with col_q3:
            if st.button("⏳ 保留", 
                        use_container_width=True,
                        type="primary" if current_status != 'pending' else "secondary",
                        disabled=current_status == 'pending', 
                        help="評価を保留状態に戻します"):
                update_quality_status(detection_id, 'pending')
        
        # ファイル生成ボタンエリア
        st.markdown("---")
        st.markdown("**⚙️ ファイル生成**")
        
        # 既存ファイルの状況表示
        file_status = f"音声 {'✅' if file_paths['audio_exists'] else '❌'} | 画像 {'✅' if file_paths['spectrogram_exists'] else '❌'}"
        st.caption(f"現在の状況: {file_status}")
        
        col_gen1, col_gen2, col_gen3 = st.columns(3)
        with col_gen1:
            audio_label = "🔄 音声" if file_paths['audio_exists'] else "🎵 音声"
            if st.button(audio_label, use_container_width=True, help="音声セグメントを生成（既存の場合上書き）"):
                generate_files(detection_id, 'audio')
        
        with col_gen2:
            spectrogram_label = "🔄 画像" if file_paths['spectrogram_exists'] else "📊 画像"
            if st.button(spectrogram_label, use_container_width=True, help="スペクトログラムを生成（既存の場合上書き）"):
                generate_files(detection_id, 'spectrogram')
        
        with col_gen3:
            both_label = "🔄 両方" if (file_paths['audio_exists'] or file_paths['spectrogram_exists']) else "✨ 両方"
            if st.button(both_label, use_container_width=True, help="音声+スペクトログラムを生成（既存の場合上書き）"):
                generate_files(detection_id, 'both')

def show_search_filters(db_path):
    """検索フィルタUIを表示"""
    st.sidebar.markdown("### 🔍 検索・フィルタ")
    
    sessions = get_unique_sessions(db_path)
    session_options = ["すべて"] + sessions
    selected_session = st.sidebar.selectbox("セッション名", session_options, help="特定のセッションで絞り込み")
    
    species = get_unique_species(db_path)
    species_options = ["すべて"] + species
    selected_species = st.sidebar.selectbox("種名", species_options, help="特定の種で絞り込み")
    
    confidence_min = st.sidebar.slider("信頼度（以上）", min_value=0.0, max_value=1.0, value=0.0, step=0.01, help="指定値以上の信頼度で絞り込み")
    
    # 品質評価ステータスフィルタ
    quality_options = [
        "すべて",
        "⏳ 評価待ち",
        "✅ 承認済み", 
        "❌ 却下"
    ]
    selected_quality = st.sidebar.selectbox("品質評価", quality_options, help="品質評価ステータスで絞り込み")
    
    return selected_session, selected_species, confidence_min, selected_quality

def show_data_view():
    """データ表示機能"""
    db = get_database()
    if db is None:
        return
    
    db_path = DatabaseConfig.get_database_path()
    
    session_filter, species_filter, confidence_min, quality_filter = show_search_filters(db_path)
    
    search_button = st.sidebar.button("🔍 検索実行", type="primary", use_container_width=True)
    
    if st.sidebar.button("🗑️ 条件クリア", use_container_width=True):
        # セッション状態をクリア
        keys_to_remove = ['data', 'search_executed', 'last_search_params', 'selected_record', 'selected_row_index', 'restore_selection']
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
        
        # キャッシュをクリア
        st.cache_data.clear()
        st.rerun()
    
    if search_button or 'search_executed' not in st.session_state:
        # 検索条件を常に保存
        st.session_state.last_search_params = {
            'session_filter': session_filter,
            'species_filter': species_filter,
            'confidence_min': confidence_min,
            'quality_filter': quality_filter
        }
        
        with st.spinner("データを取得中..."):
            df = get_filtered_data(db_path, session_filter, species_filter, confidence_min, quality_filter)
            
            if not df.empty:
                st.session_state.data = df
                st.session_state.search_executed = True
                
                st.success(f"✅ {len(df):,} 件見つかりました")
                
                # 処理状況サマリー（パスベース）
                if 'audio_segment_path' in df.columns:
                    audio_count = df['audio_segment_path'].notna().sum()
                    spectrogram_count = df['spectrogram_path'].notna().sum() if 'spectrogram_path' in df.columns else 0
                    
                    # メトリクス表示（上段：ファイル生成状況）
                    st.markdown("**📊 ファイル生成状況**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🎵 音声生成済み", f"{audio_count}/{len(df)}")
                    with col2:
                        st.metric("📊 スペクトログラム生成済み", f"{spectrogram_count}/{len(df)}")
                    with col3:
                        st.metric("⏳ 未処理", f"{len(df) - max(audio_count, spectrogram_count)}")
                    
                    # 品質評価状況の集計（quality_statusカラムが存在する場合のみ）
                    if 'quality_status' in df.columns:
                        quality_counts = df['quality_status'].value_counts()
                        approved_count = quality_counts.get('approved', 0)
                        rejected_count = quality_counts.get('rejected', 0)
                        pending_count = quality_counts.get('pending', 0)
                        # NaN値をpendingとしてカウント
                        nan_count = df['quality_status'].isna().sum()
                        pending_count += nan_count
                        
                        # メトリクス表示（下段：品質評価状況）
                        st.markdown("**🏆 品質評価状況**")
                        col4, col5, col6 = st.columns(3)
                        with col4:
                            st.metric("✅ 承認済み", f"{approved_count}/{len(df)}")
                        with col5:
                            st.metric("❌ 却下", f"{rejected_count}/{len(df)}")
                        with col6:
                            st.metric("⏳ 評価待ち", f"{pending_count}/{len(df)}")
                    else:
                        # quality_statusカラムがない場合の通知
                        st.info("📊 品質評価機能を使用するには、データベースのアップグレードが必要です。")
                
                conditions = []
                if session_filter and session_filter != "すべて":
                    conditions.append(f"セッション: {session_filter}")
                if species_filter and species_filter != "すべて":
                    conditions.append(f"種名: {species_filter}")
                if confidence_min > 0.0:
                    conditions.append(f"信頼度: {confidence_min:.2f}以上")
                if quality_filter and quality_filter != "すべて":
                    conditions.append(f"品質評価: {quality_filter}")
                
                if conditions:
                    st.info(f"検索条件: {' / '.join(conditions)}")
                else:
                    st.info("検索条件: すべて")
            else:
                st.warning("⚠️ 検索条件に一致するデータがありません")
                return
    
    if 'data' in st.session_state and not st.session_state.data.empty:
        df = st.session_state.data
        
        # テーブル表示用のデータ準備
        display_df = df.copy()
        
        # 削除するカラム（モデル、quality_statusを追加）
        columns_to_drop = ['id', 'file_path', 'scientific_name', 'audio_segment_path', 'spectrogram_path', 'model_name', 'quality_status']
        display_df = display_df.drop(columns=[col for col in columns_to_drop if col in display_df.columns])
        
        # 処理状況カラムを追加（パスベース）
        if 'audio_segment_path' in df.columns:
            display_df['音声'] = df['audio_segment_path'].apply(lambda x: '✅' if pd.notna(x) else '❌')
        if 'spectrogram_path' in df.columns:
            display_df['スペクトログラム'] = df['spectrogram_path'].apply(lambda x: '✅' if pd.notna(x) else '❌')
        
        # 人間による品質評価カラムを追加
        def get_quality_evaluation(row):
            """品質評価ステータスを表示"""
            quality_status = row.get('quality_status', 'pending')
            
            if pd.isna(quality_status) or quality_status is None:
                return "⏳ 評価待ち"  # デフォルト値
            elif quality_status == 'approved':
                return "✅ 承認済み"
            elif quality_status == 'rejected':
                return "❌ 却下"
            elif quality_status == 'pending':
                return "⏳ 評価待ち"
            else:
                return "❓ 不明"
        
        # quality_statusカラムが存在する場合のみ品質評価カラムを追加
        if 'quality_status' in df.columns:
            display_df['品質評価'] = df.apply(get_quality_evaluation, axis=1)
        else:
            # quality_statusカラムが存在しない場合はプレースホルダー
            display_df['品質評価'] = "⚠️ 未対応"
        
        # カラム名を日本語に変更
        display_df = display_df.rename(columns={
            'session_name': 'セッション名',
            'common_name': '種名',
            'confidence': '信頼度',
            'start_time_seconds': '開始(秒)',
            'end_time_seconds': '終了(秒)',
            'filename': 'ファイル名'
        })
        
        # カラムの順序を明示的に指定（ファイル名を最後に）
        desired_order = [
            'セッション名',
            '種名', 
            '信頼度',
            '品質評価',
            '開始(秒)',
            '終了(秒)',
            '音声',
            'スペクトログラム',
            'ファイル名'
        ]
        
        # 存在するカラムのみで順序を調整
        final_columns = [col for col in desired_order if col in display_df.columns]
        # 上記にないカラムがある場合は追加
        for col in display_df.columns:
            if col not in final_columns:
                final_columns.insert(-1, col)  # ファイル名の手前に挿入
        
        display_df = display_df[final_columns]
        
        if '信頼度' in display_df.columns:
            def format_confidence(x):
                try:
                    if pd.isna(x):
                        return "N/A"
                    if isinstance(x, str) and '%' in x:
                        return x
                    if isinstance(x, (int, float)):
                        return f"{x:.1%}"
                    return "N/A"
                except:
                    return "N/A"
            
            display_df['信頼度'] = display_df['信頼度'].apply(format_confidence)
        
        for time_col in ['開始(秒)', '終了(秒)']:
            if time_col in display_df.columns:
                def format_time(x):
                    try:
                        if pd.isna(x):
                            return "N/A"
                        if isinstance(x, str) and x != "N/A":
                            try:
                                float(x)
                                return x
                            except:
                                return x
                        if isinstance(x, (int, float)):
                            return f"{x:.1f}"
                        return "N/A"
                    except:
                        return "N/A"
                
                display_df[time_col] = display_df[time_col].apply(format_time)
        
        # データテーブル表示
        st.subheader("📊 検索結果")
        
        # 選択状態の復元を確認
        initial_selection = None
        if 'restore_selection' in st.session_state and st.session_state.restore_selection:
            if 'selected_record' in st.session_state and st.session_state.selected_record:
                # 更新されたデータから同じIDのレコードのインデックスを見つける
                selected_id = st.session_state.selected_record.get('id')
                if selected_id:
                    matching_indices = df.index[df['id'] == selected_id].tolist()
                    if matching_indices:
                        initial_selection = {"rows": [matching_indices[0]]}
            # フラグをクリア
            st.session_state.restore_selection = False
        
        event = st.dataframe(
            display_df, 
            use_container_width=True, 
            height=300,
            on_select="rerun",
            selection_mode="single-row",
            key="data_table"
        )
        
        # 選択された行の情報を取得・保持
        selected_record = None
        
        if event.selection.rows:
            # 新しい選択がある場合
            selected_idx = event.selection.rows[0]
            selected_record = df.iloc[selected_idx].to_dict()
            # 現在選択された行の情報を保存
            st.session_state.selected_record = selected_record
            st.session_state.selected_row_index = selected_idx
        elif 'selected_record' in st.session_state and st.session_state.selected_record:
            # 選択がないが、以前の選択情報がある場合（アクション後の復元）
            selected_record = st.session_state.selected_record
            # 更新されたデータから同じIDのレコードを再取得して最新化
            if 'id' in selected_record:
                matching_rows = df[df['id'] == selected_record['id']]
                if not matching_rows.empty:
                    # 最新のデータで選択レコードを更新
                    selected_record = matching_rows.iloc[0].to_dict()
                    st.session_state.selected_record = selected_record
        
        # プレビューエリア表示
        st.subheader("🎵 プレビュー")
        show_preview_area(selected_record)
        
        # エクスポート
        st.subheader("📊 エクスポート")
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📊 CSV ダウンロード",
            data=csv,
            file_name=f"birdnet_search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def main():
    st.title("🐦 BirdNet データベースビューワー")
    st.markdown("検索・フィルタ機能 + リアルタイムプレビュー")
    
    with st.sidebar:
        if st.button("🔄 リロード", use_container_width=True):
            # 全てのセッション状態をクリア
            keys_to_remove = ['data', 'search_executed', 'last_search_params', 'selected_record', 'selected_row_index', 'restore_selection']
            for key in keys_to_remove:
                if key in st.session_state:
                    del st.session_state[key]
            
            # 全てのキャッシュをクリア
            st.cache_resource.clear()
            st.cache_data.clear()
            st.rerun()
    
    show_data_view()

if __name__ == "__main__":
    main()
