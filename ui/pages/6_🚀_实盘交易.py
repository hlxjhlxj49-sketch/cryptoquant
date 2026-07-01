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

# ===== 第二步：交易参数 =====
st.markdown("---")
st.markdown("### 第二步：设置交易参数")

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

# ===== 第三步：连接交易所 =====
st.markdown("---")
st.markdown("### 第三步：连接交易所")

if st.button("🔌 连接交易所", type="primary", use_container_width=True):
    if not api_key or not api_secret:
        st.error("❌ 请输入API Key和Secret Key")
    else:
        with st.spinner("正在连接交易所..."):
            trader = LiveTrader(
                api_key=api_key,
                secret=api_secret,
                password=api_password,
                exchange=exchange_name,
                test_mode=test_mode,
            )

            if trader.connect():
                st.session_state.live_trader = trader
                st.session_state.connected = True

                # 获取余额
                balance = trader.get_balance("USDT")
                st.markdown(f"""
                <div class="success-box">
                    <b>✅ 连接成功！</b><br>
                    交易所: {exchange_name.upper()} {'(测试模式)' if test_mode else '(实盘模式)'}<br>
                    USDT余额: ${balance['total']:,.2f} (可用: ${balance['free']:,.2f})
                </div>
                """, unsafe_allow_html=True)

                # 显示余额详情
                st.markdown("#### 💰 账户余额")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("USDT 可用", f"${balance['free']:,.2f}")
                with col2:
                    st.metric("USDT 冻结", f"${balance['used']:,.2f}")
                with col3:
                    st.metric("USDT 总额", f"${balance['total']:,.2f}")
            else:
                st.error(f"❌ 连接失败，请检查API Key和网络")

# ===== 第四步：交易操作 =====
if st.session_state.get("connected") and st.session_state.get("live_trader"):
    st.markdown("---")
    st.markdown("### 第四步：交易操作")

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
                    st.error("❌ 买入失败")
            else:
                st.warning("请输入有效的交易数量")

    with col3:
        if st.button("🔴 市价卖出", use_container_width=True):
            if order_size > 0:
                order = trader.market_sell(symbol, order_size)
                if order:
                    st.success(f"✅ 卖出成功: {symbol} {order_size}")
                else:
                    st.error("❌ 卖出失败，可能持仓不足")
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
        st.session_state.live_trader = None
        st.rerun()

else:
    st.info("👆 请先配置API Key并点击「连接交易所」")
