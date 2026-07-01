"""
数据管理页面
支持自定义输入交易对（现货/合约/期权）+ 多交易所下载
"""

import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data.fetcher import DataFetcher
from data.manager import create_manager
from utils.helpers import get_proxy_config

# ===== 页面初始化 =====
st.markdown("# 📊 数据管理")
st.markdown("输入交易对名称，一键下载历史K线数据到本地数据库")

# 从配置加载默认代理
_default_proxy = get_proxy_config()
_default_http = _default_proxy.get("http", "")
_default_https = _default_proxy.get("https", "")

# ===== 第一步：选择数据源 =====
st.markdown("---")
st.markdown("### 第一步：选择交易所和配置")

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    exchange_name = st.selectbox(
        "🏦 交易所",
        options=list(DataFetcher.POPULAR_EXCHANGES.keys()),
        format_func=lambda x: DataFetcher.POPULAR_EXCHANGES[x],
        index=0,
        help="选择数据来源交易所",
    )

with col2:
    market_type = st.selectbox(
        "📂 市场类型",
        options=list(DataFetcher.MARKET_TYPES.keys()),
        format_func=lambda x: f"{DataFetcher.MARKET_TYPES[x]} ({x})",
        index=0,
        help="""
        - 现货(spot)：BTC/USDT
        - 永续合约(swap)：BTC/USDT:USDT
        - 交割合约(future)：BTC/USDT-241229
        - 期权(option)：BTC/USDT-241229-50000-C
        """,
    )

with col3:
    timeframe = st.selectbox(
        "⏱️ K线周期",
        options=list(DataFetcher.TIMEFRAMES.keys()),
        format_func=lambda x: f"{x} ({DataFetcher.TIMEFRAMES[x]})",
        index=4,
        help="K线的时间周期",
    )

# ===== 代理设置（可折叠） =====
with st.expander("🔧 高级设置（代理/网络）", expanded=False):
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        proxy_http = st.text_input(
            "HTTP 代理",
            value=_default_http,
            placeholder="如 http://127.0.0.1:7897",
            help="如果无法直接访问交易所，请配置代理地址。Clash Verge 默认 7897 端口",
        )

    with col2:
        proxy_https = st.text_input(
            "HTTPS 代理",
            value=_default_https,
            placeholder="如 http://127.0.0.1:7897",
            help="通常与HTTP代理相同。Clash Verge 默认 7897 端口",
        )

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔌 测试连接", use_container_width=True):
            proxies = None
            if proxy_http or proxy_https:
                proxies = {}
                if proxy_http:
                    proxies["http"] = proxy_http
                if proxy_https:
                    proxies["https"] = proxy_https

            fetcher = DataFetcher(
                exchange_name=exchange_name,
                market_type=market_type,
                proxies=proxies,
                timeout=15000,
            )
            success, msg = fetcher.test_connection()
            if success:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")

    st.caption("💡 常见代理地址：Clash: http://127.0.0.1:7890 | V2Ray: http://127.0.0.1:10809")

# ===== 第二步：输入交易对 =====
st.markdown("---")
st.markdown("### 第二步：输入交易对名称")

st.markdown("""
<div style="
    background: #F0F0F0;
    padding: 16px 20px;
    border-radius: 8px;
    margin: 8px 0;
    border: 1px solid #E0E0E0;
    color: #1A1A1A;
    line-height: 2.2;
">
<strong>📝 交易对命名格式参考：</strong><br>
<strong>现货：</strong><code>BTC/USDT</code>&ensp;<code>ETH/USDT</code>&ensp;<code>SOL/USDT</code><br>
<strong>永续合约：</strong><code>BTC/USDT:USDT</code>&ensp;<code>ETH/USDT:USDT</code>&ensp;（币安）<br>
&emsp;&emsp;&emsp;&emsp;<code>BTC-USDT-SWAP</code>&ensp;<code>ETH-USDT-SWAP</code>&ensp;（OKX）<br>
<strong>期权：</strong><code>BTC/USDT-241229-50000-C</code>&ensp;（看涨）&ensp;<code>BTC/USDT-241229-50000-P</code>&ensp;（看跌）
</div>

<style>
    /* 容器内的 code 标签统一样式 */
    .stMarkdown code {
        background: #E0E0E0;
        color: #1A1A1A;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# 自定义输入
st.markdown("#### ✏️ 自定义输入交易对")

col1, col2 = st.columns([3, 1])

with col1:
    custom_input = st.text_input(
        "输入交易对名称（多个用逗号或空格分隔）",
        value="BTC/USDT",
        placeholder="例如：BTC/USDT, ETH/USDT, BTC/USDT:USDT, SOL/USDT",
        help="直接输入交易对名称。现货如 BTC/USDT，合约如 BTC/USDT:USDT",
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    quick_fill = st.selectbox(
        "⚡ 快速填充",
        options=["---", "主流现货", "主流合约", "最近输入"],
        help="快速填充常用交易对",
    )

    # 解析用户输入的符号
    if quick_fill == "主流现货":
        st.session_state.custom_input = "BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, XRP/USDT"
        st.rerun()
    elif quick_fill == "主流合约":
        st.session_state.custom_input = "BTC/USDT:USDT, ETH/USDT:USDT, BNB/USDT:USDT, SOL/USDT:USDT"
        st.rerun()

# 解析输入
raw_input = custom_input.strip()
if raw_input:
    # 支持逗号、空格、中文逗号分隔
    import re
    symbols = re.split(r'[,，\s]+', raw_input)
    symbols = [s.strip() for s in symbols if s.strip()]

    if symbols:
        st.markdown(f"**📋 已识别 {len(symbols)} 个交易对：**")
        # 显示为标签
        cols = st.columns(min(len(symbols), 5))
        for i, sym in enumerate(symbols):
            with cols[i % 5]:
                st.markdown(f"<code style='background:#E8E8E8; color:#1A1A1A; padding:4px 8px; border-radius:4px;'>{sym}</code>",
                            unsafe_allow_html=True)

st.markdown("---")

# 搜索功能
st.markdown("#### 🔍 搜索交易所交易对")

col1, col2 = st.columns([3, 1])

with col1:
    search_keyword = st.text_input(
        "搜索关键词",
        value="",
        placeholder="如 BTC, ETH, SOL ...",
        help="输入币种名称搜索该交易所支持的完整交易对名称",
        key="search_input",
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    search_btn = st.button("🔍 搜索", use_container_width=True)

if search_btn and search_keyword.strip():
    proxies = None
    if proxy_http or proxy_https:
        proxies = {}
        if proxy_http:
            proxies["http"] = proxy_http
        if proxy_https:
            proxies["https"] = proxy_https

    with st.spinner(f"正在搜索 {search_keyword}..."):
        try:
            fetcher = DataFetcher(
                exchange_name=exchange_name,
                market_type=market_type,
                proxies=proxies,
            )
            results = fetcher.search_symbols(search_keyword.strip())

            if results:
                st.success(f"找到 {len(results)} 个匹配交易对")
                # 分列显示
                cols = st.columns(3)
                for i, sym in enumerate(results[:60]):  # 最多显示60个
                    with cols[i % 3]:
                        if st.button(sym, key=f"sym_{i}", use_container_width=True):
                            # 点击添加到输入框
                            current = custom_input.strip()
                            if current:
                                st.session_state[f"custom_input_{id(st.session_state)}"] = current + ", " + sym
                            else:
                                st.session_state[f"custom_input_{id(st.session_state)}"] = sym
                            st.rerun()
            else:
                st.warning(f"未找到匹配 '{search_keyword}' 的交易对")
        except Exception as e:
            st.error(f"搜索失败: {e}")

# ===== 第三步：设置下载参数 =====
st.markdown("---")
st.markdown("### 第三步：设置下载范围")

col1, col2, col3 = st.columns(3)

with col1:
    days = st.number_input(
        "📅 回溯天数",
        min_value=1,
        max_value=365,
        value=30,
        step=10,
        help="从今天往前推多少天的数据",
    )

with col2:
    kline_limit = st.number_input(
        "📊 单次获取条数",
        min_value=100,
        max_value=1500,
        value=500,
        step=100,
        help="每次API请求获取的K线数（不同交易所有不同上限）",
    )

with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    bars_per_day = {"1m": 1440, "5m": 288, "15m": 96, "30m": 48, "1h": 24, "4h": 6, "1d": 1}
    est = days * bars_per_day.get(timeframe, 24)
    st.markdown(f"""
    <div style="background: #F5F5F5; padding: 12px; border-radius: 8px; margin-top: 8px; border: 1px solid #E8E8E8;">
        <p style="color: #555555; font-size: 0.9rem; margin: 0;">
            📊 预计数据量: <b style="color: #1A1A1A;">~{est:,}</b> 条/币种
        </p>
    </div>
    """, unsafe_allow_html=True)

# ===== 第四步：执行下载 =====
st.markdown("---")
st.markdown("### 第四步：执行下载")

if not symbols:
    st.warning("⚠️ 请先在第二步输入交易对名称")
else:
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(f"📥 下载 {len(symbols)} 个交易对数据", type="primary", use_container_width=True):
            # 构建代理
            proxies = None
            if proxy_http or proxy_https:
                proxies = {}
                if proxy_http:
                    proxies["http"] = proxy_http
                if proxy_https:
                    proxies["https"] = proxy_https

            # 创建管理器
            manager = create_manager(
                exchange=exchange_name,
                market_type=market_type,
                proxies=proxies,
            )

            progress_bar = st.progress(0)
            status_text = st.empty()
            results = {}

            for i, symbol in enumerate(symbols):
                status_text.text(f"🔄 正在下载 {symbol} ({i+1}/{len(symbols)})...")

                try:
                    count = manager.sync_history(symbol, timeframe, days=days)
                    results[symbol] = count
                except Exception as e:
                    results[symbol] = 0
                    st.error(f"❌ {symbol}: {e}")

                progress_bar.progress((i + 1) / len(symbols))

            progress_bar.progress(1.0)
            status_text.empty()

            # 结果
            success_count = sum(1 for v in results.values() if v > 0)
            if success_count > 0:
                st.markdown(f"""
                <div class="success-box">
                    <b>✅ 下载完成！</b><br>
                    成功: {success_count}/{len(symbols)} |
                    总数据: {sum(results.values()):,} 条<br>
                    现在可以前往 <b>「行情看板」</b> 查看K线图
                </div>
                """, unsafe_allow_html=True)

                detail_df = pd.DataFrame([
                    {"交易对": s, "存入条数": c, "状态": "✅" if c > 0 else "❌ 失败"}
                    for s, c in results.items()
                ])
                st.dataframe(detail_df, use_container_width=True, hide_index=True)

    with col2:
        if st.button("⚡ 一键下载主流现货 Top20", use_container_width=True):
            proxies = None
            if proxy_http or proxy_https:
                proxies = {}
                if proxy_http:
                    proxies["http"] = proxy_http
                if proxy_https:
                    proxies["https"] = proxy_https

            manager = create_manager(
                exchange=exchange_name,
                market_type="spot",
                proxies=proxies,
            )

            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(current, total):
                progress_bar.progress(current / total)
                status_text.text(f"下载进度: {current}/{total}")

            with st.spinner("正在批量下载..."):
                result = manager.download_top_coins(timeframe, days=days, top_n=20,
                                                     progress_callback=update_progress)

            progress_bar.progress(1.0)
            status_text.empty()

            st.markdown(f"""
            <div class="success-box">
                <b>✅ 批量下载完成！</b><br>
                成功: {result['success']} | 失败: {result['failed']}
            </div>
            """, unsafe_allow_html=True)

# ===== 数据库概览 =====
st.markdown("---")
st.markdown("### 📊 本地数据库概览")

if st.button("🔄 刷新数据概览", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

try:
    from data.storage import DataStorage
    storage = DataStorage("E:/crypto_quant/data/market.db")
    summary_df = storage.get_data_summary()

    if not summary_df.empty:
        total_bars = summary_df["数据条数"].sum()
        total_tables = len(summary_df)

        col1, col2, col3 = st.columns(3)
        col1.metric("📦 数据表数量", total_tables)
        col2.metric("📊 总数据条数", f"{total_bars:,}")
        col3.metric("💾 交易所", exchange_name.upper())

        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.info("📭 数据库为空，请先下载数据")
except Exception as e:
    st.warning(f"⚠️ 无法获取数据库概览: {e}")
