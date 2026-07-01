"""
加密货币量化交易系统 - 主入口
Streamlit Web 界面，所有操作的可视化入口

启动方式：
    streamlit run ui/app.py
    或双击 "启动.bat"
"""

import streamlit as st
import sys
import os

# 将项目根目录加入Python路径（确保模块导入正常）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ===== 页面配置 =====
st.set_page_config(
    page_title="加密货币量化交易系统",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== 自定义CSS（简洁浅色主题） =====
st.markdown("""
<style>
    /* ===== 页面背景 ===== */
    .stApp {
        background-color: #FAFBFC;
    }

    /* ===== 侧边栏 ===== */
    [data-testid="stSidebar"] {
        background-color: #F0F1F3;
        border-right: 1px solid #DDE;
    }
    [data-testid="stSidebar"] * {
        color: #2C3E50 !important;
    }

    /* ===== 标题层级 ===== */
    h1 {
        color: #2C3E50 !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }
    h2 {
        color: #34495E !important;
        font-size: 1.5rem !important;
    }
    h3 {
        color: #555555 !important;
        font-size: 1.2rem !important;
    }

    /* ===== 卡片容器（浅灰底色 + 黑字） ===== */
    .info-card {
        background: #F5F5F5;
        border-radius: 12px;
        padding: 24px;
        margin: 12px 0;
        border: 1px solid #E8E8E8;
    }
    .info-card h3 {
        color: #2C3E50 !important;
        margin-bottom: 12px;
    }
    .info-card p {
        color: #555555;
        font-size: 0.95rem;
        line-height: 1.6;
    }

    /* ===== 主按钮（简洁蓝色） ===== */
    .stButton > button {
        background: #2E86C1 !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 12px 32px !important;
        width: 100%;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #1B6CA8 !important;
        transform: translateY(-1px);
    }

    /* ===== 状态信息框（柔和底色 + 醒目左边框） ===== */
    .success-box {
        background: #E8F5E9;
        border-left: 4px solid #4CAF50;
        padding: 16px;
        border-radius: 8px;
        margin: 12px 0;
        color: #1A1A1A;
    }
    .warning-box {
        background: #FFF8E1;
        border-left: 4px solid #FFC107;
        padding: 16px;
        border-radius: 8px;
        margin: 12px 0;
        color: #1A1A1A;
    }
    .error-box {
        background: #FFEBEE;
        border-left: 4px solid #F44336;
        padding: 16px;
        border-radius: 8px;
        margin: 12px 0;
        color: #1A1A1A;
    }

    /* ===== Metric 指标卡片 ===== */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 12px;
        border: 1px solid #E8E8E8;
    }
    [data-testid="stMetric"] label {
        color: #666666 !important;
    }
    [data-testid="stMetricValue"] {
        color: #2C3E50 !important;
        font-size: 1.5rem !important;
    }

    /* ===== 数据表格 ===== */
    [data-testid="stTable"] {
        background: #FFFFFF;
        border-radius: 8px;
    }

    /* ===== 辅助文字 ===== */
    .tooltip {
        color: #888888;
        font-size: 0.85rem;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# ===== 侧边栏导航 =====
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 16px 0;">
        <h1 style="font-size: 1.6rem !important;">🪙 量化交易系统</h1>
        <p style="color: #666666; font-size: 0.85rem;">CryptoQuant v1.0</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 导航按钮
    st.markdown("### 📋 功能导航")

    st.markdown("""
    <div style="color: #555555; font-size: 0.9rem; line-height: 2.2;">
        📊 <b>数据管理</b> — 下载历史数据<br>
        📈 <b>行情看板</b> — 实时K线和指标<br>
        🧠 <b>策略工坊</b> — 创建交易策略<br>
        🔬 <b>因子实验室</b> — 可视化构建策略<br>
        ⏮️ <b>策略回测</b> — 测试策略收益<br>
        💹 <b>模拟交易</b> — 模拟盘演练<br>
        🚀 <b>实盘交易</b> — 真实资金交易
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 系统状态指示
    st.markdown("### ⚡ 系统状态")
    st.markdown("""
    <div style="font-size: 0.85rem; color: #4CAF50;">
        🟢 系统运行中<br>
        📡 交易所: 币安 Binance<br>
        💾 数据库: 已连接
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 风险提示（警告色容器）
    st.markdown("""
    <div style="background: #FFF3E0; padding: 12px; border-radius: 8px; border: 1px solid #FFCC80;">
        <p style="color: #E65100; font-size: 0.8rem; margin: 0;">
            ⚠️ <b>风险提示</b><br>
            加密货币交易存在高风险，可能导致本金全部亏损。
            本系统仅供学习研究使用，不构成投资建议。
        </p>
    </div>
    """, unsafe_allow_html=True)


# ===== 主页内容 =====
st.markdown("# 🪙 加密货币量化交易系统")
st.markdown("#### 一站式数据抓取 · 策略回测 · 量化交易平台")

st.markdown("---")

# 欢迎引导卡片
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="info-card">
        <h3>📊 第1步：获取数据</h3>
        <p>进入<b>「数据管理」</b>页面，选择交易所和币种，一键下载历史K线数据到本地数据库。支持币安、OKX、Bybit等主流交易所。</p>
        <p class="tooltip">💡 首次使用建议下载BTC/USDT的1小时K线</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="info-card">
        <h3>📈 第2步：查看行情</h3>
        <p>在<b>「行情看板」</b>查看实时K线图、均线、KDJ、成交量等指标。直观了解市场走势，发现交易机会。</p>
        <p class="tooltip">💡 支持MA5/MA10/MA20/MA60均线叠加</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="info-card">
        <h3>🧠 第3步：创建策略</h3>
        <p>使用<b>「策略工坊」</b>，用大白话描述你的交易想法，系统自动生成策略代码。也可以直接使用预置策略模板。</p>
        <p class="tooltip">💡 试试输入："当5日均线上穿20日均线时买入"</p>
    </div>
    """, unsafe_allow_html=True)

col4, col5, col6 = st.columns(3)

with col4:
    st.markdown("""
    <div class="info-card">
        <h3>⏮️ 第4步：策略回测</h3>
        <p>在<b>「策略回测」</b>中用历史数据测试策略表现。查看收益率、最大回撤、夏普比率等关键指标。</p>
        <p class="tooltip">💡 回测结果不代表未来表现，但能发现策略缺陷</p>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown("""
    <div class="info-card">
        <h3>💹 第5步：模拟交易</h3>
        <p>在<b>「模拟交易」</b>中用虚拟资金演练，零风险验证策略在真实市场中的表现。</p>
        <p class="tooltip">💡 建议先模拟交易至少1周再考虑实盘</p>
    </div>
    """, unsafe_allow_html=True)

with col6:
    st.markdown("""
    <div class="info-card">
        <h3>🚀 第6步：实盘交易</h3>
        <p>准备好后，在<b>「实盘交易」</b>中配置API密钥，启动真实交易。务必设置止损和仓位控制。</p>
        <p class="tooltip">⚠️ 实盘有真实亏损风险，请谨慎操作</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# 快速开始按钮
st.markdown("### 🚀 快速开始")
st.markdown("第一次使用？点击下方按钮，自动下载主流币种数据：")

if st.button("⚡ 一键下载主流币种数据（BTC/ETH等10个，约需1-2分钟）", type="primary"):
    with st.spinner("正在下载数据，请耐心等待..."):
        from data.manager import create_manager
        manager = create_manager()

        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total):
            progress_bar.progress(current / total)
            status_text.text(f"正在下载... {current}/{total}")

        result = manager.download_top_coins("1h", days=30, top_n=10, progress_callback=update_progress)

        progress_bar.progress(1.0)
        status_text.empty()

        st.markdown(f"""
        <div class="success-box">
            <b>✅ 下载完成！</b><br>
            成功: {result['success']} 个币种 | 失败: {result['failed']} 个<br>
            现在可以前往 <b>「行情看板」</b> 查看K线图了！
        </div>
        """, unsafe_allow_html=True)
