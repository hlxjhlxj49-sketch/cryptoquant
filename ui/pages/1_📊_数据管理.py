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

# ===== 第二步：选择交易对 =====
st.markdown("---")
st.markdown("### 第二步：选择交易对")

# 初始化 session state
if "selected_symbols" not in st.session_state:
    st.session_state.selected_symbols = []
if "symbol_list_loaded" not in st.session_state:
    st.session_state.symbol_list_loaded = False
if "loaded_market_type" not in st.session_state:
    st.session_state.loaded_market_type = None
if "all_symbols_cache" not in st.session_state:
    st.session_state.all_symbols_cache = []

# ---- 4 个市场类型按钮 ----
st.markdown("**选择加密货币类型:**")
market_types = [
    ("spot", "📊 现货"),
    ("swap", "💹 U本位合约"),
    ("future", "📈 币本位合约"),
    ("option", "📋 期权"),
]

# 同步页面选择器与 session state
current_market = st.session_state.get("loaded_market_type", market_type)

cols_mt = st.columns(4)
for i, (mt_key, mt_label) in enumerate(market_types):
    with cols_mt[i]:
        is_active = (current_market == mt_key)
        btn_style = "primary" if is_active else "secondary"
        if st.button(
            mt_label,
            key=f"mt_btn_{mt_key}",
            use_container_width=True,
            type=btn_style,
        ):
            st.session_state.loaded_market_type = mt_key
            st.session_state.symbol_list_loaded = False
            st.session_state.all_symbols_cache = []
            st.rerun()

# 使用 session state 中记录的市场类型
active_market = st.session_state.loaded_market_type or market_type

# ---- 加载/刷新交易对列表 ----
col_s, col_l = st.columns([3, 1])
with col_s:
    search_filter = st.text_input(
        "🔍 搜索过滤",
        placeholder="输入 BTC/ETH/SOL 等关键词实时过滤...",
        key="symbol_search_filter",
    )
with col_l:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 加载交易所列表", use_container_width=True):
        st.session_state.symbol_list_loaded = False
        st.session_state.all_symbols_cache = []
        st.rerun()

# 加载交易对列表
if not st.session_state.symbol_list_loaded or not st.session_state.all_symbols_cache:
    proxies = None
    if proxy_http or proxy_https:
        proxies = {}
        if proxy_http:
            proxies["http"] = proxy_http
        if proxy_https:
            proxies["https"] = proxy_https

    with st.spinner(f"正在从 {exchange_name.upper()} 加载 {active_market} 交易对列表..."):
        try:
            fetcher = DataFetcher(
                exchange_name=exchange_name,
                market_type=active_market,
                proxies=proxies,
                timeout=15000,
            )
            all_by_type = fetcher.get_symbols_by_type(active_market)
            symbols_list = all_by_type.get(active_market, [])
            # 过滤 USDT 计价（如果适用）
            if not symbols_list:
                # 现货回退到 get_usdt_symbols
                if active_market == "spot":
                    symbols_list = fetcher.get_usdt_symbols()
                elif active_market == "swap":
                    symbols_list = fetcher.get_swap_symbols()

            st.session_state.all_symbols_cache = symbols_list
            st.session_state.symbol_list_loaded = True
        except Exception as e:
            st.error(f"❌ 加载交易对列表失败: {e}")
            st.info("💡 请检查网络连接或代理设置")
            st.session_state.all_symbols_cache = []

# ---- 过滤后的列表 ----
all_syms = st.session_state.all_symbols_cache
if search_filter.strip():
    filtered = [s for s in all_syms if search_filter.strip().upper() in s.upper()]
else:
    filtered = all_syms

st.caption(f"共 {len(all_syms)} 个交易对，当前显示 {len(filtered)} 个")

# ---- 复选框列表 ----
if filtered:
    # 用 columns 布局显示复选框
    n_cols = 3
    cols = st.columns(n_cols)
    for i, sym in enumerate(filtered[:150]):  # 最多显示 150 个
        with cols[i % n_cols]:
            checked = sym in st.session_state.selected_symbols
            cb = st.checkbox(
                sym, value=checked,
                key=f"chk_{active_market}_{i}",
                label_visibility="visible",
            )
            # 同步到 selected_symbols
            if cb and sym not in st.session_state.selected_symbols:
                st.session_state.selected_symbols.append(sym)
            elif not cb and sym in st.session_state.selected_symbols:
                st.session_state.selected_symbols.remove(sym)

    if len(filtered) > 150:
        st.caption(f"（仅显示前 150 个，请用搜索缩小范围）")

# ---- 已选标签 ----
if st.session_state.selected_symbols:
    st.markdown("---")
    st.markdown(f"**已选 {len(st.session_state.selected_symbols)} 个交易对:**")
    # 用标签显示已选
    tags_html = ""
    for sym in st.session_state.selected_symbols[:30]:
        tags_html += (
            f"<span style='display:inline-block; background:#E8E8E8; color:#1A1A1A; "
            f"padding:3px 8px; border-radius:4px; margin:2px; font-size:0.85rem;'>"
            f"{sym}</span> "
        )
    if len(st.session_state.selected_symbols) > 30:
        tags_html += f"<span style='color:#888888;'>... 等 {len(st.session_state.selected_symbols)} 个</span>"
    st.markdown(tags_html, unsafe_allow_html=True)

    if st.button("🗑️ 清空已选", use_container_width=False):
        st.session_state.selected_symbols = []
        st.rerun()

# 符号列表供后续步骤使用
symbols = st.session_state.selected_symbols

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
    bars_per_day = {"1m": 1440, "5m": 288, "15m": 96, "30m": 48, "1h": 24, "4h": 6, "1d": 1, "1w": 0.14}
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

type_labels = {"spot": "现货", "swap": "U本位合约", "future": "币本位合约", "option": "期权"}
active_type_label = type_labels.get(active_market, active_market)

if not symbols:
    st.warning(f"⚠️ 请先在第二步勾选要下载的{active_type_label}交易对")
else:
    col1, col2 = st.columns([1, 1])

    with col1:
        btn_label = f"📥 下载已选的 {len(symbols)} 个{active_type_label}数据"
        if st.button(btn_label, type="primary", use_container_width=True):
            proxies = None
            if proxy_http or proxy_https:
                proxies = {}
                if proxy_http:
                    proxies["http"] = proxy_http
                if proxy_https:
                    proxies["https"] = proxy_https

            manager = create_manager(
                exchange=exchange_name,
                market_type=active_market,
                proxies=proxies,
            )

            progress_bar = st.progress(0)
            status_text = st.empty()
            results = {}
            failed_symbols = []

            for i, symbol in enumerate(symbols):
                status_text.text(f"🔄 正在下载 {symbol} ({i+1}/{len(symbols)})...")
                try:
                    count = manager.sync_history(symbol, timeframe, days=days)
                    results[symbol] = count
                except Exception as e:
                    results[symbol] = 0
                    failed_symbols.append((symbol, str(e)))
                    st.error(f"❌ {symbol}: {e}")
                progress_bar.progress((i + 1) / len(symbols))

            progress_bar.progress(1.0)
            status_text.empty()

            success_count = sum(1 for v in results.values() if v > 0)
            if success_count > 0:
                st.markdown(f"""
                <div class="success-box">
                    <b>✅ 下载完成！</b><br>
                    成功: {success_count}/{len(symbols)} |
                    总数据: {sum(results.values()):,} 条
                </div>
                """, unsafe_allow_html=True)

                detail_df = pd.DataFrame([
                    {"交易对": s, "存入条数": c, "状态": "✅" if c > 0 else "❌ 失败"}
                    for s, c in results.items()
                ])
                st.dataframe(detail_df, use_container_width=True, hide_index=True)

            if failed_symbols:
                with st.expander(f"⚠️ {len(failed_symbols)} 个失败详情"):
                    for sym, err in failed_symbols:
                        st.caption(f"❌ {sym}: {err[:100]}")

    with col2:
        btn_all = f"⚡ 一键下载全部{active_type_label} ({len(all_syms)} 个)"
        if st.button(btn_all, use_container_width=True):
            proxies = None
            if proxy_http or proxy_https:
                proxies = {}
                if proxy_http:
                    proxies["http"] = proxy_http
                if proxy_https:
                    proxies["https"] = proxy_https

            manager = create_manager(
                exchange=exchange_name,
                market_type=active_market,
                proxies=proxies,
            )

            # 限制最多下载 50 个
            to_download = all_syms[:50]
            if len(all_syms) > 50:
                st.info(f"交易对较多，仅下载前 50 个。可在第二步勾选指定交易对精准下载。")

            progress_bar = st.progress(0)
            status_text = st.empty()
            results = {}

            for i, symbol in enumerate(to_download):
                status_text.text(f"🔄 {symbol} ({i+1}/{len(to_download)})...")
                try:
                    count = manager.sync_history(symbol, timeframe, days=days)
                    results[symbol] = count
                except Exception as e:
                    results[symbol] = 0
                progress_bar.progress((i + 1) / len(to_download))

            progress_bar.progress(1.0)
            status_text.empty()

            success_count = sum(1 for v in results.values() if v > 0)
            st.markdown(f"""
            <div class="success-box">
                <b>✅ 批量下载完成！</b><br>
                成功: {success_count} | 失败: {len(to_download) - success_count}<br>
                总数据: {sum(results.values()):,} 条
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
