"""
结果卡片组件
用于回测结果的可视化展示
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict


def show_metric_cards(metrics: Dict, columns: int = 4):
    """
    显示绩效指标卡片

    参数:
        metrics: 指标字典（来自 BacktestResult.to_dict()）
        columns: 每行显示的卡片数
    """
    # 提取关键指标
    key_metrics = {}

    # 解析字符串格式的值
    def parse_val(val_str):
        """从格式化字符串中提取数值"""
        if isinstance(val_str, (int, float)):
            return val_str
        if isinstance(val_str, str):
            import re
            # 提取数字
            nums = re.findall(r'[-+]?\d*\.?\d+', val_str)
            return float(nums[0]) if nums else 0.0
        return 0.0

    metric_items = [
        ("💰 总收益率", metrics.get("总收益率", "0%"), ""),
        ("📈 年化收益", metrics.get("年化收益率", "0%"), ""),
        ("📉 最大回撤", metrics.get("最大回撤", "0%"), ""),
        ("📊 夏普比率", metrics.get("夏普比率", "0"), ""),
        ("🎯 胜率", metrics.get("胜率", "0%"), ""),
        ("🔄 交易次数", metrics.get("交易次数", "0"), ""),
        ("⚖️ 盈亏比", metrics.get("盈亏比", "0"), ""),
        ("💸 总手续费", metrics.get("总手续费", "$0"), ""),
    ]

    cols = st.columns(columns)
    for i, (label, value, _) in enumerate(metric_items):
        col_idx = i % columns
        with cols[col_idx]:
            # 根据指标类型设置颜色
            v = parse_val(value)

            if "回撤" in label:
                color = "normal"  # 回撤越低越好
            elif "收益" in label:
                color = "normal" if v >= 0 else "inverse"
            elif "夏普" in label:
                color = "normal" if v >= 1 else "off"
            elif "胜率" in label:
                color = "normal" if v >= 40 else "off"
            else:
                color = "normal"

            st.metric(label=label, value=value)


def show_equity_chart(equity_df: pd.DataFrame, title: str = "权益曲线"):
    """
    显示权益曲线和回撤曲线

    参数:
        equity_df: 权益DataFrame（含 equity 列）
        title: 图表标题
    """
    if equity_df.empty:
        st.info("暂无权益数据")
        return

    # 计算回撤
    peak = equity_df["equity"].expanding().max()
    drawdown = (equity_df["equity"] - peak) / peak * 100

    # 创建子图
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=[title, "回撤曲线 (%)"],
    )

    # 权益曲线
    fig.add_trace(
        go.Scatter(
            x=equity_df.index,
            y=equity_df["equity"],
            mode="lines",
            name="权益",
            fill="tozeroy",
            fillcolor="rgba(0,184,148,0.1)",
            line=dict(color="#00B894", width=2),
        ),
        row=1, col=1,
    )

    # 初始资金参考线
    if not equity_df.empty:
        initial = equity_df["equity"].iloc[0]
        fig.add_hline(
            y=initial, line_dash="dash", line_color="#888888",
            opacity=0.5, row=1, col=1,
            annotation_text="初始资金",
        )

    # 回撤曲线
    fig.add_trace(
        go.Scatter(
            x=equity_df.index,
            y=drawdown,
            mode="lines",
            name="回撤",
            fill="tozeroy",
            fillcolor="rgba(225,112,85,0.3)",
            line=dict(color="#E17055", width=1.5),
        ),
        row=2, col=1,
    )

    # 最大回撤标注
    max_dd_idx = drawdown.idxmin()
    if pd.notna(max_dd_idx):
        max_dd_val = drawdown.min()
        fig.add_annotation(
            x=max_dd_idx,
            y=max_dd_val,
            text=f"最大回撤 {abs(max_dd_val):.2f}%",
            showarrow=True,
            arrowhead=1,
            font=dict(color="#E17055", size=11),
            row=2, col=1,
        )

    # 布局
    fig.update_layout(
        height=500,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FAFBFC",
        font=dict(color="#1A1A1A", size=11),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
            bgcolor="#F5F5F5",
            bordercolor="#E0E0E0",
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",
    )

    fig.update_xaxes(gridcolor="#E0E0E0", zerolinecolor="#CCCCCC")
    fig.update_yaxes(gridcolor="#E0E0E0", zerolinecolor="#CCCCCC")

    st.plotly_chart(fig, use_container_width=True)


def show_trade_details(trades_df: pd.DataFrame):
    """
    显示交易明细表

    参数:
        trades_df: 交易记录DataFrame
    """
    if trades_df.empty:
        st.info("暂无交易记录")
        return

    display_df = trades_df.copy()

    # 格式化显示
    if "time" in display_df.columns:
        display_df["time"] = display_df["time"].astype(str)

    for col in ["price", "cost", "revenue", "fee", "pnl", "equity"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"${x:,.2f}" if pd.notna(x) else "--"
            )

    # 重命名列
    rename_map = {
        "time": "时间", "side": "方向", "price": "价格",
        "size": "数量", "cost": "成本", "revenue": "收入",
        "fee": "手续费", "pnl": "盈亏", "equity": "权益",
    }
    display_df = display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns})

    st.dataframe(display_df, use_container_width=True, height=400, hide_index=True)
