"""
可視化ユーティリティモジュール
グラフ作成、統計表示などの可視化機能
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

# 可視化ライブラリ
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import matplotlib.pyplot as plt
    PLOT_SUPPORT = True
except ImportError:
    PLOT_SUPPORT = False


def check_plot_support() -> bool:
    """可視化ライブラリがサポートされているかチェック"""
    return PLOT_SUPPORT


def create_confidence_histogram(df: pd.DataFrame, bins: int = 30) -> go.Figure:
    """信頼度のヒストグラムを作成"""
    if not PLOT_SUPPORT:
        raise ImportError("可視化ライブラリが利用できません")
    
    if 'confidence' not in df.columns:
        raise ValueError("confidence列が見つかりません")
    
    fig = px.histogram(
        df, 
        x='confidence',
        bins=bins,
        title='検出信頼度の分布',
        labels={'confidence': '信頼度', 'count': '件数'},
        color_discrete_sequence=['#667eea']
    )
    
    fig.update_layout(
        xaxis_title="信頼度",
        yaxis_title="検出数",
        showlegend=False,
        template="plotly_white"
    )
    
    return fig


def create_species_bar_chart(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """種別検出数の棒グラフを作成"""
    if not PLOT_SUPPORT:
        raise ImportError("可視化ライブラリが利用できません")
    
    if 'common_name' not in df.columns:
        raise ValueError("common_name列が見つかりません")
    
    # 種別の検出数を集計
    species_counts = df['common_name'].value_counts().head(top_n)
    
    fig = px.bar(
        x=species_counts.values,
        y=species_counts.index,
        orientation='h',
        title=f'検出数上位{top_n}種',
        labels={'x': '検出数', 'y': '種名'},
        color=species_counts.values,
        color_continuous_scale='viridis'
    )
    
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title="検出数",
        yaxis_title="種名",
        showlegend=False,
        template="plotly_white",
        height=max(400, top_n * 25)
    )
    
    return fig


def create_confidence_by_species_box(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """種別信頼度のボックスプロットを作成"""
    if not PLOT_SUPPORT:
        raise ImportError("可視化ライブラリが利用できません")
    
    if 'common_name' not in df.columns or 'confidence' not in df.columns:
        raise ValueError("必要な列が見つかりません")
    
    # 上位N種を抽出
    top_species = df['common_name'].value_counts().head(top_n).index.tolist()
    filtered_df = df[df['common_name'].isin(top_species)]
    
    fig = px.box(
        filtered_df,
        x='common_name',
        y='confidence',
        title=f'種別信頼度分布（上位{top_n}種）',
        labels={'common_name': '種名', 'confidence': '信頼度'}
    )
    
    fig.update_layout(
        xaxis_title="種名",
        yaxis_title="信頼度",
        xaxis={'tickangle': 45},
        template="plotly_white",
        height=500
    )
    
    return fig


def create_time_series_plot(df: pd.DataFrame, time_column: str = 'date') -> go.Figure:
    """時系列プロットを作成"""
    if not PLOT_SUPPORT:
        raise ImportError("可視化ライブラリが利用できません")
    
    if time_column not in df.columns:
        raise ValueError(f"{time_column}列が見つかりません")
    
    # 日別検出数を集計
    try:
        df_copy = df.copy()
        df_copy[time_column] = pd.to_datetime(df_copy[time_column])
        daily_counts = df_copy.groupby(df_copy[time_column].dt.date).size().reset_index()
        daily_counts.columns = ['date', 'count']
        
        fig = px.line(
            daily_counts,
            x='date',
            y='count',
            title='日別検出数の推移',
            labels={'date': '日付', 'count': '検出数'},
            line_shape='linear'
        )
        
        fig.update_layout(
            xaxis_title="日付",
            yaxis_title="検出数",
            template="plotly_white"
        )
        
        return fig
    
    except Exception as e:
        # フォールバック: インデックスを使用
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=df.index,
            mode='lines',
            name='検出数推移'
        ))
        fig.update_layout(
            title="検出数推移",
            xaxis_title="レコード番号",
            yaxis_title="検出数",
            template="plotly_white"
        )
        return fig


def create_scatter_plot(df: pd.DataFrame, x_col: str, y_col: str, color_col: Optional[str] = None) -> go.Figure:
    """散布図を作成"""
    if not PLOT_SUPPORT:
        raise ImportError("可視化ライブラリが利用できません")
    
    if x_col not in df.columns or y_col not in df.columns:
        raise ValueError("指定された列が見つかりません")
    
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        title=f'{y_col} vs {x_col}',
        labels={x_col: x_col, y_col: y_col},
        opacity=0.7
    )
    
    fig.update_layout(
        template="plotly_white"
    )
    
    return fig


def create_waveform_plot(audio: np.ndarray, sample_rate: int, title: str = "音声波形") -> go.Figure:
    """音声波形プロットを作成"""
    if not PLOT_SUPPORT:
        raise ImportError("可視化ライブラリが利用できません")
    
    # 時間軸を作成
    time = np.arange(len(audio)) / sample_rate
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time,
        y=audio,
        mode='lines',
        name='波形',
        line=dict(width=1)
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="時間 (秒)",
        yaxis_title="振幅",
        template="plotly_white",
        height=300
    )
    
    return fig


def create_spectrogram_plot(db: np.ndarray, times: np.ndarray, freqs: np.ndarray, title: str = "スペクトログラム") -> go.Figure:
    """スペクトログラムプロットを作成"""
    if not PLOT_SUPPORT:
        raise ImportError("可視化ライブラリが利用できません")
    
    fig = go.Figure(data=go.Heatmap(
        z=db,
        x=times,
        y=freqs,
        colorscale='viridis',
        colorbar=dict(title="振幅 (dB)")
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="時間 (秒)",
        yaxis_title="周波数 (Hz)",
        template="plotly_white",
        height=400
    )
    
    return fig


def create_summary_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """サマリーメトリクスを計算"""
    if df.empty:
        return {}
    
    metrics = {
        "総検出数": len(df),
        "ユニーク種数": df.get('common_name', pd.Series()).nunique(),
        "ユニークファイル数": df.get('filename', pd.Series()).nunique(),
    }
    
    if 'confidence' in df.columns:
        metrics.update({
            "平均信頼度": round(df['confidence'].mean(), 3),
            "最高信頼度": round(df['confidence'].max(), 3),
            "最低信頼度": round(df['confidence'].min(), 3),
            "信頼度標準偏差": round(df['confidence'].std(), 3)
        })
    
    return metrics


def create_pie_chart(df: pd.DataFrame, column: str, top_n: int = 10, title: str = "") -> go.Figure:
    """円グラフを作成"""
    if not PLOT_SUPPORT:
        raise ImportError("可視化ライブラリが利用できません")
    
    if column not in df.columns:
        raise ValueError(f"{column}列が見つかりません")
    
    # 上位N件を取得、残りは「その他」にまとめる
    value_counts = df[column].value_counts()
    top_values = value_counts.head(top_n)
    
    if len(value_counts) > top_n:
        others_count = value_counts.iloc[top_n:].sum()
        top_values = pd.concat([top_values, pd.Series([others_count], index=['その他'])])
    
    fig = px.pie(
        values=top_values.values,
        names=top_values.index,
        title=title or f'{column}の分布'
    )
    
    fig.update_layout(
        template="plotly_white"
    )
    
    return fig
