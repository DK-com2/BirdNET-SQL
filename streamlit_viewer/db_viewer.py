#!/usr/bin/env python3
"""
BirdNet データベースビューワー
検索・フィルタ機能付き
"""

import streamlit as st
import pandas as pd
import sys
import os
import sqlite3
from pathlib import Path
from datetime import datetime

# 設定とユーティリティをインポート
from config import DatabaseConfig, AppConfig

# 親ディレクトリのlibをパスに追加
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
lib_path = project_root / "lib"
sys.path.append(str(lib_path))

try:
    from db.database import BirdNetSimpleDB
except ImportError as e:
    st.error(f"データベースモジュールの読み込みに失敗: {e}")
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

@st.cache_resource
def get_database():
    """データベースを読み込み（キャッシュ付き）"""
    try:
        db_path = DatabaseConfig.get_database_path()
        
        # ファイルの存在確認
        if not os.path.exists(db_path):
            st.error(f"データベースファイルが見つかりません: {db_path}")
            
            # 代替パスを試す
            alternative_paths = DatabaseConfig.get_alternative_paths()
            
            for alt_path in alternative_paths:
                if alt_path.exists():
                    db_path = str(alt_path)
                    break
            else:
                st.error("データベースファイルがどこにも見つかりません")
                return None
        
        # データベース接続テスト
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

def get_filtered_data(db_path, session_filter=None, species_filter=None, confidence_min=0.0):
    """検索条件に基づいてデータを取得"""
    try:
        # 必要なカラムのみを指定
        required_columns = [
            'id', 'session_name', 'model_name', 'common_name', 'scientific_name',
            'confidence', 'start_time_seconds', 'end_time_seconds', 'filename', 'file_path'
        ]
        
        with sqlite3.connect(db_path) as conn:
            # WHERE条件を構築
            where_conditions = []
            params = []
            
            # セッション名フィルタ
            if session_filter and session_filter != "すべて":
                where_conditions.append("session_name = ?")
                params.append(session_filter)
            
            # 種名フィルタ
            if species_filter and species_filter != "すべて":
                where_conditions.append("common_name = ?")
                params.append(species_filter)
            
            # 信頼度フィルタ
            if confidence_min > 0.0:
                where_conditions.append("confidence >= ?")
                params.append(confidence_min)
            
            # SQLクエリ作成
            columns_str = ", ".join(required_columns)
            query = f"SELECT {columns_str} FROM bird_detections"
            
            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)
            
            query += " ORDER BY created_at DESC"
            
            # データ取得
            df = pd.read_sql_query(query, conn, params=params)
            return df
            
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return pd.DataFrame()

def show_search_filters(db_path):
    """検索フィルタUIを表示"""
    st.sidebar.markdown("### 🔍 検索・フィルタ")
    
    # セッション名選択
    sessions = get_unique_sessions(db_path)
    session_options = ["すべて"] + sessions
    selected_session = st.sidebar.selectbox(
        "セッション名",
        session_options,
        help="特定のセッションで絞り込み"
    )
    
    # 種名選択
    species = get_unique_species(db_path)
    species_options = ["すべて"] + species
    selected_species = st.sidebar.selectbox(
        "種名",
        species_options,
        help="特定の種で絞り込み"
    )
    
    # 信頼度フィルタ
    confidence_min = st.sidebar.slider(
        "信頼度（以上）",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.01,
        help="指定値以上の信頼度で絞り込み"
    )
    
    return selected_session, selected_species, confidence_min

def show_data_view():
    """データ表示機能"""
    db = get_database()
    if db is None:
        return
    
    # データベースパスを取得
    db_path = DatabaseConfig.get_database_path()
    
    # 検索フィルタ表示
    session_filter, species_filter, confidence_min = show_search_filters(db_path)
    
    # 検索実行ボタン
    search_button = st.sidebar.button("🔍 検索実行", type="primary", use_container_width=True)
    
    # 検索条件クリアボタン
    if st.sidebar.button("🗑️ 条件クリア", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # 初回読み込みまたは検索実行
    if search_button or 'search_executed' not in st.session_state:
        with st.spinner("データを取得中..."):
            df = get_filtered_data(db_path, session_filter, species_filter, confidence_min)
            
            if not df.empty:
                st.session_state.data = df
                st.session_state.search_executed = True
                
                # 検索結果サマリー
                st.success(f"✅ {len(df):,} 件見つかりました")
                
                # 検索条件表示
                conditions = []
                if session_filter and session_filter != "すべて":
                    conditions.append(f"セッション: {session_filter}")
                if species_filter and species_filter != "すべて":
                    conditions.append(f"種名: {species_filter}")
                if confidence_min > 0.0:
                    conditions.append(f"信頼度: {confidence_min:.2f}以上")
                
                if conditions:
                    st.info(f"検索条件: {' / '.join(conditions)}")
                else:
                    st.info("検索条件: すべて")
            else:
                st.warning("⚠️ 検索条件に一致するデータがありません")
                return
    
    # データ表示
    if 'data' in st.session_state and not st.session_state.data.empty:
        df = st.session_state.data
        
        # データテーブル表示と選択機能
        st.subheader("📊 検索結果")
        
        # 表示用データフレームを作成（id、file_path、scientific_nameは表示しない）
        display_df = df.drop(columns=['id', 'file_path', 'scientific_name'], errors='ignore').copy()
        
        # カラム名を日本語に変更
        display_df = display_df.rename(columns={
            'session_name': 'セッション名',
            'model_name': 'モデル', 
            'common_name': '種名',
            'confidence': '信頼度',
            'start_time_seconds': '開始(秒)',
            'end_time_seconds': '終了(秒)',
            'filename': 'ファイル名'
        })
        
        # 信頼度をパーセント表示に変換（数値のみ）
        if '信頼度' in display_df.columns:
            def format_confidence(x):
                try:
                    if pd.isna(x):
                        return "N/A"
                    # 既に文字列に変換済みの場合（%が含まれている）
                    if isinstance(x, str) and '%' in x:
                        return x
                    # 数値の場合
                    if isinstance(x, (int, float)):
                        return f"{x:.1%}"
                    return "N/A"
                except:
                    return "N/A"
            
            display_df['信頼度'] = display_df['信頼度'].apply(format_confidence)
        
        # 時間を小数点1位に（数値のみ処理）
        for time_col in ['開始(秒)', '終了(秒)']:
            if time_col in display_df.columns:
                def format_time(x):
                    try:
                        if pd.isna(x):
                            return "N/A"
                        # 既に文字列に変換済みの場合
                        if isinstance(x, str) and x != "N/A":
                            try:
                                # 数値に戻せるか試す
                                float(x)
                                return x  # 数値文字列ならそのまま
                            except:
                                return x  # 変換済み文字列ならそのまま
                        # 数値の場合
                        if isinstance(x, (int, float)):
                            return f"{x:.1f}"
                        return "N/A"
                    except:
                        return "N/A"
                
                display_df[time_col] = display_df[time_col].apply(format_time)
        
        # データテーブル表示
        event = st.dataframe(
            display_df, 
            use_container_width=True, 
            height=400,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # 行が選択された時の処理
        if event.selection.rows:
            selected_idx = event.selection.rows[0]
            selected_record = df.iloc[selected_idx].to_dict()
            
            # 選択されたレコード情報を表示
            st.success(f"✅ 選択されたレコード: {selected_record.get('common_name', 'N/A')} - {selected_record.get('filename', 'N/A')}")
            
            # 詳細ページへのボタン
            col1, col2, col3 = st.columns([1, 1, 2])
            with col2:
                if st.button("🎧 音声詳細を表示", type="primary", use_container_width=True):
                    # 選択されたレコードをセッションステートに保存
                    st.session_state.selected_record = selected_record
                    st.switch_page("pages/audio_detail.py")
        
        # CSVエクスポート
        st.subheader("📊 エクスポート")
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📊 CSV ダウンロード",
            data=csv,
            file_name=f"birdnet_search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def main():
    # シンプルなヘッダー
    st.title("🐦 BirdNet データベースビューワー")
    
    # サイドバーは検索機能中心
    with st.sidebar:
        # リロードボタン
        if st.button("🔄 リロード", use_container_width=True):
            if 'data' in st.session_state:
                del st.session_state.data
            if 'search_executed' in st.session_state:
                del st.session_state.search_executed
            st.cache_resource.clear()
            st.cache_data.clear()
            st.rerun()
    
    # メインコンテンツ
    show_data_view()

if __name__ == "__main__":
    main()
