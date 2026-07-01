"""
因子模板库
预定义的策略模板，用户可以通过自然语言描述匹配对应模板

模板分类：
  📈 均线类：金叉死叉、均线斜率、多空排列
  📊 成交量类：放量突破、缩量筑底、量价背离
  🔄 KDJ类：超买超卖、金叉死叉、钝化信号
  🧩 组合类：多指标组合策略
"""

from typing import Dict, List, Optional


# ============================================================
# 模板数据结构
# ============================================================

FACTOR_TEMPLATES = []


def register_template(
    name: str,
    category: str,
    description: str,
    keywords: List[str],
    code_template: str,
    default_params: Optional[Dict] = None,
):
    """
    注册一个策略模板

    参数:
        name: 模板名称（中文）
        category: 分类（均线/成交量/KDJ/组合）
        description: 一句话描述
        keywords: 匹配关键词列表
        code_template: 策略代码模板（Python代码字符串，使用{param}占位）
        default_params: 默认参数值
    """
    FACTOR_TEMPLATES.append({
        "name": name,
        "category": category,
        "description": description,
        "keywords": keywords,
        "code_template": code_template,
        "default_params": default_params or {},
    })


# ============================================================
# 📈 均线类模板
# ============================================================

register_template(
    name="双均线金叉死叉",
    category="均线",
    description="当短期均线上穿长期均线时买入，下穿时卖出",
    keywords=["均线", "金叉", "死叉", "上穿", "下穿", "MA", "移动平均", "交叉"],
    default_params={"fast_period": 5, "slow_period": 20},
    code_template='''"""
{name} - 自动生成的策略
描述: {description}
参数: 快线={fast_period}, 慢线={slow_period}
"""

from strategy.base import Strategy
from strategy.factors import sma
import pandas as pd


class {class_name}(Strategy):
    """{name}"""

    def __init__(self):
        super().__init__(name="{name}")
        self.fast = {fast_period}    # 短期均线周期
        self.slow = {slow_period}    # 长期均线周期

    def on_start(self):
        """计算均线"""
        self.data[f"MA{{self.fast}}"] = sma(self.data, self.fast)
        self.data[f"MA{{self.slow}}"] = sma(self.data, self.slow)

    def on_bar(self, bar):
        idx = self.current_index
        if idx < self.slow + 1:
            return

        # 获取均线值（当前和前一根）
        fast_now = self.data[f"MA{{self.fast}}"].iloc[idx]
        fast_prev = self.data[f"MA{{self.fast}}"].iloc[idx - 1]
        slow_now = self.data[f"MA{{self.slow}}"].iloc[idx]
        slow_prev = self.data[f"MA{{self.slow}}"].iloc[idx - 1]

        # 金叉买入
        if fast_prev <= slow_prev and fast_now > slow_now:
            if not self.has_position():
                size = self.portfolio["cash"] / bar["close"] * 0.95
                self.buy(size=size)

        # 死叉卖出
        elif fast_prev >= slow_prev and fast_now < slow_now:
            if self.has_position():
                self.close_position()
'''
)


register_template(
    name="均线多头排列",
    category="均线",
    description="当多条均线呈现多头排列（短期>中期>长期）时买入",
    keywords=["多头排列", "均线排列", "多头", "上涨趋势", "均线向上"],
    default_params={"periods": "5,10,20,60"},
    code_template='''"""
{name} - 自动生成的策略
描述: {description}
参数: 均线周期={periods}
"""

from strategy.base import Strategy
from strategy.factors import sma
import pandas as pd


class {class_name}(Strategy):
    """{name}"""

    def __init__(self):
        super().__init__(name="{name}")
        self.periods = [{periods}]    # 均线周期列表

    def on_start(self):
        """计算多条均线"""
        for p in self.periods:
            self.data[f"MA{{p}}"] = sma(self.data, p)

    def on_bar(self, bar):
        idx = self.current_index
        if idx < max(self.periods) + 1:
            return

        # 检查多头排列：MA5 > MA10 > MA20 > MA60
        is_bullish = True
        for i in range(len(self.periods) - 1):
            ma_short = self.data[f"MA{{self.periods[i]}}"].iloc[idx]
            ma_long = self.data[f"MA{{self.periods[i+1]}}"].iloc[idx]
            if ma_short <= ma_long:
                is_bullish = False
                break

        if is_bullish and not self.has_position():
            size = self.portfolio["cash"] / bar["close"] * 0.95
            self.buy(size=size)

        elif not is_bullish and self.has_position():
            self.close_position()
'''
)


register_template(
    name="均线斜率突破",
    category="均线",
    description="当均线斜率为正且加速上扬时买入",
    keywords=["斜率", "均线加速", "趋势加速", "均线斜率"],
    default_params={"ma_period": 20, "slope_period": 5},
    code_template='''"""
{name} - 自动生成的策略
描述: {description}
参数: 均线周期={ma_period}, 斜率计算周期={slope_period}
"""

from strategy.base import Strategy
from strategy.factors import sma
import pandas as pd
import numpy as np


class {class_name}(Strategy):
    """{name}"""

    def __init__(self):
        super().__init__(name="{name}")
        self.ma_period = {ma_period}
        self.slope_period = {slope_period}

    def on_start(self):
        """计算均线和斜率"""
        self.data[f"MA{{self.ma_period}}"] = sma(self.data, self.ma_period)
        # 斜率 = 当前MA值 - N天前MA值
        self.data["MA_slope"] = self.data[f"MA{{self.ma_period}}"].diff(self.slope_period)

    def on_bar(self, bar):
        idx = self.current_index
        if idx < self.ma_period + self.slope_period + 1:
            return

        slope = self.data["MA_slope"].iloc[idx]
        prev_slope = self.data["MA_slope"].iloc[idx - 1]

        # 斜率为正且加速 → 买入
        if slope > 0 and slope > prev_slope:
            if not self.has_position():
                size = self.portfolio["cash"] / bar["close"] * 0.95
                self.buy(size=size)

        # 斜率转负 → 卖出
        elif slope < 0 and self.has_position():
            self.close_position()
'''
)


# ============================================================
# 📊 成交量类模板
# ============================================================

register_template(
    name="放量突破",
    category="成交量",
    description="当价格突破阻力位且成交量显著放大时买入",
    keywords=["放量", "突破", "成交量放大", "放量上涨", "量增价涨"],
    default_params={"breakout_period": 20, "volume_multiple": 1.5},
    code_template='''"""
{name} - 自动生成的策略
描述: {description}
参数: 突破周期={breakout_period}, 放量倍数={volume_multiple}
"""

from strategy.base import Strategy
import pandas as pd


class {class_name}(Strategy):
    """{name}"""

    def __init__(self):
        super().__init__(name="{name}")
        self.breakout_period = {breakout_period}     # 突破周期
        self.volume_multiple = {volume_multiple}     # 放量倍数

    def on_start(self):
        """计算指标"""
        self.data["high_N"] = self.data["high"].rolling(self.breakout_period).max().shift(1)
        self.data["vol_ma"] = self.data["volume"].rolling(20).mean()

    def on_bar(self, bar):
        idx = self.current_index
        if idx < self.breakout_period + 20:
            return

        price = bar["close"]
        high_n = self.data["high_N"].iloc[idx]
        vol_ma = self.data["vol_ma"].iloc[idx]

        # 价格突破 + 放量 → 买入
        if price > high_n and bar["volume"] > vol_ma * self.volume_multiple:
            if not self.has_position():
                size = self.portfolio["cash"] / price * 0.95
                self.buy(size=size)

        # 跌破20日均线 → 止损卖出
        ma20 = self.data["close"].rolling(20).mean().iloc[idx]
        if price < ma20 and self.has_position():
            self.close_position()
'''
)


register_template(
    name="缩量筑底",
    category="成交量",
    description="成交量持续萎缩后突然放量，视为底部信号买入",
    keywords=["缩量", "筑底", "地量", "缩量反弹", "底部放量"],
    default_params={"shrink_period": 10, "surge_multiple": 2.0},
    code_template='''"""
{name} - 自动生成的策略
描述: {description}
参数: 缩量周期={shrink_period}, 放量倍数={surge_multiple}
"""

from strategy.base import Strategy
import pandas as pd


class {class_name}(Strategy):
    """{name}"""

    def __init__(self):
        super().__init__(name="{name}")
        self.shrink_period = {shrink_period}
        self.surge_multiple = {surge_multiple}

    def on_start(self):
        """计算指标"""
        self.data["vol_ma20"] = self.data["volume"].rolling(20).mean()

    def on_bar(self, bar):
        idx = self.current_index
        if idx < self.shrink_period + 20:
            return

        # 前N天成交量持续低于均量（缩量）
        recent_vol = self.data["volume"].iloc[idx - self.shrink_period:idx]
        recent_vol_ma = self.data["vol_ma20"].iloc[idx - self.shrink_period:idx]
        is_shrinking = (recent_vol < recent_vol_ma * 0.7).all()

        # 今天突然放量 + 价格收阳
        today_vol = bar["volume"]
        vol_ma = self.data["vol_ma20"].iloc[idx]
        is_surge = today_vol > vol_ma * self.surge_multiple
        is_green = bar["close"] > bar["open"]

        if is_shrinking and is_surge and is_green:
            if not self.has_position():
                size = self.portfolio["cash"] / bar["close"] * 0.8
                self.buy(size=size)

        # 盈利5%止盈
        if self.has_position():
            entry_price = self.portfolio["trades"][-1]["price"]
            if bar["close"] > entry_price * 1.05:
                self.close_position()
'''
)


register_template(
    name="量价背离",
    category="成交量",
    description="价格创新高但成交量缩小，视为顶部背离信号卖出",
    keywords=["量价背离", "背离", "顶背离", "缩量上涨", "量价"],
    default_params={"price_period": 20, "volume_period": 20},
    code_template='''"""
{name} - 自动生成的策略
描述: {description}
参数: 价格周期={price_period}, 成交量周期={volume_period}
"""

from strategy.base import Strategy
import pandas as pd


class {class_name}(Strategy):
    """{name}"""

    def __init__(self):
        super().__init__(name="{name}")
        self.price_period = {price_period}
        self.volume_period = {volume_period}

    def on_start(self):
        """计算指标"""
        self.data["price_ma"] = self.data["close"].rolling(self.price_period).mean()
        self.data["vol_ma"] = self.data["volume"].rolling(self.volume_period).mean()

    def on_bar(self, bar):
        idx = self.current_index
        if idx < max(self.price_period, self.volume_period) + 1:
            return

        # 价格创新高但成交量未创新高 → 顶背离
        price_new_high = bar["close"] > self.data["high"].iloc[idx - self.price_period:idx].max()
        vol_prev_max = self.data["volume"].iloc[idx - self.volume_period:idx].max()
        vol_no_new_high = bar["volume"] < vol_prev_max * 0.8

        if price_new_high and vol_no_new_high and self.has_position():
            self.close_position()

        # 价格RSI超卖 → 买入
        delta = self.data["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[idx]

        if current_rsi < 30 and not self.has_position():
            size = self.portfolio["cash"] / bar["close"] * 0.5
            self.buy(size=size)
'''
)


# ============================================================
# 🔄 KDJ类模板
# ============================================================

register_template(
    name="KDJ金叉死叉",
    category="KDJ",
    description="当KDJ的K线上穿D线（金叉）时买入，下穿（死叉）时卖出",
    keywords=["KDJ", "KDJ金叉", "KDJ死叉", "随机指标", "K上穿D"],
    default_params={"n": 9, "m1": 3, "m2": 3},
    code_template='''"""
{name} - 自动生成的策略
描述: {description}
参数: KDJ周期=({n},{m1},{m2})
"""

from strategy.base import Strategy
from strategy.factors import kdj
import pandas as pd


class {class_name}(Strategy):
    """{name}"""

    def __init__(self):
        super().__init__(name="{name}")
        self.n = {n}   # RSV周期
        self.m1 = {m1}  # K平滑
        self.m2 = {m2}  # D平滑

    def on_start(self):
        """计算KDJ指标"""
        self.data = kdj(self.data, self.n, self.m1, self.m2)

    def on_bar(self, bar):
        idx = self.current_index
        if idx < self.n + self.m1 + self.m2:
            return

        k_now = self.data["K"].iloc[idx]
        k_prev = self.data["K"].iloc[idx - 1]
        d_now = self.data["D"].iloc[idx]
        d_prev = self.data["D"].iloc[idx - 1]
        j_now = self.data["J"].iloc[idx]

        # KDJ金叉：K上穿D，且在超卖区域更好
        if k_prev <= d_prev and k_now > d_now:
            if not self.has_position():
                size = self.portfolio["cash"] / bar["close"] * 0.8
                self.buy(size=size)

        # KDJ死叉：K下穿D
        elif k_prev >= d_prev and k_now < d_now:
            if self.has_position():
                self.close_position()

        # J值极端信号 → 增强版交易
        if j_now < 0 and not self.has_position():
            size = self.portfolio["cash"] / bar["close"] * 0.3
            self.buy(size=size)
'''
)


register_template(
    name="KDJ超买超卖",
    category="KDJ",
    description="KDJ进入超卖区（K<20）买入，超买区（K>80）卖出",
    keywords=["KDJ超买", "KDJ超卖", "超买超卖", "KD超买", "KD超卖"],
    default_params={"oversold": 20, "overbought": 80},
    code_template='''"""
{name} - 自动生成的策略
描述: {description}
参数: 超卖线={oversold}, 超买线={overbought}
"""

from strategy.base import Strategy
from strategy.factors import kdj
import pandas as pd


class {class_name}(Strategy):
    """{name}"""

    def __init__(self):
        super().__init__(name="{name}")
        self.oversold = {oversold}
        self.overbought = {overbought}

    def on_start(self):
        """计算KDJ指标"""
        self.data = kdj(self.data)

    def on_bar(self, bar):
        idx = self.current_index
        if idx < 12:
            return

        k = self.data["K"].iloc[idx]
        d = self.data["D"].iloc[idx]
        j = self.data["J"].iloc[idx]

        # K值和D值都在超卖区 → 买入
        if k < self.oversold and d < self.oversold:
            if not self.has_position():
                size = self.portfolio["cash"] / bar["close"] * 0.5
                self.buy(size=size)

        # K值和D值都在超买区 → 卖出
        elif k > self.overbought and d > self.overbought:
            if self.has_position():
                self.close_position()
'''
)


register_template(
    name="KDJ钝化",
    category="KDJ",
    description="KDJ高位钝化时警惕反转，低位钝化时关注反弹机会",
    keywords=["KDJ钝化", "KD钝化", "钝化", "高位钝化", "低位钝化"],
    default_params={"overbought": 80, "oversold": 20, "钝化周期": 5},
    code_template='''"""
{name} - 自动生成的策略
描述: {description}
参数: 超买线={overbought}, 超卖线={oversold}, 钝化周期={钝化周期}
"""

from strategy.base import Strategy
from strategy.factors import kdj
import pandas as pd


class {class_name}(Strategy):
    """{name}"""

    def __init__(self):
        super().__init__(name="{name}")
        self.overbought = {overbought}
        self.oversold = {oversold}
        self.stall_period = {钝化周期}

    def on_start(self):
        """计算KDJ指标"""
        self.data = kdj(self.data)

    def on_bar(self, bar):
        idx = self.current_index
        if idx < self.stall_period + 12:
            return

        # 高位钝化检测：连续N根K线K值都在超买区
        k_values = self.data["K"].iloc[idx - self.stall_period + 1:idx + 1]
        is_overbought_stall = (k_values > self.overbought).all()

        # 低位钝化检测：连续N根K线K值都在超卖区
        is_oversold_stall = (k_values < self.oversold).all()

        # 高位钝化后K值下穿D值 → 卖出
        if is_overbought_stall and self.has_position():
            k_now = self.data["K"].iloc[idx]
            d_now = self.data["D"].iloc[idx]
            k_prev = self.data["K"].iloc[idx - 1]
            d_prev = self.data["D"].iloc[idx - 1]
            if k_prev >= d_prev and k_now < d_now:
                self.close_position()

        # 低位钝化后K值上穿D值 → 买入
        if is_oversold_stall and not self.has_position():
            k_now = self.data["K"].iloc[idx]
            d_now = self.data["D"].iloc[idx]
            k_prev = self.data["K"].iloc[idx - 1]
            d_prev = self.data["D"].iloc[idx - 1]
            if k_prev <= d_prev and k_now > d_now:
                size = self.portfolio["cash"] / bar["close"] * 0.8
                self.buy(size=size)
'''
)


# ============================================================
# 🧩 组合类模板
# ============================================================

register_template(
    name="MACD+KDJ共振",
    category="组合",
    description="MACD金叉且KDJ也在低位金叉时买入，双重确认提高胜率",
    keywords=["共振", "MACD金叉", "KDJ金叉", "双金叉", "双重确认"],
    default_params={"macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
    code_template='''"""
{name} - 自动生成的策略
描述: {description}
参数: MACD=({macd_fast},{macd_slow},{macd_signal}), KDJ=(9,3,3)
"""

from strategy.base import Strategy
from strategy.factors import macd, kdj
import pandas as pd


class {class_name}(Strategy):
    """{name}"""

    def __init__(self):
        super().__init__(name="{name}")

    def on_start(self):
        """计算MACD和KDJ"""
        self.data = macd(self.data, {macd_fast}, {macd_slow}, {macd_signal})
        self.data = kdj(self.data)

    def on_bar(self, bar):
        idx = self.current_index
        if idx < 30:
            return

        # MACD金叉：DIF上穿DEA
        dif_now = self.data["DIF"].iloc[idx]
        dif_prev = self.data["DIF"].iloc[idx - 1]
        dea_now = self.data["DEA"].iloc[idx]
        dea_prev = self.data["DEA"].iloc[idx - 1]
        macd_golden = dif_prev <= dea_prev and dif_now > dea_now

        # KDJ金叉：K上穿D，且在低位
        k_now = self.data["K"].iloc[idx]
        k_prev = self.data["K"].iloc[idx - 1]
        d_now = self.data["D"].iloc[idx]
        d_prev = self.data["D"].iloc[idx - 1]
        kdj_golden = k_prev <= d_prev and k_now > d_now and k_now < 50

        # 双金叉共振 → 买入
        if macd_golden and kdj_golden:
            if not self.has_position():
                size = self.portfolio["cash"] / bar["close"] * 0.9
                self.buy(size=size)

        # 任一死叉 → 卖出
        macd_death = dif_prev >= dea_prev and dif_now < dea_now
        kdj_death = k_prev >= d_prev and k_now < d_now

        if (macd_death or kdj_death) and self.has_position():
            self.close_position()
'''
)


register_template(
    name="均线+成交量确认",
    category="组合",
    description="均线金叉且成交量放大时买入，双重确认避免假突破",
    keywords=["均线放量", "金叉放量", "量价配合", "放量金叉"],
    default_params={"fast": 5, "slow": 20, "vol_multiple": 1.5},
    code_template='''"""
{name} - 自动生成的策略
描述: {description}
参数: 快线={fast}, 慢线={slow}, 放量={vol_multiple}倍
"""

from strategy.base import Strategy
from strategy.factors import sma
import pandas as pd


class {class_name}(Strategy):
    """{name}"""

    def __init__(self):
        super().__init__(name="{name}")
        self.fast = {fast}
        self.slow = {slow}
        self.vol_multiple = {vol_multiple}

    def on_start(self):
        """计算指标"""
        self.data[f"MA{{self.fast}}"] = sma(self.data, self.fast)
        self.data[f"MA{{self.slow}}"] = sma(self.data, self.slow)
        self.data["vol_ma20"] = self.data["volume"].rolling(20).mean()

    def on_bar(self, bar):
        idx = self.current_index
        if idx < self.slow + 20:
            return

        # 金叉检测
        fast_now = self.data[f"MA{{self.fast}}"].iloc[idx]
        fast_prev = self.data[f"MA{{self.fast}}"].iloc[idx - 1]
        slow_now = self.data[f"MA{{self.slow}}"].iloc[idx]
        slow_prev = self.data[f"MA{{self.slow}}"].iloc[idx - 1]
        golden_cross = fast_prev <= slow_prev and fast_now > slow_now

        # 放量检测
        vol_ma = self.data["vol_ma20"].iloc[idx]
        is_surge = bar["volume"] > vol_ma * self.vol_multiple

        # 金叉 + 放量 → 买入
        if golden_cross and is_surge:
            if not self.has_position():
                size = self.portfolio["cash"] / bar["close"] * 0.9
                self.buy(size=size)

        # 死叉 → 卖出
        death_cross = fast_prev >= slow_prev and fast_now < slow_now
        if death_cross and self.has_position():
            self.close_position()
'''
)


# ============================================================
# 查询函数
# ============================================================

def get_all_templates() -> List[Dict]:
    """获取所有策略模板"""
    return FACTOR_TEMPLATES


def get_templates_by_category(category: str) -> List[Dict]:
    """按分类获取模板"""
    return [t for t in FACTOR_TEMPLATES if t["category"] == category]


def search_templates(query: str) -> List[Dict]:
    """
    根据用户输入搜索匹配的模板

    参数:
        query: 用户输入的自然语言描述

    返回:
        匹配的模板列表（按匹配度排序）
    """
    query_lower = query.lower()
    scored = []

    for template in FACTOR_TEMPLATES:
        score = 0
        # 关键词匹配
        for keyword in template["keywords"]:
            if keyword.lower() in query_lower:
                score += 1

        # 名称直接匹配
        if template["name"] in query:
            score += 3

        # 分类匹配
        if template["category"] in query:
            score += 2

        if score > 0:
            scored.append((score, template))

    # 按分数降序排列
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored]
