"""
模拟交易页面
用虚拟资金+实时行情模拟真实交易
"""

import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data.manager import create_manager
from execution.paper_trader import PaperTrader
from execution.risk import RiskManager
from strategy.examples.ma_cross import MACrossStrategy
from strategy.examples.rsi_strategy import RSIStrategy


# ===== 页面初始化 =====
st.markdown("# 💹 模拟交易")
st.markdown("零风险 · 用虚拟资金在真实行情中演练")

if "manager" not in st.session_state:
    st.session_state.manager = create_manager()
if "paper_trader" not in st.session_state:
    st.session_state.paper_trader = None
if "paper_running" not in st.session_state:
    st.session_state.paper_running = False

manager = st.session_state.manager

# ===== 第一步：配置模拟账户 =====
st.markdown("---")
st.markdown("### 第一步：配置模拟账户")

col1, col2, col3 = st.columns(3)

with col1:
    initial_capital = st.number_input(
        "💰 初始资金 (USDT)",
        min_value=100,
        max_value=1000000,
        value=10000,
        step=1000,
        help="模拟账户的起始资金",
    )

with col2:
    selected_strategy_name = st.selectbox(
        "🧠 选择策略",
        options=["双均线交叉", "RSI均值回归", "网格交易"],
    )

with col3:
    symbol = st.selectbox(
        "💱 交易对",
        options=["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"],
        index=0,
    )

# 风险管理设置
st.markdown("**🛡️ 风险参数**")
col1, col2, col3, col4 = st.columns(4)

with col1:
    max_position = st.slider("最大仓位 (%):", 1, 100, 20, help="单次交易占总资金的最大比例")
with col2:
    stop_loss = st.slider("止损 (%):", 0.5, 20.0, 3.0, step=0.5, help="亏损超过此比例自动卖出")
with col3:
    take_profit = st.slider("止盈 (%):", 1.0, 50.0, 6.0, step=0.5, help="盈利超过此比例自动止盈")
with col4:
    daily_limit = st.slider("日亏损上限 (%):", 1.0, 20.0, 5.0, step=0.5, help="单日亏损达到上限停止交易")

# ===== 第二步：启动/停止 =====
st.markdown("---")
st.markdown("### 第二步：控制模拟交易")

col1, col2 = st.columns(2)

with col1:
    start_btn = st.button(
        "▶️ 启动模拟交易",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.paper_running,
    )

with col2:
    stop_btn = st.button(
        "⏹️ 停止模拟交易",
        use_container_width=True,
        disabled=not st.session_state.paper_running,
    )

# 启动逻辑
if start_btn:
    # 创建策略实例
    if selected_strategy_name == "双均线交叉":
        strategy = MACrossStrategy(fast_period=5, slow_period=20)
    elif selected_strategy_name == "RSI均值回归":
        strategy = RSIStrategy()
    else:
        strategy = MACrossStrategy()

    # 创建风险管理器
    risk_mgr = RiskManager(
        max_position_pct=max_position,
        stop_loss_pct=stop_loss,
        take_profit_pct=take_profit,
        max_daily_loss_pct=daily_limit,
    )

    # 创建模拟交易器
    trader = PaperTrader(
        strategy=strategy,
        initial_capital=initial_capital,
        risk_manager=risk_mgr,
    )
    trader.start(symbol=symbol, timeframe="1h")

    st.session_state.paper_trader = trader
    st.session_state.paper_running = True
    st.session_state.paper_start_time = datetime.now()

    st.markdown("""
    <div class="success-box">
        ✅ 模拟交易已启动！系统将从交易所获取最新数据并模拟执行策略。
    </div>
    """, unsafe_allow_html=True)

# 停止逻辑
if stop_btn:
    if st.session_state.paper_trader:
        st.session_state.paper_trader.stop()
    st.session_state.paper_running = False

    st.markdown("""
    <div class="warning-box">
        ⏹️ 模拟交易已停止
    </div>
    """, unsafe_allow_html=True)

# ===== 第三步：查看状态 =====
st.markdown("---")
st.markdown("### 第三步：模拟账户状态")

if st.session_state.paper_running and st.session_state.paper_trader:
    trader = st.session_state.paper_trader

    # 获取最新价格
    df = manager.get_data(symbol, "1h", limit=1, auto_sync=True)
    current_price = df["close"].iloc[-1] if not df.empty else 0

    status = trader.get_status(current_price)

    # 账户概览
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 总权益", f"${status['equity']:,.2f}",
                  delta=f"{status['pnl_pct']:+.2f}%")
    with col2:
        st.metric("💵 可用现金", f"${status['cash']:,.2f}")
    with col3:
        st.metric("📦 持仓数量", f"{status['position']:.4f}")
    with col4:
        st.metric("🔄 交易次数", status['trade_count'])

    # 运行状态
    run_duration = (datetime.now() - st.session_state.paper_start_time).seconds // 60
    st.markdown(f"""
    <div style="background: #E8F5E9; padding: 10px; border-radius: 8px; text-align: center; color: #1A1A1A;">
        🟢 模拟运行中 · {symbol} 1h · 已运行 {run_duration} 分钟 ·
        成交 {status['trade_count']} 笔
    </div>
    """, unsafe_allow_html=True)

    # 交易记录
    st.markdown("#### 📋 交易记录")
    trades_df = trader.get_trades_df()
    if not trades_df.empty:
        st.dataframe(trades_df.tail(20), use_container_width=True, hide_index=True)
    else:
        st.info("暂无交易记录，等待策略信号...")

elif not st.session_state.paper_running and st.session_state.paper_trader:
    # 已停止，显示最终结果
    trader = st.session_state.paper_trader

    df = manager.get_data(symbol, "1h", limit=1, auto_sync=True)
    current_price = df["close"].iloc[-1] if not df.empty else 0
    status = trader.get_status(current_price)

    st.markdown("#### 📊 最终结果")

    col1, col2, col3 = st.columns(3)
    with col1:
        final_pnl = status['pnl']
        st.metric("最终盈亏", f"${final_pnl:+,.2f}",
                  delta=f"{status['pnl_pct']:+.2f}%")
    with col2:
        st.metric("总手续费", f"${status['total_fees']:,.2f}")
    with col3:
        st.metric("总交易次数", status['trade_count'])

    trades_df = trader.get_trades_df()
    if not trades_df.empty:
        st.dataframe(trades_df, use_container_width=True, hide_index=True)

else:
    st.info("👆 请配置参数后点击「启动模拟交易」开始模拟")

# ===== 说明 =====
st.markdown("---")
with st.expander("💡 模拟交易说明"):
    st.markdown("""
    **模拟交易 vs 回测**
    - **回测**：用历史数据一次性跑完，结果瞬间出来
    - **模拟交易**：用实时推送的最新数据，一笔一笔执行，更接近真实

    **建议流程**
    1. 先在「策略工坊」创建或选择策略
    2. 在「策略回测」用历史数据验证
    3. 在「模拟交易」用实时数据演练至少1周
    4. 确认策略稳定后，再考虑「实盘交易」

    **模拟交易的局限**
    - 不模拟订单簿深度（你的大单不会影响市场价）
    - 不模拟网络延迟和交易所故障
    - 滑点和手续费是固定假设值
    """)
