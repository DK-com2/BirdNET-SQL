#!/usr/bin/env python3
"""
BirdNet データベースビューワー
シンプルなデータ表示に特化
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

def get_filtered_data(db_path, limit=None):
    """必要なカラムのみでデータを直接取得"""
    try:
        # 必要なカラムのみを指定してデータ取得
        required_columns = [
            'session_name', 'model_name', 'common_name', 
            'confidence', 'start_time_seconds', 'end_time_seconds', 'filename'
        ]
        
        with sqlite3.connect(db_path) as conn:
            # 存在するカラムのみを選択
            select_columns = []
            for col in required_columns:
                select_columns.append(col)
            
            # SQLクエリ作成
            columns_str = ", ".join(select_columns)
            query = f"SELECT {columns_str} FROM bird_detections ORDER BY created_at DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            # データ取得
            df = pd.read_sql_query(query, conn)
            return df
            
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return pd.DataFrame()

def show_data_view():
    """データ表示機能"""
    db = get_database()
    if db is None:
        return
    
    # データベースパスを取得
    db_path = DatabaseConfig.get_database_path()
    
    # 全件取得
    df = get_filtered_data(db_path, limit=None)
    
    if not df.empty:
        st.session_state.data = df
    else:
        st.warning("データがありません")
        return
    
    # データ表示
    if 'data' in st.session_state and not st.session_state.data.empty:
        df = st.session_state.data
        
        # データテーブル表示のみ
        st.dataframe(df, use_container_width=True, height=600)
        
        # CSVエクスポートのみ
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📊 CSV ダウンロード",
            data=csv,
            file_name=f"birdnet_detections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def main():
    # シンプルなヘッダー
    st.title("🐦 BirdNet データベースビューワー")
    
    # サイドバーは最小限に
    with st.sidebar:
        # リロードボタンのみ
        if st.button("🔄 リロード", type="primary", use_container_width=True):
            if 'data' in st.session_state:
                del st.session_state.data
            st.cache_resource.clear()
            st.rerun()
    
    # メインコンテンツ
    show_data_view()

if __name__ == "__main__":
    main()
