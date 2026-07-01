"""
双均线交叉策略（Golden Cross / Death Cross）

策略逻辑：
  买入信号：短期均线（MA5）上穿长期均线（MA20）→ 金叉
  卖出信号：短期均线（MA5）下穿长期均线（MA20）→ 死叉

特点：
  - 最经典的趋势跟踪策略
  - 适合有明显趋势的市场
  - 震荡市场容易产生假信号

参数：
  fast_period: 短期均线周期（默认5）
  slow_period: 长期均线周期（默认20）
"""

from strategy.base import Strategy
from strategy.factors import sma
import pandas as pd


class MACrossStrategy(Strategy):
    """双均线交叉策略"""

    def __init__(self, fast_period: int = 5, slow_period: int = 20):
        """
        初始化策略

        参数:
            fast_period: 快线周期（默认5）
            slow_period: 慢线周期（默认20）
        """
        super().__init__(name=f"双均线交叉 MA{fast_period}/{slow_period}")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def on_start(self):
        """策略启动：计算均线"""
        # 计算短期和长期均线
        self.data[f"MA{self.fast_period}"] = sma(self.data, self.fast_period)
        self.data[f"MA{self.slow_period}"] = sma(self.data, self.slow_period)

    def on_bar(self, bar: pd.Series) -> None:
        """每根K线回调：检查金叉/死叉信号"""
        idx = self.current_index

        # 需要足够的历史数据
        if idx < self.slow_period + 1:
            return

        # 获取当前和前一根K线的均线值
        fast_now = self.data[f"MA{self.fast_period}"].iloc[idx]
        fast_prev = self.data[f"MA{self.fast_period}"].iloc[idx - 1]
        slow_now = self.data[f"MA{self.slow_period}"].iloc[idx]
        slow_prev = self.data[f"MA{self.slow_period}"].iloc[idx - 1]

        # --- 买入信号：金叉（快线上穿慢线）---
        if fast_prev <= slow_prev and fast_now > slow_now:
            if not self.has_position():
                # 全仓买入
                size = self.portfolio["cash"] / bar["close"] * 0.95  # 留5%手续费余量
                if size > 0:
                    self.buy(size=size, price=bar["close"])

        # --- 卖出信号：死叉（快线下穿慢线）---
        elif fast_prev >= slow_prev and fast_now < slow_now:
            if self.has_position():
                self.close_position(price=bar["close"])

    def on_finish(self):
        """策略结束：输出统计"""
        trades = len(self.portfolio["trades"])
        final_equity = self.equity()
        initial = self.portfolio.get("initial_capital", 10000)
        pnl_pct = (final_equity - initial) / initial * 100
        print(f"[{self.name}] 交易次数: {trades}, "
              f"最终收益: {pnl_pct:+.2f}%")
