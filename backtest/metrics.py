"""
绩效指标计算模块
独立的指标计算函数，可单独使用或配合回测引擎

参考标准：
  - 夏普比率 > 1: 良好
  - 夏普比率 > 2: 优秀
  - 最大回撤 < 20%: 可接受
  - 卡尔玛比率 > 1: 良好
  - 胜率 > 40%: 正常（趋势策略通常胜率不高但盈亏比高）
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple


def calculate_returns(equity_curve: pd.Series) -> pd.Series:
    """计算每期收益率"""
    return equity_curve.pct_change().dropna()


def total_return(equity_curve: pd.Series) -> float:
    """
    总收益率

    返回: 百分比 (如 15.5 表示 15.5%)
    """
    if len(equity_curve) < 2:
        return 0.0
    return (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100


def annual_return(equity_curve: pd.Series, periods_per_year: int = 365) -> float:
    """
    年化收益率

    参数:
        equity_curve: 权益曲线
        periods_per_year: 每年的周期数（日线365，小时线8760）

    返回: 百分比
    """
    if len(equity_curve) < 2:
        return 0.0

    total_ret = equity_curve.iloc[-1] / equity_curve.iloc[0]
    years = len(equity_curve) / periods_per_year
    if years <= 0:
        return 0.0

    return (total_ret ** (1 / years) - 1) * 100


def max_drawdown(equity_curve: pd.Series) -> Tuple[float, int]:
    """
    最大回撤

    返回: (最大回撤百分比, 最长回撤持续期)

    示例:
        dd, duration = max_drawdown(equity_curve)
        # dd = 15.2 (15.2% 最大回撤)
        # duration = 120 (持续120个周期)
    """
    if len(equity_curve) < 2:
        return 0.0, 0

    peak = equity_curve.expanding(min_periods=1).max()
    drawdown = (equity_curve - peak) / peak * 100
    max_dd = abs(drawdown.min())

    # 回撤持续期：权益低于峰值的最长连续周期数
    in_dd = equity_curve < peak
    max_duration = 0
    current_duration = 0

    for is_dd in in_dd:
        if is_dd:
            current_duration += 1
            max_duration = max(max_duration, current_duration)
        else:
            current_duration = 0

    return max_dd, max_duration


def sharpe_ratio(returns: pd.Series, periods_per_year: int = 365, risk_free: float = 0.0) -> float:
    """
    夏普比率

    公式: (年化收益 - 无风险利率) / 年化波动率

    参考:
      > 1.0: 良好
      > 2.0: 优秀
      > 3.0: 极佳
    """
    if len(returns) < 2 or returns.std() == 0:
        return 0.0

    excess = returns.mean() - risk_free / periods_per_year
    return excess / returns.std() * np.sqrt(periods_per_year)


def sortino_ratio(returns: pd.Series, periods_per_year: int = 365, risk_free: float = 0.0) -> float:
    """
    索提诺比率（只考虑下行风险）

    公式: (年化收益 - 无风险利率) / 下行年化波动率

    比夏普比率更合理：上涨的波动不是风险
    """
    if len(returns) < 2:
        return 0.0

    downside = returns[returns < 0]
    if len(downside) < 2 or downside.std() == 0:
        return 0.0

    excess = returns.mean() - risk_free / periods_per_year
    return excess / downside.std() * np.sqrt(periods_per_year)


def calmar_ratio(annual_ret: float, max_dd: float) -> float:
    """
    卡尔玛比率

    公式: 年化收益率 / 最大回撤

    参考:
      > 1.0: 良好
      > 2.0: 优秀
      > 3.0: 极佳
    """
    if max_dd == 0:
        return 0.0
    return annual_ret / max_dd


def win_rate(trades: pd.DataFrame) -> float:
    """
    胜率

    参数:
        trades: 交易记录DataFrame（需包含 pnl 列）

    返回: 百分比
    """
    if trades.empty or "pnl" not in trades.columns:
        return 0.0
    sells = trades[trades["side"] == "sell"]
    if sells.empty:
        return 0.0
    return len(sells[sells["pnl"] > 0]) / len(sells) * 100


def profit_factor(trades: pd.DataFrame) -> float:
    """
    盈亏比

    公式: 总盈利 / 总亏损

    参考:
      > 1.5: 良好
      > 2.0: 优秀
    """
    if trades.empty or "pnl" not in trades.columns:
        return 0.0
    sells = trades[trades["side"] == "sell"]
    if sells.empty:
        return 0.0

    total_profit = sells[sells["pnl"] > 0]["pnl"].sum()
    total_loss = abs(sells[sells["pnl"] < 0]["pnl"].sum())

    if total_loss == 0:
        return float("inf") if total_profit > 0 else 0.0

    return total_profit / total_loss


def average_trade(trades: pd.DataFrame) -> Tuple[float, float]:
    """
    平均盈利和平均亏损

    返回: (平均盈利, 平均亏损)
    """
    if trades.empty or "pnl" not in trades.columns:
        return 0.0, 0.0

    sells = trades[trades["side"] == "sell"]
    wins = sells[sells["pnl"] > 0]["pnl"]
    losses = sells[sells["pnl"] < 0]["pnl"]

    avg_win = wins.mean() if len(wins) > 0 else 0.0
    avg_loss = losses.mean() if len(losses) > 0 else 0.0

    return avg_win, avg_loss


def monthly_returns_table(equity_curve: pd.Series) -> pd.DataFrame:
    """
    月度收益表（热力图数据）

    返回: DataFrame，行为年，列为月，值为月收益率(%)
    """
    if len(equity_curve) < 2:
        return pd.DataFrame()

    # 按月重采样
    monthly = equity_curve.resample("ME").last()
    monthly_ret = monthly.pct_change().dropna() * 100

    # 转为年×月矩阵
    df = pd.DataFrame({
        "year": monthly_ret.index.year,
        "month": monthly_ret.index.month,
        "return": monthly_ret.values,
    })

    pivot = df.pivot(index="year", columns="month", values="return")
    pivot.columns = ["1月", "2月", "3月", "4月", "5月", "6月",
                     "7月", "8月", "9月", "10月", "11月", "12月"][:len(pivot.columns)]

    return pivot


def comprehensive_metrics(
    equity_curve: pd.Series,
    trades: pd.DataFrame,
    periods_per_year: int = 365,
) -> Dict:
    """
    一键计算所有绩效指标

    返回:
        包含所有指标的字典
    """
    returns = calculate_returns(equity_curve)

    ann_ret = annual_return(equity_curve, periods_per_year)
    max_dd_val, max_dd_dur = max_drawdown(equity_curve)

    return {
        "total_return": total_return(equity_curve),
        "annual_return": ann_ret,
        "max_drawdown": max_dd_val,
        "max_drawdown_duration": max_dd_dur,
        "sharpe_ratio": sharpe_ratio(returns, periods_per_year),
        "sortino_ratio": sortino_ratio(returns, periods_per_year),
        "calmar_ratio": calmar_ratio(ann_ret, max_dd_val),
        "win_rate": win_rate(trades),
        "profit_factor": profit_factor(trades),
        "total_trades": len(trades[trades["side"] == "sell"]) if not trades.empty else 0,
    }
