"""
信号生成器
提供各种交易信号的检测和生成

信号类型：
  🔀 交叉信号：金叉/死叉
  📊 阈值信号：超买/超卖
  📈 形态信号：突破、背离
  🧩 组合信号：多条件合并
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple


# ============================================================
# 🔀 交叉信号
# ============================================================

def crossover(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    检测 上穿（金叉）

    参数:
        series1: 快线（如DIF、K值）
        series2: 慢线（如DEA、D值）

    返回:
        bool Series，True表示series1上穿series2

    示例:
        golden_cross = crossover(df["MA5"], df["MA20"])  # MA5上穿MA20
    """
    return (series1 > series2) & (series1.shift(1) <= series2.shift(1))


def crossunder(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    检测 下穿（死叉）

    参数:
        series1: 快线
        series2: 慢线

    返回:
        bool Series，True表示series1下穿series2

    示例:
        death_cross = crossunder(df["MA5"], df["MA20"])  # MA5下穿MA20
    """
    return (series1 < series2) & (series1.shift(1) >= series2.shift(1))


# ============================================================
# 📊 阈值信号
# ============================================================

def overbought(series: pd.Series, threshold: float = 80) -> pd.Series:
    """
    检测超买区域

    用于 RSI > 70, KDJ K值 > 80 等场景
    """
    return series > threshold


def oversold(series: pd.Series, threshold: float = 20) -> pd.Series:
    """
    检测超卖区域

    用于 RSI < 30, KDJ K值 < 20 等场景
    """
    return series < threshold


def above_level(series: pd.Series, level: float) -> pd.Series:
    """检测指标在某个水平之上"""
    return series > level


def below_level(series: pd.Series, level: float) -> pd.Series:
    """检测指标在某个水平之下"""
    return series < level


# ============================================================
# 📈 趋势/形态信号
# ============================================================

def breakout_high(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    检测突破N日最高价

    用途：识别向上突破信号
    """
    high_n = df["high"].rolling(window=period).max().shift(1)
    return df["close"] > high_n


def breakdown_low(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    检测跌破N日最低价

    用途：识别向下突破信号
    """
    low_n = df["low"].rolling(window=period).min().shift(1)
    return df["close"] < low_n


def volume_surge(df: pd.DataFrame, multiple: float = 1.5) -> pd.Series:
    """
    检测成交量放大

    参数:
        multiple: 放大倍数（相对于20日均量）

    用途：放量突破确认
    """
    vol_ma = df["volume"].rolling(window=20).mean()
    return df["volume"] > vol_ma * multiple


def ma_bullish_alignment(df: pd.DataFrame, periods: Tuple[int, ...] = (5, 10, 20, 60)) -> bool:
    """
    检测均线多头排列（短期均线 > 长期均线）

    用途：确认上升趋势
    """
    mas = [f"MA{p}" for p in periods]
    for col in mas:
        if col not in df.columns:
            return False

    # 检查短期 > 长期（如 MA5 > MA10 > MA20 > MA60）
    for i in range(len(mas) - 1):
        if df[mas[i]].iloc[-1] <= df[mas[i + 1]].iloc[-1]:
            return False
    return True


def ma_bearish_alignment(df: pd.DataFrame, periods: Tuple[int, ...] = (5, 10, 20, 60)) -> bool:
    """
    检测均线空头排列（短期均线 < 长期均线）

    用途：确认下降趋势
    """
    mas = [f"MA{p}" for p in periods]
    for col in mas:
        if col not in df.columns:
            return False

    for i in range(len(mas) - 1):
        if df[mas[i]].iloc[-1] >= df[mas[i + 1]].iloc[-1]:
            return False
    return True


# ============================================================
# 🧩 组合信号生成器
# ============================================================

class SignalGenerator:
    """
    信号生成器 - 组合多种条件生成交易信号

    使用示例:
        gen = SignalGenerator(df)
        buy_signal = gen.buy_when(
            gen.crossover("MA5", "MA20"),
            gen.oversold("K", 20),
            gen.volume_surge(1.5),
        )
    """

    def __init__(self, df: pd.DataFrame):
        """
        初始化信号生成器

        参数:
            df: 包含技术指标的DataFrame
        """
        self.df = df

    def crossover(self, col1: str, col2: str) -> pd.Series:
        """上穿信号"""
        if col1 not in self.df.columns or col2 not in self.df.columns:
            return pd.Series([False] * len(self.df))
        return crossover(self.df[col1], self.df[col2])

    def crossunder(self, col1: str, col2: str) -> pd.Series:
        """下穿信号"""
        if col1 not in self.df.columns or col2 not in self.df.columns:
            return pd.Series([False] * len(self.df))
        return crossunder(self.df[col1], self.df[col2])

    def overbought(self, col: str, threshold: float = 80) -> pd.Series:
        """超买信号"""
        if col not in self.df.columns:
            return pd.Series([False] * len(self.df))
        return overbought(self.df[col], threshold)

    def oversold(self, col: str, threshold: float = 20) -> pd.Series:
        """超卖信号"""
        if col not in self.df.columns:
            return pd.Series([False] * len(self.df))
        return oversold(self.df[col], threshold)

    def volume_surge(self, multiple: float = 1.5) -> pd.Series:
        """放量信号"""
        return volume_surge(self.df, multiple)

    def breakout(self, period: int = 20) -> pd.Series:
        """突破高点"""
        return breakout_high(self.df, period)

    @staticmethod
    def buy_when(*conditions: pd.Series) -> pd.Series:
        """
        组合买入信号（所有条件同时满足）

        示例:
            buy = SignalGenerator.buy_when(
                golden_cross,  # MA金叉
                low_rsi,       # RSI超卖
                high_vol,      # 放量
            )
        """
        result = conditions[0].copy()
        for cond in conditions[1:]:
            result = result & cond
        return result

    @staticmethod
    def sell_when(*conditions: pd.Series) -> pd.Series:
        """
        组合卖出信号（任一条件满足）

        示例:
            sell = SignalGenerator.sell_when(
                death_cross,    # MA死叉
                high_rsi,       # RSI超买
            )
        """
        result = conditions[0].copy()
        for cond in conditions[1:]:
            result = result | cond
        return result
