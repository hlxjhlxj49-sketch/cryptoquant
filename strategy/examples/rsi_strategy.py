"""
RSI 均值回归策略

策略逻辑：
  买入信号：RSI 低于超卖线（默认30）时买入，等待回归
  卖出信号：RSI 高于超买线（默认70）时卖出

特点：
  - 均值回归型策略，适合震荡市场
  - 在趋势市场可能逆势亏损
  - 建议配合趋势过滤器使用

参数：
  rsi_period: RSI计算周期（默认14）
  oversold: 超卖线（默认30，低于此值买入）
  overbought: 超买线（默认70，高于此值卖出）
"""

from strategy.base import Strategy
from strategy.factors import rsi
import pandas as pd


class RSIStrategy(Strategy):
    """RSI均值回归策略"""

    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
    ):
        """
        初始化策略

        参数:
            rsi_period: RSI周期
            oversold: 超卖阈值
            overbought: 超买阈值
        """
        super().__init__(name=f"RSI均值回归 RSI{rsi_period}")
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def on_start(self):
        """策略启动：计算RSI"""
        self.data["RSI"] = rsi(self.data, self.rsi_period)

    def on_bar(self, bar: pd.Series) -> None:
        """每根K线回调：检查RSI超买超卖"""
        idx = self.current_index

        # 需要足够数据
        if idx < self.rsi_period + 1:
            return

        current_rsi = self.data["RSI"].iloc[idx]

        if pd.isna(current_rsi):
            return

        # --- 买入信号：RSI进入超卖区域 ---
        if current_rsi < self.oversold and not self.has_position():
            # 用一半资金买入
            size = (self.portfolio["cash"] * 0.5) / bar["close"]
            if size > 0:
                self.buy(size=size, price=bar["close"])

        # --- 卖出信号：RSI进入超买区域 ---
        elif current_rsi > self.overbought and self.has_position():
            self.close_position(price=bar["close"])

    def on_finish(self):
        """策略结束：输出统计"""
        trades = len(self.portfolio["trades"])
        final_equity = self.equity()
        initial = self.portfolio.get("initial_capital", 10000)
        pnl_pct = (final_equity - initial) / initial * 100
        print(f"[{self.name}] 交易次数: {trades}, "
              f"最终收益: {pnl_pct:+.2f}%")
