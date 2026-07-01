"""
因子实验室 — 可视化因子组合 → 策略代码生成
通过点击选择和排列因子，所见即所得地构建交易策略
"""

import streamlit as st
import sys
import os
import json
from datetime import datetime

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from factor_builder.factor_store import (
    BUILTIN_FACTORS, CONDITION_TYPES,
    save_user_factor, list_user_factors,
)
from factor_builder.generator import (
    save_strategy_with_meta, generate_strategy_code,
)

# ===== 页面初始化 =====
st.markdown("# 🔬 因子实验室")
st.markdown("勾选因子 → 配置参数 → 设置条件 → 自动生成策略代码")

# 初始化 session state
if "lab_workspace" not in st.session_state:
    st.session_state.lab_workspace = {
        "selected_factors": [],      # [{type, params, name, category}]
        "buy_conditions": [],         # [{type, left, right, threshold}]
        "sell_conditions": [],
        "stop_loss": 0.0,
        "take_profit": 0.0,
    }
if "lab_generated_code" not in st.session_state:
    st.session_state.lab_generated_code = ""
if "lab_strategy_name" not in st.session_state:
    st.session_state.lab_strategy_name = ""

ws = st.session_state.lab_workspace

# ===== 左右两栏布局 =====
left, right = st.columns([1, 2])

# ============================================================
# 左栏：因子面板
# ============================================================
with left:
    st.markdown("### 📊 因子面板")
    st.caption("勾选要使用的技术指标")

    # 按分类组织因子
    categories = {}
    for f in BUILTIN_FACTORS:
        cat = f["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f)

    for cat, factors in categories.items():
        emoji_map = {"趋势": "📈", "震荡": "🔄", "波动": "📊", "成交量": "📉"}
        emoji = emoji_map.get(cat, "📌")
        with st.expander(f"{emoji} {cat}类", expanded=True):
            for i, fac in enumerate(factors):
                ftype = fac["type"]
                fname = fac["name"]
                key = f"chk_{cat}_{ftype}_{i}"

                # 检查是否已选中
                is_selected = any(
                    s["type"] == ftype for s in ws["selected_factors"]
                )

                col_cb, col_cfg = st.columns([2, 1])
                with col_cb:
                    checked = st.checkbox(
                        f"{fname}",
                        value=is_selected,
                        key=key,
                        help=fac.get("description", ""),
                    )
                with col_cfg:
                    with st.popover("⚙️"):
                        new_params = {}
                        for pname, pval in fac["params"].items():
                            if isinstance(pval, (int, float)):
                                new_params[pname] = st.number_input(
                                    pname, value=pval, step=1 if isinstance(pval, int) else 0.5,
                                    key=f"param_{key}_{pname}",
                                )
                            else:
                                new_params[pname] = st.text_input(
                                    pname, value=str(pval), key=f"param_{key}_{pname}",
                                )

                # 更新 workspace
                if checked and not is_selected:
                    ws["selected_factors"].append({
                        "type": ftype,
                        "name": fname,
                        "category": cat,
                        "params": new_params or dict(fac["params"]),
                    })
                elif not checked and is_selected:
                    ws["selected_factors"] = [
                        s for s in ws["selected_factors"] if s["type"] != ftype
                    ]
                    # 同时清理相关条件
                    ws["buy_conditions"] = [
                        c for c in ws["buy_conditions"]
                        if c.get("left") != ftype and c.get("right") != ftype
                    ]
                    ws["sell_conditions"] = [
                        c for c in ws["sell_conditions"]
                        if c.get("left") != ftype and c.get("right") != ftype
                    ]
                elif checked and is_selected:
                    # 更新参数
                    for s in ws["selected_factors"]:
                        if s["type"] == ftype:
                            s["params"] = new_params or dict(fac["params"])

    # 保存因子按钮
    st.markdown("---")
    with st.expander("💾 保存当前因子组合"):
        save_name = st.text_input("因子名称", placeholder="如: 我的双均线组合", key="save_factor_name")
        save_desc = st.text_area("描述", placeholder="描述这个因子的用途", key="save_factor_desc")
        if st.button("💾 保存因子", use_container_width=True) and save_name.strip():
            factor_def = {
                "type": "combo",
                "factors": ws["selected_factors"],
                "buy_conditions": ws["buy_conditions"],
                "sell_conditions": ws["sell_conditions"],
                "stop_loss": ws["stop_loss"],
                "take_profit": ws["take_profit"],
            }
            path = save_user_factor(save_name.strip(), factor_def, save_desc, "组合")
            if path:
                st.success(f"因子已保存: {save_name.strip()}")

# ============================================================
# 右栏：策略工作台
# ============================================================
with right:
    st.markdown("### 🧩 策略工作台")
    st.caption("配置选中的因子、条件和买卖信号")

    # ---- 因子卡片 ----
    if not ws["selected_factors"]:
        st.info("👈 请在左侧因子面板中勾选要使用的技术指标")
    else:
        st.markdown("**📌 已选因子**")
        cols = st.columns(min(len(ws["selected_factors"]), 4))
        for i, fac in enumerate(ws["selected_factors"]):
            with cols[i % len(cols)]:
                # 因子卡片
                params_display = ", ".join(
                    f"{k}={v}" for k, v in fac.get("params", {}).items()
                )
                st.markdown(f"""
                <div style="
                    background: #F5F5F5;
                    border: 1px solid {'#2E86C1' if i == 0 else '#E0E0E0'};
                    border-radius: 8px;
                    padding: 10px;
                    margin: 4px 0;
                    text-align: center;
                ">
                    <div style="font-weight: 700; color: #2C3E50;">{fac['name']}</div>
                    <div style="font-size: 0.8rem; color: #888888;">{params_display}</div>
                </div>
                """, unsafe_allow_html=True)

    # ---- 条件设置 ----
    if len(ws["selected_factors"]) >= 2:
        st.markdown("---")
        st.markdown("**🔗 买入条件**")

        col_a, col_b, col_c = st.columns([2, 2, 1])
        with col_a:
            left_factor = st.selectbox(
                "因子 A", [f["type"] for f in ws["selected_factors"]],
                key="buy_left",
            )
        with col_b:
            cond_type = st.selectbox(
                "条件", [c["name"] for c in CONDITION_TYPES if c["type"] not in ("AND", "OR")],
                key="buy_cond",
            )
        with col_c:
            right_factor = st.selectbox(
                "因子 B", [f["type"] for f in ws["selected_factors"]],
                key="buy_right",
            )

        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button("➕ 添加买入条件", use_container_width=True):
                ct = [c for c in CONDITION_TYPES if c["name"] == cond_type][0]
                ws["buy_conditions"].append({
                    "type": ct["type"],
                    "left": left_factor,
                    "right": right_factor,
                })

        # 显示已有条件
        if ws["buy_conditions"]:
            with st.container():
                for i, cond in enumerate(ws["buy_conditions"]):
                    co, cr = st.columns([5, 1])
                    with co:
                        icons = {c["type"]: c["icon"] for c in CONDITION_TYPES}
                        icon = icons.get(cond["type"], "→")
                        st.markdown(
                            f"🟢 {cond['left']} {icon} {cond['right']}",
                        )
                    with cr:
                        if st.button("✕", key=f"rm_buy_{i}"):
                            ws["buy_conditions"].pop(i)
                            st.rerun()

        # 卖出条件
        st.markdown("**🔗 卖出条件**")
        col_a2, col_b2, col_c2 = st.columns([2, 2, 1])
        with col_a2:
            sl_factor = st.selectbox(
                "因子 A", [f["type"] for f in ws["selected_factors"]],
                key="sell_left",
            )
        with col_b2:
            scond_type = st.selectbox(
                "条件", [c["name"] for c in CONDITION_TYPES if c["type"] not in ("AND", "OR")],
                key="sell_cond",
            )
        with col_c2:
            sr_factor = st.selectbox(
                "因子 B", [f["type"] for f in ws["selected_factors"]],
                key="sell_right",
            )

        c1s, c2s = st.columns([1, 3])
        with c1s:
            if st.button("➕ 添加卖出条件", use_container_width=True):
                ct = [c for c in CONDITION_TYPES if c["name"] == scond_type][0]
                ws["sell_conditions"].append({
                    "type": ct["type"],
                    "left": sl_factor,
                    "right": sr_factor,
                })

        if ws["sell_conditions"]:
            for i, cond in enumerate(ws["sell_conditions"]):
                co, cr = st.columns([5, 1])
                with co:
                    icons = {c["type"]: c["icon"] for c in CONDITION_TYPES}
                    icon = icons.get(cond["type"], "→")
                    st.markdown(f"🔴 {cond['left']} {icon} {cond['right']}")
                with cr:
                    if st.button("✕", key=f"rm_sell_{i}"):
                        ws["sell_conditions"].pop(i)
                        st.rerun()

    # ---- 风控参数 ----
    st.markdown("---")
    st.markdown("**🛡️ 风控参数**")
    c1, c2 = st.columns(2)
    with c1:
        ws["stop_loss"] = st.number_input("止损 (%)", 0.0, 50.0, ws["stop_loss"], 0.5)
    with c2:
        ws["take_profit"] = st.number_input("止盈 (%)", 0.0, 100.0, ws["take_profit"], 0.5)

# ============================================================
# 底部操作栏
# ============================================================
st.markdown("---")

col_op1, col_op2, col_op3, col_op4, col_op5 = st.columns([1, 1, 1, 1, 1])

with col_op1:
    if st.button("🔄 清空工作台", use_container_width=True):
        st.session_state.lab_workspace = {
            "selected_factors": [],
            "buy_conditions": [],
            "sell_conditions": [],
            "stop_loss": 0.0,
            "take_profit": 0.0,
        }
        st.session_state.lab_generated_code = ""
        st.rerun()

with col_op2:
    if st.button("🚀 生成策略", type="primary", use_container_width=True):
        code = _workspace_to_code(ws)
        st.session_state.lab_generated_code = code
        st.rerun()

with col_op3:
    save_name = st.text_input("策略名称", placeholder="策略名", key="lab_strat_name", label_visibility="collapsed")

with col_op4:
    if st.button("💾 保存策略", use_container_width=True):
        if save_name.strip() and st.session_state.lab_generated_code:
            path = save_strategy_with_meta(
                st.session_state.lab_generated_code,
                save_name.strip(),
                description=f"因子实验室生成 — 买入: {len(ws['buy_conditions'])}个条件, 卖出: {len(ws['sell_conditions'])}个条件",
            )
            st.success(f"已保存: {save_name}")
        else:
            st.warning("请先生成策略代码")

with col_op5:
    if st.button("⏮️ 直接回测", use_container_width=True):
        if save_name.strip() and st.session_state.lab_generated_code:
            save_strategy_with_meta(
                st.session_state.lab_generated_code,
                save_name.strip(),
                description=f"因子实验室生成",
            )
            st.session_state.goto_backtest = save_name.strip()
            try:
                st.switch_page("pages/4_⏮️_策略回测.py")
            except Exception:
                st.success(f"✅ 策略已保存！切换到「策略回测」页面")
        else:
            st.warning("请先生成策略代码并命名")

# ============================================================
# 生成的代码展示
# ============================================================
if st.session_state.lab_generated_code:
    st.markdown("---")
    st.markdown("### 📝 生成的策略代码")

    import hashlib
    code = st.session_state.lab_generated_code
    uid = hashlib.md5(code.encode()).hexdigest()[:8]

    col_code, col_copy = st.columns([5, 1])
    with col_code:
        st.caption("📄 策略代码")
    with col_copy:
        st.markdown(f"""
        <textarea id="lab_code_{uid}" style="display:none;">{code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</textarea>
        <button onclick="
            var el = document.getElementById('lab_code_{uid}');
            el.style.display = 'block'; el.select();
            try {{ navigator.clipboard.writeText(el.value); this.innerText = '✅ 已复制!'; }}
            catch(e) {{ document.execCommand('copy'); this.innerText = '✅ 已复制!'; }}
            el.style.display = 'none';
            setTimeout(function() {{ this.innerText = '📋 复制代码'; }}.bind(this), 2000);
        " style="
            background: #2E86C1; color: #FFFFFF; border: none;
            border-radius: 6px; padding: 6px 16px; font-size: 0.85rem; cursor: pointer;
        ">📋 复制代码</button>
        """, unsafe_allow_html=True)

    st.code(code, language="python", line_numbers=True)


# ============================================================
# workspace → 策略代码
# ============================================================

def _workspace_to_code(ws: dict) -> str:
    """将工作台状态转为完整策略代码"""
    factors = ws.get("selected_factors", [])
    buy_conds = ws.get("buy_conditions", [])
    sell_conds = ws.get("sell_conditions", [])
    sl = ws.get("stop_loss", 0)
    tp = ws.get("take_profit", 0)

    if not factors:
        return "# 请先在因子面板中勾选技术指标"

    # 生成因子导入和计算代码
    factor_imports = []
    factor_calcs = []
    used_funcs = set()

    for f in factors:
        ftype = f["type"]
        params = f.get("params", {})

        if ftype in ("MA", "EMA", "WMA"):
            period = params.get("period", 20)
            col_name = f"{ftype}{period}"
            factor_calcs.append(f'        self.data["{col_name}"] = {ftype.lower()}(self.data, {period})')
            used_funcs.add(ftype.lower())

        elif ftype == "MACD":
            fast = params.get("fast", 12)
            slow = params.get("slow", 26)
            sig = params.get("signal", 9)
            factor_calcs.append(f"        self.data = macd(self.data, {fast}, {slow}, {sig})")
            used_funcs.add("macd")

        elif ftype == "KDJ":
            n = params.get("n", 9)
            m1 = params.get("m1", 3)
            m2 = params.get("m2", 3)
            factor_calcs.append(f"        self.data = kdj(self.data, {n}, {m1}, {m2})")
            used_funcs.add("kdj")

        elif ftype == "RSI":
            period = params.get("period", 14)
            factor_calcs.append(f'        self.data["RSI{period}"] = rsi(self.data, {period})')
            used_funcs.add("rsi")

        elif ftype == "BOLL":
            period = params.get("period", 20)
            std = params.get("std_dev", 2.0)
            factor_calcs.append(f"        self.data = bollinger_bands(self.data, {period}, {std})")
            used_funcs.add("bollinger_bands")

        elif ftype == "ATR":
            period = params.get("period", 14)
            factor_calcs.append(f'        self.data["ATR{period}"] = atr(self.data, {period})')
            used_funcs.add("atr")

        elif ftype == "Volume_MA":
            period = params.get("period", 20)
            factor_calcs.append(f'        self.data["VolMA{period}"] = volume_ma(self.data, {period})')
            used_funcs.add("volume_ma")

        elif ftype == "OBV":
            factor_calcs.append('        self.data["OBV"] = obv(self.data)')
            used_funcs.add("obv")

        elif ftype == "VWAP":
            factor_calcs.append('        self.data["VWAP"] = vwap(self.data)')
            used_funcs.add("vwap")

    # 导入语句
    func_imports = ", ".join(sorted(used_funcs))
    import_block = f"from strategy.factors import {func_imports}"

    # 构建买入逻辑
    buy_lines = []
    for i, cond in enumerate(buy_conds):
        left = _resolve_factor_column(cond["left"], factors)
        right = _resolve_factor_column(cond["right"], factors)
        ctype = cond["type"]
        prefix = "if" if i == 0 else "elif"

        if ctype == "CROSSOVER":
            buy_lines.append(
                f"            {prefix} {left}_now > {right}_now "
                f"and {left}_prev <= {right}_prev:"
            )
        elif ctype == "CROSSUNDER":
            buy_lines.append(
                f"            {prefix} {left}_now < {right}_now "
                f"and {left}_prev >= {right}_prev:"
            )
        elif ctype == "GREATER":
            buy_lines.append(f"            {prefix} {left}_now > {right}_now:")
        elif ctype == "LESS":
            buy_lines.append(f"            {prefix} {left}_now < {right}_now:")

    if buy_lines:
        buy_lines.append("                if not self.has_position():")
        buy_lines.append("                    size = self.portfolio[\"cash\"] / bar[\"close\"] * 0.95")
        buy_lines.append("                    self.buy(size=size, price=bar[\"close\"])")
    else:
        buy_lines.append("            # 未配置买入条件")
        buy_lines.append("            pass")

    # 构建卖出逻辑
    sell_lines = []
    for i, cond in enumerate(sell_conds):
        left = _resolve_factor_column(cond["left"], factors)
        right = _resolve_factor_column(cond["right"], factors)
        ctype = cond["type"]
        prefix = "if" if i == 0 else "elif"

        if ctype == "CROSSOVER":
            sell_lines.append(
                f"            {prefix} {left}_now > {right}_now "
                f"and {left}_prev <= {right}_prev and self.has_position():"
            )
        elif ctype == "CROSSUNDER":
            sell_lines.append(
                f"            {prefix} {left}_now < {right}_now "
                f"and {left}_prev >= {right}_prev and self.has_position():"
            )
        elif ctype == "GREATER":
            sell_lines.append(f"            {prefix} {left}_now > {right}_now and self.has_position():")
        elif ctype == "LESS":
            sell_lines.append(f"            {prefix} {left}_now < {right}_now and self.has_position():")

    if sell_lines:
        sell_lines.append("                self.close_position(price=bar[\"close\"])")
    else:
        sell_lines.append("            pass")

    # 止损止盈
    sl_tp_lines = []
    if sl > 0:
        sl_tp_lines.append(f"            # 止损: 亏损超过{sl}%")
        sl_tp_lines.append("            if self.has_position():")
        sl_tp_lines.append("                entry = self.portfolio[\"trades\"][-1][\"price\"]")
        sl_tp_lines.append(f"                if bar[\"close\"] < entry * (1 - {sl}/100):")
        sl_tp_lines.append("                    self.close_position(price=bar[\"close\"])")
    if tp > 0:
        sl_tp_lines.append(f"            # 止盈: 盈利超过{tp}%")
        sl_tp_lines.append("            if self.has_position():")
        sl_tp_lines.append("                entry = self.portfolio[\"trades\"][-1][\"price\"]")
        sl_tp_lines.append(f"                if bar[\"close\"] > entry * (1 + {tp}/100):")
        sl_tp_lines.append("                    self.close_position(price=bar[\"close\"])")

    # 组装完整代码
    buy_block = "\n".join(buy_lines)
    sell_block = "\n".join(sell_lines)
    sl_tp_block = "\n".join(sl_tp_lines)
    calc_block = "\n".join(factor_calcs)

    code = f'''"""
因子实验室自动生成策略
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
买入条件: {len(buy_conds)} 个
卖出条件: {len(sell_conds)} 个
止损: {sl}%  止盈: {tp}%
"""

from strategy.base import Strategy
{import_block}
import pandas as pd


class LabStrategy(Strategy):
    """因子实验室生成策略"""

    def __init__(self):
        super().__init__(name="因子实验室策略")

    def on_start(self):
        """计算因子"""
{calc_block}

    def on_bar(self, bar):
        idx = self.current_index
        if idx < 1:
            return

        # 获取因子当前值和前一值
{_build_factor_vars(factors)}

        # ---- 止损止盈 ----
{sl_tp_block if sl_tp_block else "        pass"}

        # ---- 卖出条件 ----
{sell_block}

        # ---- 买入条件 ----
{buy_block}
'''
    return code


def _resolve_factor_column(ftype: str, factors: list) -> str:
    """根据 factor type 确定列名"""
    for f in factors:
        if f["type"] == ftype:
            p = f.get("params", {})
            if ftype in ("MA", "EMA", "WMA"):
                return f'MA{p.get("period", 20)}'
            elif ftype == "MACD":
                return "DIF"
            elif ftype == "KDJ":
                return "K"
            elif ftype == "RSI":
                return f'RSI{p.get("period", 14)}'
            elif ftype == "BOLL":
                return "BB_UPPER"
            elif ftype == "ATR":
                return f'ATR{p.get("period", 14)}'
            elif ftype == "Volume_MA":
                return f'VolMA{p.get("period", 20)}'
            elif ftype == "OBV":
                return "OBV"
            elif ftype == "VWAP":
                return "VWAP"
    return ftype


def _build_factor_vars(factors: list) -> str:
    """为每个因子生成 _now/_prev 变量"""
    lines = []
    for f in factors:
        col = _resolve_factor_column(f["type"], factors)
        lines.append(f'        {col}_now = self.data["{col}"].iloc[idx]')
        lines.append(f'        {col}_prev = self.data["{col}"].iloc[idx - 1]')
    return "\n".join(lines)
