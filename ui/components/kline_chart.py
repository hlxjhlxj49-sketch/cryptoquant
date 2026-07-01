"""
交互式K线图组件
基于 Plotly 实现，支持缩放、拖拽、叠加指标

默认显示：
  主图：K线 + MA均线（MA5/MA10/MA20/MA60）
  副图1：成交量柱状图（Volume）
  副图2：KDJ 指标（K/D/J 三条线）
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Optional, List, Dict


def calculate_ma(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
    """
    计算移动平均线（MA）

    参数:
        df: K线DataFrame（需包含 close 列）
        periods: 均线周期列表，默认 [5, 10, 20, 60]

    返回:
        添加了 MA 列的 DataFrame
    """
    if periods is None:
        periods = [5, 10, 20, 60]

    df = df.copy()
    for p in periods:
        df[f"MA{p}"] = df["close"].rolling(window=p).mean()
    return df


def calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
    """
    计算 KDJ 指标

    参数:
        df: K线DataFrame（需包含 high, low, close 列）
        n: RSV周期（默认9）
        m1: K值平滑周期（默认3）
        m2: D值平滑周期（默认3）

    返回:
        添加了 K, D, J 列的 DataFrame
    """
    df = df.copy()

    # 计算N日内最高价和最低价
    low_list = df["low"].rolling(window=n, min_periods=1).min()
    high_list = df["high"].rolling(window=n, min_periods=1).max()

    # 计算RSV（未成熟随机值）
    rsv = (df["close"] - low_list) / (high_list - low_list) * 100
    rsv = rsv.fillna(50)  # 处理除零情况

    # 计算K、D、J值
    k_values = rsv.ewm(com=m1 - 1, adjust=False).mean()
    d_values = k_values.ewm(com=m2 - 1, adjust=False).mean()
    j_values = 3 * k_values - 2 * d_values

    df["K"] = k_values
    df["D"] = d_values
    df["J"] = j_values

    return df


def calculate_volume_ma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    计算成交量均线

    参数:
        df: K线DataFrame（需包含 volume 列）
        period: 均线周期

    返回:
        添加了 Volume_MA 列的 DataFrame
    """
    df = df.copy()
    df["Volume_MA"] = df["volume"].rolling(window=period).mean()
    return df


def create_kline_chart(
    df: pd.DataFrame,
    title: str = "K线图",
    show_volume: bool = True,
    show_kdj: bool = True,
    show_ma: bool = True,
    ma_periods: List[int] = None,
    height: int = 700,
) -> go.Figure:
    """
    创建交互式K线图

    参数:
        df: K线DataFrame（需包含 open, high, low, close, volume 列）
        title: 图表标题
        show_volume: 是否显示成交量副图
        show_kdj: 是否显示KDJ副图
        show_ma: 是否显示均线
        ma_periods: 均线周期列表
        height: 图表总高度（像素）

    返回:
        Plotly Figure 对象
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="暂无数据，请先下载",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="#888888"),
        )
        fig.update_layout(
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FAFBFC",
            font=dict(color="#1A1A1A"),
        )
        return fig

    if ma_periods is None:
        ma_periods = [5, 10, 20, 60]

    # 预处理：计算所有指标
    df = df.copy()
    if show_ma:
        df = calculate_ma(df, ma_periods)
    if show_kdj:
        df = calculate_kdj(df)
    if show_volume:
        df = calculate_volume_ma(df)

    # 确定子图布局
    rows = 1
    heights = [1.0]
    specs = [[{"secondary_y": False}]]

    if show_volume:
        rows += 1
        heights.append(0.25)
        specs.append([{"secondary_y": False}])

    if show_kdj:
        rows += 1
        heights.append(0.25)
        specs.append([{"secondary_y": False}])

    # 创建子图
    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=heights,
        specs=specs,
        subplot_titles=([title] if rows == 1 else [title] + [""] * (rows - 1)),
    )

    # ===== 主图：K线 + 均线 =====
    # K线（涨绿跌红）
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="K线",
            increasing=dict(line=dict(color="#00B894"), fillcolor="#00B894"),
            decreasing=dict(line=dict(color="#E17055"), fillcolor="#E17055"),
            showlegend=True,
        ),
        row=1, col=1,
    )

    # MA均线
    if show_ma:
        ma_colors = {5: "#FFD700", 10: "#FF6B6B", 20: "#4ECDC4", 60: "#A29BFE"}
        for p in ma_periods:
            col_name = f"MA{p}"
            if col_name in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df[col_name],
                        mode="lines",
                        name=f"MA{p}",
                        line=dict(color=ma_colors.get(p, "#FFFFFF"), width=1.2),
                        showlegend=True,
                    ),
                    row=1, col=1,
                )

    # ===== 副图1：成交量 =====
    current_row = 1
    if show_volume:
        current_row += 1
        # 根据涨跌着色
        colors = [
            "#00B894" if close >= open_ else "#E17055"
            for close, open_ in zip(df["close"], df["open"])
        ]

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["volume"],
                name="成交量",
                marker=dict(color=colors, opacity=0.6),
                showlegend=True,
            ),
            row=current_row, col=1,
        )

        # 成交量均线
        if "Volume_MA" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["Volume_MA"],
                    mode="lines",
                    name="成交量MA20",
                    line=dict(color="#F0A500", width=1),
                    showlegend=True,
                ),
                row=current_row, col=1,
            )

    # ===== 副图2：KDJ =====
    if show_kdj:
        current_row += 1
        # K线
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["K"],
                mode="lines", name="K值",
                line=dict(color="#FFD700", width=1.2),
                showlegend=True,
            ),
            row=current_row, col=1,
        )
        # D线
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["D"],
                mode="lines", name="D值",
                line=dict(color="#FF6B6B", width=1.2),
                showlegend=True,
            ),
            row=current_row, col=1,
        )
        # J线
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["J"],
                mode="lines", name="J值",
                line=dict(color="#4ECDC4", width=0.8, dash="dot"),
                showlegend=True,
            ),
            row=current_row, col=1,
        )

        # 超买超卖参考线
        for level, color, label in [(80, "#E17055", "超买80"), (20, "#00B894", "超卖20")]:
            fig.add_hline(
                y=level, line_dash="dash", line_color=color,
                opacity=0.3, row=current_row, col=1,
            )

    # ===== 图表布局 =====
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=18, color="#2C3E50"),
        ),
        height=height,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FAFBFC",
        font=dict(color="#1A1A1A", size=11),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="#F5F5F5",
            bordercolor="#E0E0E0",
            font=dict(size=10, color="#1A1A1A"),
        ),
        hovermode="x unified",
        margin=dict(l=10, r=10, t=50, b=10),
        dragmode="pan",
    )

    # X轴配置
    fig.update_xaxes(
        gridcolor="#E0E0E0",
        zerolinecolor="#CCCCCC",
        showgrid=True,
    )

    # Y轴配置
    fig.update_yaxes(
        gridcolor="#E0E0E0",
        zerolinecolor="#CCCCCC",
        showgrid=True,
        side="right",
    )

    # KDJ子图的Y轴范围
    if show_kdj:
        fig.update_yaxes(range=[-5, 105], row=current_row, col=1)

    # 配置交互按钮
    config = {
        "scrollZoom": True,
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "displaylogo": False,
    }

    return fig


def create_indicator_chart(
    df: pd.DataFrame,
    indicator_name: str,
    indicator_values: pd.Series,
    overlay: bool = False,
    height: int = 250,
) -> go.Figure:
    """
    创建单独的指标图表

    参数:
        df: K线DataFrame
        indicator_name: 指标名称
        indicator_values: 指标值Series
        overlay: 是否叠加到主图（False则独立副图）
        height: 图表高度

    返回:
        Plotly Figure 对象
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=indicator_values,
            mode="lines",
            name=indicator_name,
            line=dict(color="#F0A500", width=1.5),
        )
    )

    fig.update_layout(
        height=height,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FAFBFC",
        font=dict(color="#1A1A1A"),
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified",
    )

    fig.update_xaxes(gridcolor="#E0E0E0", zerolinecolor="#CCCCCC")
    fig.update_yaxes(gridcolor="#E0E0E0", zerolinecolor="#CCCCCC", side="right")

    return fig
