"""
行情看板页面
实时查看K线图、均线（MA）、成交量（Volume）、KDJ 指标
"""

import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime

# 确保模块导入
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data.manager import create_manager
from ui.components.kline_chart import create_kline_chart

# ===== 页面初始化 =====
st.markdown("# 📈 行情看板")
st.markdown("实时K线图 · 均线系统 · 成交量 · KDJ指标")

if "manager" not in st.session_state:
    st.session_state.manager = create_manager()

manager = st.session_state.manager

# ===== 第一步：选择币种和参数 =====
st.markdown("---")
st.markdown("### 第一步：选择币种和K线周期")

col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    # 输入模式切换
    input_mode = st.radio(
        "选择方式",
        options=["📋 常用交易对", "✏️ 自定义输入"],
        horizontal=True,
    )

    if input_mode == "📋 常用交易对":
        popular_symbols = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
            "BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT",
        ]
        symbol = st.selectbox(
            "💱 交易对",
            options=popular_symbols,
            index=0,
            help="选择要查看的交易对（含现货和合约）",
        )
    else:
        symbol = st.text_input(
            "✏️ 输入交易对名称",
            value="BTC/USDT",
            placeholder="现货: BTC/USDT | 合约: BTC/USDT:USDT | OKX合约: BTC-USDT-SWAP",
            help="直接输入交易对名称，支持现货、永续合约、交割合约、期权",
        )

with col2:
    timeframe = st.selectbox(
        "⏱️ K线周期",
        options=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
        index=4,
        help="K线的时间周期",
    )

with col3:
    data_range = st.selectbox(
        "📅 数据范围",
        options=["1天", "3天", "7天", "30天", "90天"],
        index=3,
        help="查看多长时间的数据",
    )
    # 转换为limit
    range_to_limit = {"1天": 100, "3天": 300, "7天": 500, "30天": 500, "90天": 1000}
    limit = range_to_limit[data_range]

with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    auto_refresh = st.checkbox(
        "🔄 自动刷新",
        value=False,
        help="开启后每30秒自动刷新数据",
    )

# ===== 第二步：选择显示的指标 =====
st.markdown("---")
st.markdown("### 第二步：选择显示指标")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    show_ma = st.checkbox("📊 均线 MA", value=True, help="显示MA5/MA10/MA20/MA60均线")
with col2:
    show_volume = st.checkbox("📊 成交量 Volume", value=True, help="显示成交量柱状图")
with col3:
    show_kdj = st.checkbox("📊 KDJ 指标", value=True, help="显示KDJ（K/D/J值）")
with col4:
    show_bb = st.checkbox("📊 布林带 BOLL", value=False, help="显示布林带（上轨/中轨/下轨）")
with col5:
    show_ema = st.checkbox("📊 EMA 均线", value=False, help="显示指数移动平均线")

# 均线周期选择
if show_ma:
    ma_periods = st.multiselect(
        "均线周期选择",
        options=[5, 10, 20, 60, 120, 250],
        default=[5, 10, 20, 60],
        help="选择要显示的均线周期",
    )
else:
    ma_periods = []

# ===== 第三步：加载并显示图表 =====
st.markdown("---")
st.markdown("### 第三步：查看行情")

if st.button("📈 加载行情数据", type="primary", use_container_width=True):
    with st.spinner(f"正在加载 {symbol} {timeframe} 数据..."):
        df = manager.get_data(symbol, timeframe, limit=limit, auto_sync=True)

    if df.empty:
        st.error(f"❌ 无法获取 {symbol} 的数据，请先到「数据管理」页面下载数据")
    else:
        # 显示最新行情概览
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        price_change = latest["close"] - prev["close"]
        price_change_pct = (price_change / prev["close"]) * 100

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "💰 最新价格",
                f"${latest['close']:,.2f}",
                delta=f"{price_change:+,.2f} ({price_change_pct:+.2f}%)",
            )
        with col2:
            st.metric("📈 24h最高", f"${latest['high']:,.2f}")
        with col3:
            st.metric("📉 24h最低", f"${latest['low']:,.2f}")
        with col4:
            st.metric("📊 成交量", f"{latest['volume']:,.0f}")
        with col5:
            st.metric("📅 数据条数", f"{len(df):,}")

        # 显示K线图
        st.markdown("---")
        chart_title = f"{symbol} · {timeframe} · {data_range}"

        fig = create_kline_chart(
            df,
            title=chart_title,
            show_volume=show_volume,
            show_kdj=show_kdj,
            show_ma=show_ma and len(ma_periods) > 0,
            ma_periods=ma_periods,
            height=700,
        )

        st.plotly_chart(fig, use_container_width=True, config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
        })

        # ===== 数据表格 =====
        st.markdown("---")
        st.markdown("### 📋 最近K线数据")

        with st.expander("点击展开数据表格"):
            display_df = df.tail(50).copy()
            display_df.index = display_df.index.strftime("%Y-%m-%d %H:%M")
            display_df = display_df.rename(columns={
                "open": "开盘价", "high": "最高价", "low": "最低价",
                "close": "收盘价", "volume": "成交量",
            })
            st.dataframe(
                display_df.sort_index(ascending=False),
                use_container_width=True,
                height=400,
            )
elif auto_refresh:
    # 自动刷新模式
    import time
    placeholder = st.empty()

    while auto_refresh:
        df = manager.get_data(symbol, timeframe, limit=limit, auto_sync=True)

        if not df.empty:
            with placeholder.container():
                latest = df.iloc[-1]
                cols = st.columns(5)
                cols[0].metric("💰 最新价格", f"${latest['close']:,.2f}")
                cols[1].metric("📈 最高", f"${latest['high']:,.2f}")
                cols[2].metric("📉 最低", f"${latest['low']:,.2f}")
                cols[3].metric("📊 成交量", f"{latest['volume']:,.0f}")
                cols[4].metric("⏰ 更新时间", datetime.now().strftime("%H:%M:%S"))

                fig = create_kline_chart(
                    df,
                    title=f"{symbol} · {timeframe} (自动刷新中...)",
                    show_volume=show_volume,
                    show_kdj=show_kdj,
                    show_ma=show_ma and len(ma_periods) > 0,
                    ma_periods=ma_periods,
                    height=600,
                )
                st.plotly_chart(fig, use_container_width=True)

        time.sleep(30)
        st.rerun()
else:
    # 初始状态提示
    st.info("👆 请点击上方「加载行情数据」按钮查看K线图")
