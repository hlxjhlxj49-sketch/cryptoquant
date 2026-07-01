"""
风险管理模块
提供仓位计算、止损止盈、风险控制等功能

核心功能：
  - 仓位大小计算（固定/百分比/凯利公式）
  - 止损/止盈（固定比例/追踪止损/ATR止损）
  - 单日最大亏损限制
  - 最大持仓数限制
"""

from typing import Optional, Dict
import pandas as pd
import numpy as np


class RiskManager:
    """
    风险管理器

    使用示例:
        rm = RiskManager(max_position_pct=20, stop_loss_pct=3, take_profit_pct=6)
        size = rm.calculate_position_size(capital=10000, price=50000)
        # size = 0.04 (用2000U在50000价位买入0.04 BTC)
    """

    def __init__(
        self,
        max_position_pct: float = 20.0,        # 单笔最大仓位 (%)
        max_daily_loss_pct: float = 5.0,       # 单日最大亏损 (%)
        stop_loss_pct: float = 3.0,            # 默认止损 (%)
        take_profit_pct: float = 6.0,          # 默认止盈 (%)
        trailing_stop_pct: float = 0.0,        # 追踪止损 (%)
        max_positions: int = 5,                # 最大同时持仓数
        use_kelly: bool = False,               # 是否使用凯利公式
        kelly_fraction: float = 0.5,           # 凯利分数（0.5=半凯利）
    ):
        self.max_position_pct = max_position_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.max_positions = max_positions
        self.use_kelly = use_kelly
        self.kelly_fraction = kelly_fraction

        # 日内追踪
        self.daily_start_equity = 0.0
        self.daily_pnl = 0.0
        self.positions_count = 0

    def reset_daily(self, current_equity: float):
        """重置日内追踪（每天开始时调用）"""
        self.daily_start_equity = current_equity
        self.daily_pnl = 0.0

    def calculate_position_size(
        self,
        capital: float,
        price: float,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
    ) -> float:
        """
        计算仓位大小

        参数:
            capital: 可用资金
            price: 当前价格
            win_rate: 胜率（凯利公式需要）
            avg_win: 平均盈利（凯利公式需要）
            avg_loss: 平均亏损（凯利公式需要）

        返回:
            建议的买入数量
        """
        if price <= 0 or capital <= 0:
            return 0.0

        if self.use_kelly and win_rate and avg_win and avg_loss and avg_loss > 0:
            # 凯利公式: f = (bp - q) / b
            # b = avg_win / avg_loss (盈亏比)
            # p = win_rate, q = 1 - p
            b = avg_win / avg_loss
            p = win_rate / 100
            q = 1 - p
            kelly_pct = (b * p - q) / b
            kelly_pct = max(0, kelly_pct) * self.kelly_fraction
            # 不超过最大仓位限制
            position_pct = min(kelly_pct * 100, self.max_position_pct)
        else:
            position_pct = self.max_position_pct

        # 计算购买数量
        position_value = capital * position_pct / 100
        size = position_value / price

        return size

    def check_stop_loss(self, entry_price: float, current_price: float, position_side: str = "long") -> bool:
        """
        检查是否触发止损

        参数:
            entry_price: 入场价格
            current_price: 当前价格
            position_side: 持仓方向 "long"/"short"

        返回:
            True 触发止损
        """
        if position_side == "long":
            loss_pct = (entry_price - current_price) / entry_price * 100
            return loss_pct >= self.stop_loss_pct
        else:
            loss_pct = (current_price - entry_price) / entry_price * 100
            return loss_pct >= self.stop_loss_pct

    def check_take_profit(self, entry_price: float, current_price: float, position_side: str = "long") -> bool:
        """
        检查是否触发止盈

        返回:
            True 触发止盈
        """
        if position_side == "long":
            profit_pct = (current_price - entry_price) / entry_price * 100
            return profit_pct >= self.take_profit_pct
        else:
            profit_pct = (entry_price - current_price) / entry_price * 100
            return profit_pct >= self.take_profit_pct

    def check_trailing_stop(
        self,
        highest_price: float,
        current_price: float,
        position_side: str = "long",
    ) -> bool:
        """
        检查追踪止损

        参数:
            highest_price: 持仓期间最高价（做多）/ 最低价（做空）
            current_price: 当前价格
            position_side: 持仓方向

        返回:
            True 触发追踪止损
        """
        if self.trailing_stop_pct <= 0:
            return False

        if position_side == "long":
            drawdown = (highest_price - current_price) / highest_price * 100
            return drawdown >= self.trailing_stop_pct
        else:
            drawdown = (current_price - highest_price) / highest_price * 100
            return drawdown >= self.trailing_stop_pct

    def check_daily_loss_limit(self, current_equity: float) -> bool:
        """
        检查是否达到单日最大亏损限制

        返回:
            True 达到限制，应停止交易
        """
        if self.daily_start_equity <= 0:
            return False

        daily_loss_pct = (self.daily_start_equity - current_equity) / self.daily_start_equity * 100
        return daily_loss_pct >= self.max_daily_loss_pct

    def can_open_position(self) -> bool:
        """检查是否可以开新仓位"""
        return self.positions_count < self.max_positions

    def calculate_atr_stop(
        self,
        df: pd.DataFrame,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
    ) -> float:
        """
        基于ATR计算止损价

        参数:
            df: K线DataFrame
            atr_period: ATR周期
            atr_multiplier: ATR倍数

        返回:
            止损价格
        """
        if df.empty or len(df) < atr_period:
            return 0.0

        # 计算ATR
        high, low, close = df["high"], df["low"], df["close"]
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(atr_period).mean().iloc[-1]

        current_price = close.iloc[-1]
        return current_price - atr * atr_multiplier
