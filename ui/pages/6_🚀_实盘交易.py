"""
实盘交易页面
连接真实交易所API，执行真实资金交易

⚠️ 此页面涉及真实资金操作！
"""

import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from execution.trader import LiveTrader
from execution.risk import RiskManager
from data.manager import create_manager

# ===== 页面初始化 =====
st.markdown("# 🚀 实盘交易")

# ===== ⚠️ 醒目风险警告 =====
st.markdown("""
<div style="background: #FFF3E0; border: 2px solid #FF9800; border-radius: 12px; padding: 20px; margin: 16px 0;">
    <h2 style="color: #E65100; margin: 0;">⚠️ 风险警告</h2>
    <p style="color: #1A1A1A; font-size: 1rem; margin-top: 12px;">
        • 实盘交易使用<b>真实资金</b>，可能导致<b>本金全部亏损</b><br>
        • 加密货币市场波动剧烈，价格可能在几分钟内大幅下跌<br>
        • 历史回测结果<b>不代表未来表现</b><br>
        • 请确认你已充分理解策略逻辑和风险<br>
        • 建议先用「模拟交易」充分验证策略<br>
        • <b>不要投入你无法承受亏损的资金</b>
    </p>
</div>
""", unsafe_allow_html=True)

# 确认复选框
confirmed = st.checkbox(
    "我已阅读并理解上述风险警告，自愿承担实盘交易的一切风险",
    value=False,
)

if not confirmed:
    st.warning("⚠️ 请先确认风险警告")
    st.stop()

st.markdown("---")

# ===== 第一步：API配置 =====
st.markdown("### 第一步：配置交易所API")

st.markdown("""
<div class="info-card">
    <h4>🔑 如何获取API Key</h4>
    <p>
    1. 登录你的交易所账户（币安/OKX/Bybit等）<br>
    2. 进入「API管理」页面<br>
    3. 创建新API Key，<b>只勾选交易权限</b>，<b>不要勾选提现权限</b><br>
    4. 妥善保管 Secret Key，不要泄露给任何人<br>
    5. <b>建议先使用测试网API进行验证</b>
    </p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    exchange_name = st.selectbox(
        "🏦 交易所",
        options=["binance", "okx", "bybit"],
        format_func=lambda x: {"binance": "币安 Binance", "okx": "OKX", "bybit": "Bybit"}[x],
        help="选择你的交易所",
    )

    test_mode = st.checkbox(
        "🧪 测试模式（沙盒环境）",
        value=True,
        help="强烈建议先使用测试网API验证一切正常后，再关闭此选项",
    )

with col2:
    api_key = st.text_input(
        "🔑 API Key",
        type="password",
        help="从交易所API管理页面获取",
    )
    api_secret = st.text_input(
        "🔐 Secret Key",
        type="password",
        help="从交易所API管理页面获取",
    )
    api_password = st.text_input(
        "🔒 密码（部分交易所需要）",
        type="password",
        help="OKX等交易所需要API密码，币安留空即可",
    )

# ===== 第二步：测试 API 连接 =====
st.markdown("---")
st.markdown("### 第二步：测试 API 连接")
st.markdown("验证 API Key 是否正确、网络是否连通、账户权限是否足够")

# 初始化 session state
if "api_tested" not in st.session_state:
    st.session_state.api_tested = False
if "test_error" not in st.session_state:
    st.session_state.test_error = ""
if "test_result" not in st.session_state:
    st.session_state.test_result = {}

col_test1, col_test2 = st.columns([2, 1])

with col_test1:
    test_btn = st.button(
        "🔍 测试 API 连接",
        type="primary",
        use_container_width=True,
        disabled=not (api_key and api_secret),
    )
    if not api_key or not api_secret:
        st.caption("⚠️ 请先在第一步填入 API Key 和 Secret Key")

with col_test2:
    if st.button("🔄 重置测试", use_container_width=True):
        st.session_state.api_tested = False
        st.session_state.test_error = ""
        st.session_state.test_result = {}
        st.session_state.connected = False
        st.session_state.live_trader = None
        st.rerun()

if test_btn:
    st.session_state.api_tested = False
    st.session_state.test_error = ""
    st.session_state.test_result = {}
    st.session_state.connected = False

    with st.spinner("正在验证 API 连接..."):
        try:
            # 创建交易器并尝试连接
            trader = LiveTrader(
                api_key=api_key,
                secret=api_secret,
                password=api_password,
                exchange=exchange_name,
                test_mode=test_mode,
            )

            if not trader.connect():
                st.session_state.test_error = "连接失败 — 请检查网络或代理设置，确保能访问交易所 API"
                st.error(f"❌ {st.session_state.test_error}")
            else:
                # 连接成功，获取账户信息
                balance = trader.get_balance("USDT")
                st.session_state.test_result = {
                    "exchange": exchange_name.upper(),
                    "test_mode": test_mode,
                    "balance": balance,
                }
                st.session_state.api_tested = True
                st.session_state.live_trader = trader

        except Exception as e:
            error_msg = str(e)
            if "BadSymbol" in error_msg or "does not have permission" in error_msg:
                st.session_state.test_error = f"API 权限不足 — 请确认已开启交易权限（不要开启提现权限）\n详情: {error_msg[:200]}"
            elif "Invalid API-key" in error_msg or "authentication" in error_msg.lower():
                st.session_state.test_error = f"API Key 无效 — 请检查 Key 和 Secret 是否正确\n详情: {error_msg[:200]}"
            elif "NetworkError" in type(e).__name__ or "timeout" in error_msg.lower():
                st.session_state.test_error = f"网络无法访问交易所 — 请检查代理是否已开启\n详情: {error_msg[:200]}"
            elif "ExchangeNotAvailable" in type(e).__name__:
                st.session_state.test_error = f"交易所暂时不可用 — 请稍后重试\n详情: {error_msg[:200]}"
            else:
                st.session_state.test_error = f"未知错误: {type(e).__name__}: {error_msg[:300]}"
            st.error(f"❌ {st.session_state.test_error}")

# 显示测试结果
if st.session_state.api_tested and st.session_state.test_result:
    res = st.session_state.test_result
    balance = res["balance"]
    st.markdown(f"""
    <div class="success-box">
        <b>✅ API 测试通过！</b><br>
        交易所: {res['exchange']} {'(测试模式)' if res['test_mode'] else '(实盘模式)'}<br>
        USDT余额: ${balance.get('total', 0):,.2f} (可用: ${balance.get('free', 0):,.2f})<br>
        <small>API 权限正常，可以执行交易操作</small>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 💰 账户余额")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("USDT 可用", f"${balance.get('free', 0):,.2f}")
    with col2:
        st.metric("USDT 冻结", f"${balance.get('used', 0):,.2f}")
    with col3:
        st.metric("USDT 总额", f"${balance.get('total', 0):,.2f}")

# 未通过测试时阻止后续操作
if not st.session_state.api_tested:
    st.info("👆 请先点击「🔍 测试 API 连接」验证 API 配置")
    st.stop()

st.session_state.connected = True

# ===== 第三步：交易参数 =====
st.markdown("---")
st.markdown("### 第三步：设置交易参数")

col1, col2, col3 = st.columns(3)

with col1:
    symbol = st.selectbox(
        "💱 交易对",
        options=["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"],
        index=0,
    )

    strategy_choice = st.selectbox(
        "🧠 策略",
        options=["双均线交叉", "RSI均值回归"],
    )

with col2:
    max_position = st.slider(
        "📊 最大仓位 (%)",
        1, 50, 10,
        help="单次交易最大占总资金百分比",
    )

    stop_loss = st.slider(
        "🛑 止损 (%)",
        0.5, 15.0, 3.0, 0.5,
        help="亏损达到此比例自动止损",
    )

with col3:
    take_profit = st.slider(
        "🎯 止盈 (%)",
        1.0, 30.0, 6.0, 0.5,
        help="盈利达到此比例自动止盈",
    )

    daily_limit = st.slider(
        "🚫 日亏损上限 (%)",
        2.0, 15.0, 5.0, 0.5,
        help="单日亏损达上限后停止交易",
    )

# ===== 第四步：交易操作 =====
st.markdown("---")
st.markdown("### 第四步：交易操作")

if st.session_state.get("live_trader"):
    trader = st.session_state.live_trader

    col1, col2, col3 = st.columns(3)

    with col1:
        order_size = st.number_input(
            "📊 交易数量",
            min_value=0.0001,
            value=0.001,
            step=0.001,
            format="%.4f",
            help="买入/卖出的数量（币本位）",
        )

    with col2:
        if st.button("🟢 市价买入", type="primary", use_container_width=True):
            if order_size > 0:
                order = trader.market_buy(symbol, order_size)
                if order:
                    st.success(f"✅ 买入成功: {symbol} {order_size}")
                else:
                    st.error("❌ 买入失败，请检查余额和交易权限")
            else:
                st.warning("请输入有效的交易数量")

    with col3:
        if st.button("🔴 市价卖出", use_container_width=True):
            if order_size > 0:
                order = trader.market_sell(symbol, order_size)
                if order:
                    st.success(f"✅ 卖出成功: {symbol} {order_size}")
                else:
                    st.error("❌ 卖出失败，可能持仓不足或交易权限受限")
            else:
                st.warning("请输入有效的交易数量")

    # 行情信息
    st.markdown("---")
    st.markdown("#### 📈 当前行情")
    ticker = trader.get_ticker(symbol)
    if ticker:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("最新价", f"${ticker.get('last', 0):,.2f}")
        with col2:
            change = ticker.get("percentage", 0) or 0
            st.metric("24h涨跌", f"{change:+.2f}%")
        with col3:
            st.metric("24h最高", f"${ticker.get('high', 0):,.2f}")
        with col4:
            st.metric("24h最低", f"${ticker.get('low', 0):,.2f}")

    # 断开按钮
    st.markdown("---")
    if st.button("🔌 断开连接", use_container_width=True):
        trader.disconnect()
        st.session_state.connected = False
        st.session_state.api_tested = False
        st.session_state.live_trader = None
        st.session_state.test_result = {}
        st.rerun()

else:
    st.info("👆 请先通过第二步的 API 连接测试")
