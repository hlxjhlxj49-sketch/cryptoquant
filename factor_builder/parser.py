"""
自然语言描述解析器
解析用户输入的交易策略描述，提取关键信息

解析内容：
  - 技术指标名称（MA、MACD、KDJ、RSI、成交量等）
  - 数值参数（周期、阈值等）
  - 条件关系（上穿、下穿、大于、小于、和、或）
  - 交易方向（买入、卖出、做多、做空）
  - 时间框架（分钟、小时、日线等）
"""

import re
from typing import Dict, List, Optional, Tuple


class StrategyDescription:
    """策略描述解析结果"""

    def __init__(self):
        self.indicators: List[Dict] = []     # 检测到的指标列表
        self.conditions: List[Dict] = []     # 条件列表
        self.actions: List[Dict] = []        # 交易动作列表
        self.raw_text: str = ""              # 原始输入文本


# ============================================================
# 关键词定义
# ============================================================

# 指标关键词映射
INDICATOR_KEYWORDS = {
    "MA": ["均线", "移动平均", "MA", "ma", "SMA", "平均线", "日均线"],
    "EMA": ["指数均线", "EMA", "ema", "指数移动平均"],
    "MACD": ["MACD", "macd", "异同移动平均", "DIF", "DEA"],
    "KDJ": ["KDJ", "kdj", "随机指标", "K值", "D值", "J值", "KD线"],
    "RSI": ["RSI", "rsi", "相对强弱", "强弱指标"],
    "BOLL": ["布林", "布林带", "BOLL", "boll", "保利加"],
    "VOLUME": ["成交量", "量能", "放量", "缩量", "volume", "VOL"],
    "ATR": ["ATR", "atr", "真实波幅", "平均波幅"],
}

# 条件关键词映射
CONDITION_KEYWORDS = {
    "CROSSOVER": ["上穿", "金叉", "突破", "上破", "cross above"],
    "CROSSUNDER": ["下穿", "死叉", "跌破", "下破", "cross below"],
    "GREATER": ["大于", "高于", "超过", ">", "大于等于", ">=", "不低于"],
    "LESS": ["小于", "低于", "不足", "<", "小于等于", "<=", "不超过"],
    "AND": ["并且", "同时", "且", "AND", "and", "&", "和", "以及"],
    "OR": ["或者", "或", "OR", "or", "|", "之一"],
}

# 交易动作关键词
ACTION_KEYWORDS = {
    "BUY": ["买入", "做多", "开多", "买", "long", "buy", "入场"],
    "SELL": ["卖出", "做空", "开空", "卖", "short", "sell", "平仓", "平多", "离场"],
    "STOP_LOSS": ["止损", "亏损", "止损线"],
    "TAKE_PROFIT": ["止盈", "盈利", "止盈线", "目标价"],
}

# 时间框架关键词
TIMEFRAME_KEYWORDS = {
    "1m": ["1分钟", "1min", "一分钟"],
    "5m": ["5分钟", "5min", "五分钟"],
    "15m": ["15分钟", "15min"],
    "1h": ["1小时", "1h", "一小时", "小时线", "小时"],
    "4h": ["4小时", "4h", "四小时"],
    "1d": ["日线", "日", "1d", "天", "每天"],
}


def extract_numbers(text: str) -> List[int]:
    """
    从文本中提取所有数字

    返回:
        数字列表
    """
    # 匹配所有整数
    numbers = re.findall(r'\d+', text)
    return [int(n) for n in numbers]


def parse_indicators(text: str) -> List[Dict]:
    """
    解析文本中提到的技术指标

    返回:
        指标列表，每个包含 name, params
    """
    found = []

    for indicator_name, keywords in INDICATOR_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                # 检查是否已添加
                if not any(i["name"] == indicator_name for i in found):
                    # 提取该指标附近的数字作为参数
                    found.append({
                        "name": indicator_name,
                        "keyword": kw,
                        "params": [],
                    })
                break

    return found


def parse_conditions(text: str) -> List[Dict]:
    """
    解析条件关系

    返回:
        条件列表
    """
    conditions = []

    for cond_name, keywords in CONDITION_KEYWORDS.items():
        for kw in keywords:
            pos = text.find(kw)
            if pos >= 0:
                conditions.append({
                    "type": cond_name,
                    "keyword": kw,
                    "position": pos,
                })
                break

    # 按位置排序
    conditions.sort(key=lambda x: x["position"])
    return conditions


def parse_actions(text: str) -> List[Dict]:
    """
    解析交易动作

    返回:
        动作列表
    """
    actions = []

    for action_name, keywords in ACTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                if not any(a["type"] == action_name for a in actions):
                    actions.append({"type": action_name, "keyword": kw})
                break

    return actions


def parse_timeframe(text: str) -> Optional[str]:
    """
    解析时间框架

    返回:
        标准时间框架标识，如 "1h"
    """
    for tf, keywords in TIMEFRAME_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return tf
    return None


def parse(text: str) -> StrategyDescription:
    """
    完整解析用户输入

    参数:
        text: 用户输入的自然语言策略描述

    返回:
        StrategyDescription 对象

    示例:
        result = parse("当5日均线上穿20日均线时买入，RSI超过70时卖出")
        # result.indicators: [{"name": "MA", ...}, {"name": "RSI", ...}]
        # result.conditions: [{"type": "CROSSOVER", ...}, ...]
        # result.actions: [{"type": "BUY", ...}, {"type": "SELL", ...}]
    """
    desc = StrategyDescription()
    desc.raw_text = text

    desc.indicators = parse_indicators(text)
    desc.conditions = parse_conditions(text)
    desc.actions = parse_actions(text)

    return desc


def extract_params(text: str, indicator_name: str) -> Dict:
    """
    从描述中提取指标参数

    例如 "5日均线上穿20日均线" → {"fast": 5, "slow": 20}

    参数:
        text: 用户输入文本
        indicator_name: 指标名称

    返回:
        参数字典
    """
    params = {}
    numbers = extract_numbers(text)

    if indicator_name == "MA":
        if len(numbers) >= 2:
            params["fast_period"] = min(numbers[0], numbers[1])
            params["slow_period"] = max(numbers[0], numbers[1])
        elif len(numbers) == 1:
            params["fast_period"] = numbers[0]
            params["slow_period"] = 20

    elif indicator_name == "MACD":
        if len(numbers) >= 3:
            params["macd_fast"] = numbers[0]
            params["macd_slow"] = numbers[1]
            params["macd_signal"] = numbers[2]
        else:
            params["macd_fast"] = 12
            params["macd_slow"] = 26
            params["macd_signal"] = 9

    elif indicator_name == "KDJ":
        if len(numbers) >= 3:
            params["n"] = numbers[0]
            params["m1"] = numbers[1]
            params["m2"] = numbers[2]
        else:
            params["n"] = 9
            params["m1"] = 3
            params["m2"] = 3

    elif indicator_name == "RSI":
        if len(numbers) >= 1:
            params["rsi_period"] = numbers[0]
        else:
            params["rsi_period"] = 14
        # 超买超卖
        if len(numbers) >= 2:
            params["oversold"] = min(numbers[0], numbers[1]) if len(numbers) >= 2 else 30
            params["overbought"] = max(numbers[0], numbers[1]) if len(numbers) >= 2 else 70

    elif indicator_name == "VOLUME":
        if len(numbers) >= 1:
            params["volume_multiple"] = float(numbers[0]) if numbers[0] > 1 else float(numbers[0])
        else:
            params["volume_multiple"] = 1.5

    return params
