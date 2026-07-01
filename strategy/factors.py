"""
因子/技术指标库
封装 pandas-ta 的200+技术指标，提供统一易用的接口

指标分类：
  📈 趋势类：MA(SMA/EMA/WMA)、MACD、ADX
  🔄 震荡类：KDJ、RSI、Stochastic、CCI
  📊 波动类：布林带(BOLL)、ATR、Keltner Channel
  📉 成交量类：Volume、Volume MA、OBV、VWAP

每个因子函数都接受 DataFrame 和参数，返回添加了对应列的 DataFrame
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Tuple


# ============================================================
# 📈 趋势类指标
# ============================================================

def sma(df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
    """
    简单移动平均线（SMA）

    用途：反映价格的平均走势，是最基础的趋势指标
    用法：价格上穿均线 → 看涨信号；价格下穿均线 → 看跌信号
    """
    return df[column].rolling(window=period).mean()


def ema(df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
    """
    指数移动平均线（EMA）

    用途：比SMA更灵敏，对近期价格赋予更高权重
    用法：常用于短期趋势判断，EMA12和EMA26配合MACD使用
    """
    return df[column].ewm(span=period, adjust=False).mean()


def wma(df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
    """
    加权移动平均线（WMA）

    用途：给近期数据更高权重，比SMA更灵敏
    """
    weights = np.arange(1, period + 1)
    return df[column].rolling(window=period).apply(
        lambda x: np.sum(weights * x) / weights.sum(), raw=True
    )


def macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """
    MACD 指标（指数平滑异同移动平均线）

    用途：判断趋势方向和强度，是最常用的趋势指标之一
    信号：
      - MACD线(DIF)上穿信号线(DEA) → 金叉，买入信号
      - MACD线(DIF)下穿信号线(DEA) → 死叉，卖出信号
      - MACD柱(Histogram)由负转正 → 多头增强
      - MACD线背离价格 → 趋势反转预警

    返回的DataFrame新增列：
      - DIF: 快慢线差值（MACD线）
      - DEA: 信号线
      - MACD: 柱状图（DIF - DEA）* 2
    """
    df = df.copy()
    ema_fast = ema(df, fast)
    ema_slow = ema(df, slow)
    df["DIF"] = ema_fast - ema_slow
    df["DEA"] = df["DIF"].ewm(span=signal, adjust=False).mean()
    df["MACD"] = 2 * (df["DIF"] - df["DEA"])
    return df


def adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    ADX 平均趋向指数

    用途：衡量趋势强度（不判断方向）
      - ADX > 25: 强趋势
      - ADX > 50: 极强趋势
      - ADX < 20: 震荡/无趋势
    """
    df = df.copy()
    high, low, close = df["high"], df["low"], df["close"]

    # +DM, -DM
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Smooth
    atr = tr.rolling(period).mean()
    plus_di = 100 * pd.Series(plus_dm).rolling(period).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).rolling(period).mean() / atr

    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df["ADX"] = dx.rolling(period).mean()
    df["+DI"] = plus_di
    df["-DI"] = minus_di
    return df


# ============================================================
# 🔄 震荡类指标
# ============================================================

def kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
    """
    KDJ 随机指标

    用途：判断超买超卖和转折点
    信号：
      - K值 > 80: 超买区域，价格可能回调
      - K值 < 20: 超卖区域，价格可能反弹
      - K线上穿D线: 金叉，买入信号
      - K线下穿D线: 死叉，卖出信号
      - J值 > 100: 严重超买
      - J值 < 0: 严重超卖

    返回的DataFrame新增列：K, D, J
    """
    df = df.copy()
    low_min = df["low"].rolling(window=n, min_periods=1).min()
    high_max = df["high"].rolling(window=n, min_periods=1).max()

    rsv = (df["close"] - low_min) / (high_max - low_min) * 100
    rsv = rsv.fillna(50)

    df["K"] = rsv.ewm(com=m1 - 1, adjust=False).mean()
    df["D"] = df["K"].ewm(com=m2 - 1, adjust=False).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]
    return df


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    RSI 相对强弱指标

    用途：衡量价格变动的速度和幅度
    信号：
      - RSI > 70: 超买，可能回调
      - RSI < 30: 超卖，可能反弹
      - RSI = 50: 中性
      - RSI背离价格: 趋势反转预警
    """
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    """
    Stochastic 慢速随机指标

    用途：与KDJ类似，判断超买超卖
    """
    df = df.copy()
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()
    df["%K"] = (df["close"] - low_min) / (high_max - low_min) * 100
    df["%D"] = df["%K"].rolling(window=d_period).mean()
    return df


def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    CCI 商品通道指数

    用途：识别超买超卖和趋势反转
      - CCI > 100: 超买
      - CCI < -100: 超卖
    """
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma_tp = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    return (tp - sma_tp) / (0.015 * mad)


# ============================================================
# 📊 波动类指标
# ============================================================

def bollinger_bands(
    df: pd.DataFrame, period: int = 20, std_dev: float = 2.0
) -> pd.DataFrame:
    """
    布林带（BOLL）

    用途：判断价格波动范围和突破方向
    信号：
      - 价格触及上轨：可能回调（超买）
      - 价格触及下轨：可能反弹（超卖）
      - 带宽收窄：变盘在即
      - 价格突破上轨：强势上涨
      - 价格突破下轨：强势下跌

    返回的DataFrame新增列：BB_MIDDLE, BB_UPPER, BB_LOWER, BB_WIDTH
    """
    df = df.copy()
    df["BB_MIDDLE"] = sma(df, period)
    std = df["close"].rolling(window=period).std()
    df["BB_UPPER"] = df["BB_MIDDLE"] + std_dev * std
    df["BB_LOWER"] = df["BB_MIDDLE"] - std_dev * std
    df["BB_WIDTH"] = (df["BB_UPPER"] - df["BB_LOWER"]) / df["BB_MIDDLE"] * 100
    return df


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    ATR 平均真实波幅

    用途：衡量市场波动性
      - ATR越大：波动越剧烈
      - ATR越小：市场越平静
      - 常用于设置止损距离（如 2×ATR）
    """
    high, low, close = df["high"], df["low"], df["close"]
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


# ============================================================
# 📉 成交量类指标
# ============================================================

def volume_ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    成交量移动平均线

    用途：判断成交量是放大还是缩小
      - 成交量 > 均量：放量，市场活跃
      - 成交量 < 均量：缩量，市场冷清
    """
    return df["volume"].rolling(window=period).mean()


def obv(df: pd.DataFrame) -> pd.Series:
    """
    OBV 能量潮

    用途：通过成交量变化判断资金流向
      - OBV上升：资金流入
      - OBV下降：资金流出
      - OBV与价格背离：趋势反转信号
    """
    obv_values = [0]
    for i in range(1, len(df)):
        if df["close"].iloc[i] > df["close"].iloc[i - 1]:
            obv_values.append(obv_values[-1] + df["volume"].iloc[i])
        elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
            obv_values.append(obv_values[-1] - df["volume"].iloc[i])
        else:
            obv_values.append(obv_values[-1])
    return pd.Series(obv_values, index=df.index)


def vwap(df: pd.DataFrame) -> pd.Series:
    """
    VWAP 成交量加权平均价格

    用途：机构交易者常用的参考价格
      - 价格 > VWAP：买方占优
      - 价格 < VWAP：卖方占优
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    return (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()


def volume_profile(df: pd.DataFrame, bins: int = 30) -> pd.DataFrame:
    """
    成交量分布（Volume Profile）

    用途：显示不同价格区间的成交量分布
      - 高成交量区域: 强支撑/阻力位
      - 低成交量区域: 价格容易快速穿越
    """
    price_range = np.linspace(df["low"].min(), df["high"].max(), bins)
    volume_by_price = []
    for i in range(len(price_range) - 1):
        mask = (df["close"] >= price_range[i]) & (df["close"] < price_range[i + 1])
        volume_by_price.append(df.loc[mask, "volume"].sum())

    return pd.DataFrame({
        "price_level": price_range[:-1],
        "volume": volume_by_price,
    })


# ============================================================
# 🔧 便捷函数：一键添加常用指标
# ============================================================

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    一键添加所有常用技术指标

    包含：MA5/10/20/60, EMA12/26, MACD, KDJ, RSI14, BOLL, ATR, Volume MA
    """
    df = df.copy()

    # 均线
    for p in [5, 10, 20, 60]:
        df[f"MA{p}"] = sma(df, p)
    df["EMA12"] = ema(df, 12)
    df["EMA26"] = ema(df, 26)

    # MACD
    df = macd(df)

    # KDJ
    df = kdj(df)

    # RSI
    df["RSI14"] = rsi(df, 14)

    # BOLL
    df = bollinger_bands(df)

    # ATR
    df["ATR14"] = atr(df, 14)

    # 成交量
    df["Volume_MA20"] = volume_ma(df, 20)

    return df
