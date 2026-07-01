"""
策略回测页面
选择策略 → 选择币种 → 设置参数 → 运行回测 → 查看结果

v2: 纯本地数据模式，不触发任何网络请求，避免阻塞
"""

import streamlit as st
import sys
import os
import pandas as pd
import importlib.util
from datetime import datetime

# 确保模块导入
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backtest.engine import BacktestEngine
from ui.components.result_cards import show_metric_cards, show_equity_chart, show_trade_details
from factor_builder.generator import list_generated_strategies, load_strategy_code

# ===== 页面初始化 =====
st.markdown("# ⏮️ 策略回测")
st.markdown("用本地历史数据验证交易策略（纯离线，不联网）")

# ---- 数据库只读连接（不触发任何网络请求） ----
DB_PATH = "E:/crypto_quant/data/market.db"


@st.cache_resource
def get_storage():
    """获取只读数据库连接（缓存，不重复创建）"""
    from data.storage import DataStorage
    return DataStorage(db_path=DB_PATH)


def list_available_data():
    """列出数据库中已有的数据"""
    try:
        storage = get_storage()
        summary = storage.get_data_summary()
        if summary.empty:
            return [], {}
        available = {}
        for _, row in summary.iterrows():
            key = (row["交易对"], row["K线周期"])
            available[key] = int(row["数据条数"])
        return list(available.keys()), available
    except Exception:
        return [], {}


storage = get_storage()
available_pairs, available_counts = list_available_data()

# ===== 第一步：选择策略 =====
st.markdown("---")
st.markdown("### 第一步：选择要回测的策略")

# 获取可用策略列表
preset_strategies = {
    "双均线交叉 MA5/20": "strategy.examples.ma_cross",
    "RSI均值回归 RSI14": "strategy.examples.rsi_strategy",
    "网格交易 10格": "strategy.examples.grid_trading",
}

# 获取用户生成的策略（新文件夹结构 + 旧扁平兼容）
user_strategies = list_generated_strategies()
user_strategy_names = {}
for s in user_strategies:
    if s.get("is_category"):
        # 分类文件夹中的子策略
        for child in s.get("children", []):
            user_strategy_names[child.get("name", "")] = child["path"]
    else:
        user_strategy_names[s.get("name", "")] = s["path"]

all_strategies = {**preset_strategies}
for name, path in user_strategy_names.items():
    all_strategies[f"📝 {name}"] = path

# 读取来自策略工坊的跳转信号
goto_name = st.session_state.pop("goto_backtest", None)

default_index = 0
if goto_name:
    for i, key in enumerate(all_strategies.keys()):
        if goto_name in key:
            default_index = i
            break

col1, col2 = st.columns([2, 1])

with col1:
    selected_strategy = st.selectbox(
        "🧠 选择策略",
        options=list(all_strategies.keys()),
        index=default_index,
        help="选择要回测的预置策略或自定义策略",
    )
    if goto_name:
        st.success(f"✅ 已自动选择策略: {goto_name}")

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    preview = st.checkbox("📖 预览策略代码", value=False)

if preview and selected_strategy:
    strategy_path = all_strategies[selected_strategy]
    if strategy_path.startswith("strategy."):
        st.info(f"预置策略模块: `{strategy_path}`")
    else:
        code = load_strategy_code(strategy_path)
        if code:
            st.code(code, language="python", line_numbers=True)

# ===== 第二步：选择回测参数 =====
st.markdown("---")
st.markdown("### 第二步：设置回测参数")

# ---- 数据可用性提示 ----
if available_pairs:
    available_str = "、".join([f"{s}（{t}）" for s, t in available_pairs[:8]])
    st.caption(f"📦 本地已有数据: {available_str}{' …' if len(available_pairs) > 8 else ''}")
else:
    st.warning("⚠️ 数据库为空，请先前往「📊 数据管理」下载历史数据", icon="⚠️")

col1, col2, col3 = st.columns(3)

with col1:
    symbol = st.selectbox(
        "💱 交易对",
        options=["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
                 "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT"],
        index=0,
    )

    timeframe = st.selectbox(
        "⏱️ K线周期",
        options=["1m", "5m", "15m", "1h", "4h", "1d"],
        index=3,
    )

    # 显示该交易对的数据量
    count = available_counts.get((symbol, timeframe), 0)
    if count > 0:
        st.caption(f"📊 本地: {count:,} 条")
    else:
        st.caption("⚠️ 无本地数据")

with col2:
    initial_capital = st.number_input(
        "💰 初始资金 (USDT)",
        min_value=100,
        max_value=10000000,
        value=10000,
        step=1000,
    )

    mode = st.selectbox(
        "📊 交易模式",
        options=["spot", "futures"],
        format_func=lambda x: "现货" if x == "spot" else "合约",
    )

with col3:
    maker_fee = st.number_input(
        "💸 手续费率 (%)",
        min_value=0.0,
        max_value=1.0,
        value=0.1,
        step=0.01,
    ) / 100

    slippage = st.number_input(
        "📉 滑点 (%)",
        min_value=0.0,
        max_value=2.0,
        value=0.05,
        step=0.01,
    ) / 100

# 数据范围
data_range = st.select_slider(
    "📅 回测数据范围",
    options=["7天", "30天", "90天", "180天", "365天"],
    value="30天",
)
days_map = {"7天": 7, "30天": 30, "90天": 90, "180天": 180, "365天": 365}
days = days_map[data_range]

# ===== 第三步：运行回测 =====
st.markdown("---")
st.markdown("### 第三步：运行回测")

run_btn = st.button("🚀 开始回测", type="primary", use_container_width=True)

if run_btn:
    # ---- 阶段1：加载本地数据 ----
    status_placeholder = st.empty()
    status_placeholder.info("📥 正在从本地数据库加载数据…")

    df = storage.load_ohlcv("binance", symbol, timeframe, limit=1500)

    if df.empty:
        status_placeholder.error(
            f"❌ 数据库中无 {symbol} {timeframe} 数据。\n\n"
            f"请先前往 **「📊 数据管理」** 页面下载该交易对的历史K线。"
        )
        st.stop()

    # 截取指定天数
    cutoff = df.index[-1] - pd.Timedelta(days=days)
    df = df[df.index >= cutoff]

    if len(df) < 20:
        status_placeholder.warning(
            f"⚠️ 数据量不足（仅 {len(df)} 条），回测结果可能不可靠。"
            f"建议先下载更多数据。"
        )
        st.stop()

    status_placeholder.success(f"✅ 已加载 {len(df)} 条K线（{df.index[0]} ~ {df.index[-1]}）")

    # ---- 阶段2：加载策略 ----
    progress_placeholder = st.empty()
    progress_placeholder.info("🧠 正在加载策略…")

    strategy_class = None
    strategy_path = all_strategies[selected_strategy]

    if strategy_path.startswith("strategy."):
        try:
            module = importlib.import_module(strategy_path)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                    and attr.__name__ != "Strategy"
                    and hasattr(attr, "on_bar")):
                    strategy_class = attr
                    break
        except Exception as e:
            progress_placeholder.error(f"❌ 加载预置策略失败: {e}")
            st.stop()
    else:
        # 处理文件夹结构：user_strategies/{name}/strategy.py
        py_path = strategy_path
        if os.path.isdir(strategy_path):
            py_path = os.path.join(strategy_path, "strategy.py")
            if not os.path.exists(py_path):
                progress_placeholder.error(f"❌ 策略文件不存在: {py_path}")
                st.stop()
        try:
            spec = importlib.util.spec_from_file_location("user_strategy", py_path)
            user_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(user_module)
            for attr_name in dir(user_module):
                attr = getattr(user_module, attr_name)
                if (isinstance(attr, type)
                    and attr.__name__ != "Strategy"
                    and hasattr(attr, "on_bar")):
                    strategy_class = attr
                    break
        except Exception as e:
            progress_placeholder.error(f"❌ 加载用户策略失败: {e}")
            st.stop()

    if strategy_class is None:
        progress_placeholder.error("❌ 未找到策略类，请检查策略代码")
        st.stop()

    # ---- 阶段3：执行回测 ----
    progress_placeholder.info("⚡ 正在执行回测…")

    strategy = strategy_class()
    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=initial_capital,
        mode=mode,
        maker_fee=maker_fee,
        taker_fee=maker_fee,
        slippage=slippage,
        equity_sample_step=max(1, len(df) // 500),  # 大数据集自动降采样
    )

    import time
    t0 = time.perf_counter()
    result = engine.run(df, symbol=symbol, timeframe=timeframe)
    elapsed = time.perf_counter() - t0

    progress_placeholder.empty()
    status_placeholder.empty()

    st.caption(f"⏱️ 回测耗时: {elapsed:.2f}s（{len(df):,} 条K线）")

    # ===== 显示结果 =====
    st.markdown("---")
    st.markdown("## 📊 回测结果")

    # 指标卡片
    metrics = result.to_dict()
    show_metric_cards(metrics)

    # 权益曲线
    st.markdown("---")
    st.markdown("### 📈 权益曲线")
    if result.equity_curve is not None and not result.equity_curve.empty:
        show_equity_chart(
            result.equity_curve,
            f"{symbol} {timeframe} - {result.strategy_name}"
        )
    else:
        st.info("无权益曲线数据")

    # 交易明细
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📋 交易记录")
        if result.trades is not None and not result.trades.empty:
            show_trade_details(result.trades)
        else:
            st.info("无交易记录")

    with col2:
        if (result.monthly_returns is not None
            and not result.monthly_returns.empty):
            st.markdown("### 📅 月度收益 (%)")
            st.dataframe(
                result.monthly_returns.round(2),
                use_container_width=True,
            )
        else:
            st.caption("数据不足，无法计算月度收益")

    # 策略总结
    st.markdown("---")
    st.markdown("### 💡 策略分析")

    col1, col2, col3 = st.columns(3)

    with col1:
        total_ret = result.total_return
        if total_ret > 0:
            st.success(f"✅ 总收益率为正: {total_ret:+.2f}%")
        else:
            st.error(f"❌ 总收益率为负: {total_ret:+.2f}%")

    with col2:
        sharpe = result.sharpe_ratio
        if sharpe >= 2:
            st.success(f"✅ 夏普比率优秀: {sharpe:.2f}")
        elif sharpe >= 1:
            st.info(f"ℹ️ 夏普比率良好: {sharpe:.2f}")
        else:
            st.warning(f"⚠️ 夏普比率偏低: {sharpe:.2f}")

    with col3:
        dd = result.max_drawdown
        if dd < 10:
            st.success(f"✅ 最大回撤可控: {dd:.2f}%")
        elif dd < 20:
            st.info(f"ℹ️ 最大回撤适中: {dd:.2f}%")
        else:
            st.warning(f"⚠️ 最大回撤较大: {dd:.2f}%")

else:
    st.info("👆 选择策略和参数后，点击「开始回测」按钮")
