"""
策略工坊页面
可视化因子构建器 — 用大白话描述想法，自动生成策略代码
"""

import streamlit as st
import sys
import os
from datetime import datetime

# 确保模块导入
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from factor_builder.templates import get_all_templates, get_templates_by_category, search_templates
from factor_builder.generator import (
    generate_strategy_code, save_strategy, save_strategy_with_meta,
    list_generated_strategies, load_strategy_code, extract_strategy_info,
)
from factor_builder.parser import parse

# ===== 页面初始化 =====
st.markdown("# 🧠 策略工坊")
st.markdown("用大白话描述你的交易想法，系统自动生成策略代码")

# ===== 标签页：因子构建器 / 策略模板 / 我的策略 =====
tab1, tab2, tab3 = st.tabs(["✨ 因子构建器", "📚 策略模板库", "📁 我的策略"])

# ============================================================
# Tab 1: 因子构建器（核心功能）
# ============================================================
with tab1:
    st.markdown("### ✨ 可视化因子构建器")
    st.markdown("在下方输入你的交易想法，系统会自动识别指标并生成策略代码")

    # 输入示例
    with st.expander("💡 点击查看输入示例"):
        st.markdown("""
        你可以这样描述你的策略：
        - **简单买入**：\"当5日均线上穿20日均线时买入\"
        - **金叉死叉**：\"MA5金叉MA20买入，死叉卖出\"
        - **KDJ策略**：\"KDJ的K值低于20时买入，高于80时卖出\"
        - **组合策略**：\"MACD金叉且KDJ也在低位时买入\"
        - **放量突破**：\"价格突破20日最高且成交量大于均量1.5倍时买入\"
        - **止损止盈**：\"买入后亏损5%止损，盈利10%止盈\"
        """)

    st.markdown("---")

    # 用户输入
    col1, col2 = st.columns([3, 1])

    with col1:
        user_input = st.text_area(
            "📝 描述你的交易策略",
            placeholder="例如：当5日均线上穿20日均线，且成交量放大时买入，RSI超过70时卖出...",
            height=100,
            help="使用自然语言描述策略，系统会自动识别均线、KDJ、MACD、成交量等指标",
        )

    with col2:
        st.markdown("#### 🎯 快速填充")
        quick_templates = {
            "双均线": "当5日均线上穿20日均线时买入，下穿时卖出",
            "KDJ超卖": "当KDJ的K值低于20时买入，高于80时卖出",
            "MACD共振": "MACD金叉且KDJ在50以下金叉时买入，任一死叉时卖出",
            "放量突破": "价格突破20日最高价且成交量大于1.5倍均量时买入",
        }
        for name, desc in quick_templates.items():
            if st.button(f"📌 {name}", key=f"quick_{name}", use_container_width=True):
                user_input = desc
                st.rerun()

    st.markdown("---")

    # 解析预览 + 生成按钮
    if user_input.strip():
        # 实时解析预览
        parsed = parse(user_input.strip())

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**🔍 识别到的指标**")
            if parsed.indicators:
                for ind in parsed.indicators:
                    st.markdown(f"- 📊 {ind['name']}")
            else:
                st.markdown("*未识别到具体指标*")

        with col2:
            st.markdown("**🔀 识别到的条件**")
            if parsed.conditions:
                for cond in parsed.conditions:
                    st.markdown(f"- {cond['keyword']}")
            else:
                st.markdown("*未识别到条件*")

        with col3:
            st.markdown("**🎯 识别到的动作**")
            if parsed.actions:
                for act in parsed.actions:
                    emoji = "🟢" if "BUY" in act["type"] else "🔴"
                    st.markdown(f"- {emoji} {act['keyword']}")
            else:
                st.markdown("*未识别到交易动作*")

        # 匹配模板
        matched_templates = search_templates(user_input.strip())

        st.markdown("---")
        st.markdown("**📋 匹配到的模板**")

        if matched_templates:
            cols = st.columns(min(len(matched_templates), 3))
            for i, tmpl in enumerate(matched_templates[:6]):
                with cols[i % 3]:
                    st.markdown(f"""
                    <div style="background: #F5F5F5; padding: 10px; border-radius: 8px; margin: 4px 0;
                                border: 1px solid {'#2E86C1' if i == 0 else '#E0E0E0'};">
                        <b style="color: #1A1A1A;">{'⭐ ' if i == 0 else ''}{tmpl['name']}</b><br>
                        <small style="color: #666666;">{tmpl['category']} · {tmpl['description']}</small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("未找到精确匹配的模板，将使用默认双均线策略模板")

        st.markdown("---")

        # 参数调整
        st.markdown("**⚙️ 参数调整（可选）**")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            fast_period = st.number_input("快线周期", 1, 200, 5, help="短期均线/快线周期")
        with col2:
            slow_period = st.number_input("慢线周期", 1, 500, 20, help="长期均线/慢线周期")
        with col3:
            stop_loss = st.number_input("止损 (%)", 0.0, 50.0, 5.0, step=0.5, help="止损百分比")
        with col4:
            take_profit = st.number_input("止盈 (%)", 0.0, 100.0, 10.0, step=0.5, help="止盈百分比")

        # 生成按钮
        if st.button("🚀 生成策略代码", type="primary", use_container_width=True):
            with st.spinner("正在生成策略代码..."):
                template_name = matched_templates[0]["name"] if matched_templates else None

                result = generate_strategy_code(
                    user_input=user_input.strip(),
                    template_name=template_name,
                    params_override={
                        "fast_period": fast_period if fast_period != 5 else None,
                        "slow_period": slow_period if slow_period != 20 else None,
                    },
                )

            st.markdown("---")
            st.markdown("### 📝 生成的策略代码")

            # 显示代码
            st.code(result["code"], language="python", line_numbers=True)

            # 操作按钮
            col1, col2, col3 = st.columns(3)

            with col1:
                strategy_name = st.text_input(
                    "策略名称",
                    value=f"我的策略_{datetime.now().strftime('%m%d_%H%M')}",
                    help="保存策略的文件名",
                )

            with col2:
                if st.button("💾 保存策略", use_container_width=True):
                    filepath = save_strategy_with_meta(
                        result["code"], strategy_name,
                        description=user_input.strip(),
                        template=result.get("template", ""),
                    )
                    st.markdown(f"""
                    <div class="success-box">
                        ✅ 策略已保存到: <code>{filepath}</code>
                    </div>
                    """, unsafe_allow_html=True)

            with col3:
                if st.button("⏮️ 立即回测此策略", use_container_width=True):
                    # 先保存
                    filepath = save_strategy_with_meta(
                        result["code"], strategy_name,
                        description=user_input.strip(),
                        template=result.get("template", ""),
                    )
                    st.session_state.goto_backtest = strategy_name
                    try:
                        st.switch_page("pages/4_⏮️_策略回测.py")
                    except Exception:
                        st.markdown("""
                        <div class="success-box">
                            ✅ 策略已保存！请切换到 <b>「策略回测」</b> 页面进行回测
                        </div>
                        """, unsafe_allow_html=True)

    else:
        st.info("👆 请在上方文本框中输入你的交易策略描述")

# ============================================================
# Tab 2: 策略模板库
# ============================================================
with tab2:
    st.markdown("### 📚 策略模板库")
    st.markdown("点击模板查看详情，或直接使用")

    # 分类筛选
    categories = ["全部"] + list(set(t["category"] for t in get_all_templates()))
    selected_category = st.selectbox("筛选分类", categories)

    templates = get_all_templates()
    if selected_category != "全部":
        templates = get_templates_by_category(selected_category)

    # 模板卡片
    for tmpl in templates:
        with st.expander(f"{tmpl['name']} — {tmpl['description']}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**分类**: {tmpl['category']}")
                st.markdown(f"**关键词**: {', '.join(tmpl['keywords'][:8])}")
                st.markdown(f"**默认参数**: {tmpl['default_params']}")

                # 显示代码预览
                code_preview = tmpl["code_template"][:500] + "\n# ... (点击「使用此模板」查看完整代码)"
                st.code(code_preview, language="python")

            with col2:
                if st.button("⭐ 使用此模板", key=f"use_{tmpl['name']}", use_container_width=True):
                    result = generate_strategy_code(
                        user_input=tmpl["description"],
                        template_name=tmpl["name"],
                    )
                    st.session_state.template_code = result["code"]
                    st.session_state.template_name = tmpl["name"]
                    st.rerun()

# ============================================================
# Tab 3: 我的策略
# ============================================================
with tab3:
    st.markdown("### 📁 我的策略")
    st.markdown("管理已保存和生成的策略文件")

    # 初始化 session state
    if "viewing_strategy_path" not in st.session_state:
        st.session_state.viewing_strategy_path = None
    if "copy_confirmed" not in st.session_state:
        st.session_state.copy_confirmed = False

    # ----- 刷新策略列表 -----
    strategies = list_generated_strategies()

    if not strategies:
        st.info("📭 还没有保存的策略，去「因子构建器」创建一个吧！")
    else:
        # ===== 策略列表 =====
        st.markdown("---")

        for i, strat in enumerate(strategies):
            # 提取详细信息
            info = extract_strategy_info(strat["path"])
            display_name = info.get("display_name") or strat["name"]
            description = info.get("description") or "（无描述）"

            col1, col2, col3, col4 = st.columns([4, 1, 1, 1])

            with col1:
                tag = "🤖" if strat["is_generated"] else "📝"
                st.markdown(
                    f"**{tag} {display_name}**  "
                    f"<small style='color: #888888;'>{strat['modified']}</small>",
                    unsafe_allow_html=True,
                )
                # 显示一行简述
                desc_text = description[:60] + "…" if len(description) > 60 else description
                st.caption(desc_text)

            with col2:
                if st.button("📖 查看", key=f"view_{i}_{strat['name']}", use_container_width=True):
                    st.session_state.viewing_strategy_path = strat["path"]
                    st.rerun()

            with col3:
                if st.button("⏮️ 回测", key=f"bt_{i}_{strat['name']}", use_container_width=True):
                    st.session_state.goto_backtest = strat["name"]
                    # 尝试直接跳转
                    try:
                        st.switch_page("pages/4_⏮️_策略回测.py")
                    except Exception:
                        st.success("✅ 已选择策略，请切换到 **「策略回测」** 页面")

            with col4:
                # 删除按钮（仅标记，实际删除需要另外实现）
                pass

            st.markdown("<hr style='margin:4px 0;border-color:#E8E8E8;'>", unsafe_allow_html=True)

        # ===== 查看策略详情容器 =====
        if st.session_state.viewing_strategy_path:
            st.markdown("---")
            st.markdown("### 📖 策略详情")

            viewing_path = st.session_state.viewing_strategy_path
            info = extract_strategy_info(viewing_path)

            if not info["code"]:
                st.warning("⚠️ 无法读取策略文件")
            else:
                display_name = info["display_name"] or info["name"]
                description = info["description"] or "（该策略未包含描述信息）"
                code = info["code"]

                # 关闭查看按钮
                if st.button("✖ 关闭", key="close_view"):
                    st.session_state.viewing_strategy_path = None
                    st.rerun()

                # ---- 策略详情容器 ----
                # 使用自定义 HTML 容器（名称 + 描述 + 代码）
                st.markdown(f"""
                <div style="
                    background: #F5F5F5;
                    border: 1px solid #E0E0E0;
                    border-radius: 10px;
                    padding: 0;
                    margin: 8px 0;
                    overflow: hidden;
                ">
                    <!-- 顶部栏：策略名 + 描述 -->
                    <div style="
                        background: #FAFAFA;
                        padding: 16px 20px;
                        border-bottom: 1px solid #E8E8E8;
                    ">
                        <div style="font-size: 1.1rem; font-weight: 700; color: #2C3E50; margin-bottom: 6px;">
                            🧠 {display_name}
                        </div>
                        <div style="font-size: 0.9rem; color: #555555;">
                            📝 {description}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ---- 代码块（含复制按钮） ----
                # 生成唯一 ID 避免多策略查看时冲突
                import hashlib
                uid = hashlib.md5(viewing_path.encode()).hexdigest()[:8]

                col_code, col_copy = st.columns([5, 1])
                with col_code:
                    st.caption("📄 策略代码")
                with col_copy:
                    # 使用 hidden textarea + JS 复制，避免转义问题
                    st.markdown(f"""
                    <textarea id="code_{uid}" style="display:none;">{code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</textarea>
                    <button onclick="
                        var el = document.getElementById('code_{uid}');
                        el.style.display = 'block';
                        el.select();
                        try {{
                            navigator.clipboard.writeText(el.value);
                            this.innerText = '✅ 已复制!';
                        }} catch(e) {{
                            document.execCommand('copy');
                            this.innerText = '✅ 已复制!';
                        }}
                        el.style.display = 'none';
                        setTimeout(function() {{ this.innerText = '📋 复制代码'; }}.bind(this), 2000);
                    " style="
                        background: #2E86C1;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 6px;
                        padding: 6px 16px;
                        font-size: 0.85rem;
                        cursor: pointer;
                        white-space: nowrap;
                    ">📋 复制代码</button>
                    """, unsafe_allow_html=True)

                st.code(code, language="python", line_numbers=True)

                # 再次提供关闭按钮
                if st.button("⬆ 收起详情", key="close_view_bottom"):
                    st.session_state.viewing_strategy_path = None
                    st.rerun()
