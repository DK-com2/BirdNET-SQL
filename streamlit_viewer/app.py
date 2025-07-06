#!/usr/bin/env python3
"""
BirdNet 解析&ビューアー
モダンなデザインでシンプルにリファクタリング
"""

import streamlit as st
import pandas as pd
import sys
import os
from pathlib import Path
from datetime import datetime

# 解析モジュールをインポート
try:
    from analyzer import SimpleBirdNetAnalyzer
except ImportError as e:
    st.error(f"解析モジュールの読み込みに失敗: {e}")
    st.stop()

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
    page_title="BirdNet AI 解析",
    page_icon="🐦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
/* メインコンテナ */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* サイドバー */
.css-1d391kg {
    background-color: #f8f9fa;
}

/* メトリクス */
.metric-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin: 0.5rem 0;
}

/* カードスタイル */
.card {
    background: white;
    padding: 1.5rem;
    border-radius: 15px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    margin: 1rem 0;
    border-left: 4px solid #667eea;
}

/* ステータスアイコン */
.status-ok { color: #28a745; }
.status-error { color: #dc3545; }
.status-warning { color: #ffc107; }

/* ヘッダー */
.header {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem;
    border-radius: 15px;
    text-align: center;
    margin-bottom: 2rem;
}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_database():
    """データベースを読み込み（キャッシュ付き）"""
    try:
        db_path = get_database_path()
        st.info(f"データベースパス: {db_path}")
        
        # ファイルの存在確認
        if not os.path.exists(db_path):
            st.error(f"データベースファイルが見つかりません: {db_path}")
            
            # 代替パスを試す
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent
            
            alternative_paths = [
                project_root / "database" / "birdnet_simple.db",
                project_root / "database" / "birdnet.db",
                project_root / "database" / "birds.db",
            ]
            
            for alt_path in alternative_paths:
                if alt_path.exists():
                    st.warning(f"代替データベースを発見: {alt_path}")
                    db_path = str(alt_path)
                    break
            else:
                st.error("データベースファイルがどこにも見つかりません")
                return None
        
        # データベース接続テスト
        db = BirdNetSimpleDB(db_path)
        
        # 簡単なテストクエリ
        try:
            stats = db.get_statistics()
            if stats:
                st.success(f"✅ データベース接続成功: {stats.get('detection_count', 0)} レコード")
            else:
                st.warning("⚠️ データベースは空です")
        except Exception as e:
            st.error(f"データベーステストエラー: {e}")
        
        return db
        
    except Exception as e:
        st.error(f"データベース接続エラー: {e}")
        return None

def get_database_path():
    """データベースパスを取得（相対パス）"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    db_path = project_root / "database" / "result.db"
    return str(db_path)

@st.cache_resource
def get_analyzer():
    """解析器を取得（キャッシュ付き）"""
    return SimpleBirdNetAnalyzer()

def show_analysis_page():
    """解析実行ページ"""
    st.markdown("## 🚀 音声解析")
    
    analyzer = get_analyzer()
    
    # 音声ファイル情報
    audio_files = analyzer.get_audio_files()
    custom_models = analyzer.get_custom_models()
    
    if not audio_files:
        st.error("🚨 音声ファイルが見つかりません")
        st.info(f"📁 音声ファイルを `{analyzer.audio_folder}` に配置してください")
        return
    
    # 解析設定カード
    st.markdown("""
    <div class="card">
        <h3>🎯 解析設定</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🤖 モデル選択")
        model_options = ["default (標準BirdNet)"] + custom_models
        selected_display = st.selectbox(
            "使用モデル",
            model_options,
            help="標準モデルまたはカスタムモデルを選択"
        )
        
        if selected_display == "default (標準BirdNet)":
            selected_model = "default"
            st.info("🌍 標準モデル: 世界中の鳥類に対応")
        else:
            selected_model = selected_display
            st.success(f"🎯 カスタムモデル: {selected_model}")
    
    with col2:
        st.subheader("📝 セッション")
        default_session = f"session_{datetime.now().strftime('%m%d_%H%M')}"
        session_name = st.text_input(
            "セッション名",
            value=default_session,
            help="解析結果を識別するための名前"
        )
        
        st.metric("🎧 処理対象", f"{len(audio_files)}件")
    
    # ファイル一覧
    with st.expander("📁 処理対象ファイル一覧"):
        for i, file in enumerate(audio_files, 1):
            st.write(f"{i}. {file}")
    
    st.markdown("---")
    
    # 解析実行ボタン
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("🚀 解析開始", type="primary", use_container_width=True):
            if not session_name.strip():
                st.error("🚨 セッション名を入力してください")
            else:
                st.session_state.start_analysis = True
                st.session_state.analysis_model = selected_model
                st.session_state.analysis_session = session_name.strip()
                st.rerun()
    
    with col2:
        if st.button("🔄 リセット", use_container_width=True):
            st.cache_resource.clear()
            for key in list(st.session_state.keys()):
                if key.startswith('analysis_') or key == 'start_analysis':
                    del st.session_state[key]
            st.rerun()
    
    # 解析実行処理
    if st.session_state.get('start_analysis', False):
        model = st.session_state.analysis_model
        session = st.session_state.analysis_session
        
        st.markdown("""
        <div class="card">
            <h3>📈 解析進行中...</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # プログレスバー
        progress_container = st.container()
        status_container = st.container()
        
        with progress_container:
            progress = st.progress(0)
        
        with status_container:
            status = st.empty()
        
        # 1. 解析実行
        status.info("🔍 音声解析中...")
        progress.progress(30)
        
        success1, msg1 = analyzer.run_analysis(model)
        
        if success1:
            progress.progress(70)
            status.info("💾 データベース保存中...")
            
            # 2. DB保存
            success2, msg2 = analyzer.save_to_db(session, model)
            
            progress.progress(100)
            
            if success2:
                status.success(f"✅ 完了: {msg1} / {msg2}")
                analyzer.move_files_after_analysis(True)
                st.balloons()
                
                # 結果表示
                st.markdown("""
                <div class="card">
                    <h3>✅ 解析完了</h3>
                    <p>音声ファイルが正常に処理され、データベースに保存されました。</p>
                </div>
                """, unsafe_allow_html=True)
                
            else:
                status.warning(f"⚠️ 解析成功、DB保存失敗: {msg2}")
                analyzer.move_files_after_analysis(False)
        else:
            status.error(f"❌ 解析失敗: {msg1}")
            analyzer.move_files_after_analysis(False)
        
        # 状態リセット
        st.session_state.start_analysis = False

def show_database_page():
    """データベース表示ページ（修正版）"""
    st.markdown("## 📊 データベース表示")
    
    # データベース読み込み
    db = get_database()
    
    if db is None:
        st.error("データベースに接続できませんでした")
        return
    
    # データベース全体の統計を取得
    try:
        total_stats = db.get_statistics()
        total_records = total_stats.get('detection_count', 0) if total_stats else 0
    except Exception as e:
        st.error(f"統計取得エラー: {e}")
        total_records = 0
    
    # サイドバー設定
    with st.sidebar:
        st.markdown("### 📊 データ取得設定")
        
        # 全体統計の表示
        st.markdown("#### 📈 データベース全体")
        if total_records > 0:
            st.success(f"総レコード数: {total_records:,} 件")
        else:
            st.warning("データなし")
        
        st.markdown("---")
        
        # デバッグモード
        debug_mode = st.checkbox("🔧 デバッグモード", value=False)
        
        # データ取得件数
        limit_options = [10, 50, 100, 500, 1000]
        if total_records > 0:
            # 全件取得オプションを追加
            limit_options.append(min(total_records, 10000))  # 最大10,000件まで
        
        limit = st.selectbox("取得件数", limit_options, index=1)
        
        # 全件取得オプション
        if total_records > 0 and total_records <= 10000:
            get_all = st.checkbox(f"全件取得 ({total_records:,} 件)", value=False)
            if get_all:
                limit = total_records
        
        st.markdown("---")
        
        # データ取得ボタン
        if st.button("📊 データ取得", type="primary", use_container_width=True):
            with st.spinner("データを取得中..."):
                try:
                    # データベースからデータ取得
                    detections = db.get_detections(limit=limit)
                    
                    if debug_mode:
                        st.write(f"📊 要求件数: {limit:,}")
                        st.write(f"📥 取得データ数: {len(detections)}")
                        if detections:
                            st.write("🔍 最初のレコード:")
                            st.json(detections[0])
                    
                    if detections:
                        # DataFrameに変換
                        df = pd.DataFrame(detections)
                        st.session_state.data = df
                        st.session_state.requested_limit = limit
                        
                        # 取得成功メッセージ
                        if len(detections) == limit and limit < total_records:
                            st.info(f"✅ {len(detections):,} 件取得（制限: {limit:,} 件）")
                        else:
                            st.success(f"✅ {len(detections):,} 件取得完了")
                        
                        if debug_mode:
                            st.write(f"📊 DataFrame形状: {df.shape}")
                            st.write(f"📝 カラム: {list(df.columns)}")
                            st.write("🏷️ データ型:")
                            for col in df.columns:
                                st.write(f"  {col}: {df[col].dtype}")
                    else:
                        st.warning("⚠️ データが取得できませんでした")
                        
                except Exception as e:
                    st.error(f"❌ データ取得エラー: {e}")
                    if debug_mode:
                        st.exception(e)
        
        # クリアボタン
        if 'data' in st.session_state:
            if st.button("🗑️ データクリア", use_container_width=True):
                if 'data' in st.session_state:
                    del st.session_state.data
                if 'requested_limit' in st.session_state:
                    del st.session_state.requested_limit
                st.rerun()
    
    # メインコンテンツ
    if 'data' in st.session_state:
        df = st.session_state.data
        requested_limit = st.session_state.get('requested_limit', 'Unknown')
        
        # ヘッダー情報
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader(f"📋 検出結果")
        
        with col2:
            if len(df) == requested_limit and requested_limit < total_records:
                st.warning(f"表示: {len(df):,} / {total_records:,} 件")
            else:
                st.success(f"表示: {len(df):,} 件")
        
        with col3:
            if len(df) < total_records:
                st.info(f"残り: {total_records - len(df):,} 件")
        
        # データテーブル表示
        st.dataframe(df, use_container_width=True, height=400)
        
        # 基本統計
        if not df.empty:
            st.markdown("### 📊 表示データ統計")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("表示件数", f"{len(df):,}")
            
            with col2:
                if 'common_name' in df.columns:
                    unique_species = df['common_name'].nunique()
                    st.metric("表示種数", f"{unique_species:,}")
                else:
                    st.metric("表示種数", "N/A")
            
            with col3:
                if 'confidence' in df.columns:
                    avg_conf = df['confidence'].mean()
                    st.metric("平均信頼度", f"{avg_conf:.3f}")
                else:
                    st.metric("平均信頼度", "N/A")
            
            with col4:
                if 'filename' in df.columns:
                    unique_files = df['filename'].nunique()
                    st.metric("ファイル数", f"{unique_files:,}")
                else:
                    st.metric("ファイル数", "N/A")
        
        # データのサンプル表示
        if len(df) > 0:
            with st.expander("📝 データサンプル（最初の5行）"):
                st.dataframe(df.head(), use_container_width=True)
        
        # データエクスポート
        if len(df) > 0:
            st.markdown("### 📥 データエクスポート")
            col1, col2 = st.columns([1, 3])
            
            with col1:
                if st.button("📊 CSV ダウンロード", type="secondary"):
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="💾 ファイルをダウンロード",
                        data=csv,
                        file_name=f"birdnet_detections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                st.info(f"エクスポート対象: {len(df):,} 件のレコード")
        
        # 全体統計との比較
        if total_records > len(df):
            st.markdown("### ⚠️ 注意事項")
            st.warning(f"""
            現在表示されているのはデータベース全体（{total_records:,} 件）の一部（{len(df):,} 件）です。
            
            全件を表示するには：
            1. サイドバーで「全件取得」にチェック
            2. または「取得件数」を {total_records:,} に設定
            3. 「📊 データ取得」ボタンをクリック
            """)
    
    else:
        # データが未取得の場合
        st.info("👈 左側の「📊 データ取得」ボタンを押してデータを表示してください")
        
        # データベース情報を表示
        if total_records > 0:
            st.markdown("### 📈 データベース概要")
            try:
                stats = db.get_statistics()
                if stats:
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("総レコード数", f"{stats.get('detection_count', 0):,}")
                    
                    with col2:
                        st.metric("ユニーク種数", f"{stats.get('unique_species', 0):,}")
                    
                    with col3:
                        st.metric("ユニークファイル数", f"{stats.get('unique_files', 0):,}")
                    
                    with col4:
                        avg_conf = stats.get('avg_confidence', 0)
                        st.metric("平均信頼度", f"{avg_conf:.3f}")
            except Exception as e:
                st.error(f"統計情報取得エラー: {e}")

def main():
    # ヘッダー
    st.markdown("""
    <div class="header">
        <h1>🐦 BirdNet AI 解析システム</h1>
        <p>高精度な鳥類音声解析とデータ管理</p>
    </div>
    """, unsafe_allow_html=True)
    
    # サイドバーでページ選択
    with st.sidebar:
        st.markdown("### 📊 ナビゲーション")
        
        page = st.radio(
            "ページを選択",
            ["🚀 解析実行", "📊 データベース"],
            index=0
        )
        
        st.markdown("---")
        
        # システム情報
        st.markdown("### ⚙️ システム情報")
        
        # 解析器初期化
        analyzer = get_analyzer()
        
        # 音声ファイル情報
        audio_files = analyzer.get_audio_files()
        audio_count = len(audio_files)
        
        if audio_count > 0:
            st.markdown(f'<div class="status-ok">✅ 音声ファイル: {audio_count}件</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-error">❌ 音声ファイル: 0件</div>', unsafe_allow_html=True)
        
        # カスタムモデル情報
        custom_models = analyzer.get_custom_models()
        model_count = len(custom_models)
        
        if model_count > 0:
            st.markdown(f'<div class="status-ok">✅ カスタムモデル: {model_count}件</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-warning">⚠️ カスタムモデル: 0件</div>', unsafe_allow_html=True)
        
        # データベース情報
        try:
            db = get_database()
            if db:
                stats = db.get_statistics()
                detection_count = stats.get('detection_count', 0) if stats else 0
                st.markdown(f'<div class="status-ok">✅ DBレコード: {detection_count}件</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="status-error">❌ DB接続エラー</div>', unsafe_allow_html=True)
        except:
            st.markdown(f'<div class="status-error">❌ DB接続エラー</div>', unsafe_allow_html=True)
    
    # ページ表示
    if page == "🚀 解析実行":
        show_analysis_page()
    elif page == "📊 データベース":
        show_database_page()

if __name__ == "__main__":
    main()
