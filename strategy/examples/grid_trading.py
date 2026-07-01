"""
网格交易策略

策略逻辑：
  在设定价格区间内，等距挂买单和卖单。
  价格下跌到网格线 → 买入
  价格上涨到网格线 → 卖出
  每格赚取固定差价利润。

特点：
  - 适合震荡市场，不适合单边趋势
  - 无需预测方向，赚取波动利润
  - 需要有足够资金覆盖网格

参数：
  grid_count: 网格数量（默认10）
  price_range_pct: 网格总区间百分比（默认10%，即上下各5%）
  per_grid_size: 每格买入金额（USDT，默认1000）
"""

from strategy.base import Strategy
import pandas as pd
import numpy as np


class GridTradingStrategy(Strategy):
    """网格交易策略"""

    def __init__(
        self,
        grid_count: int = 10,
        price_range_pct: float = 10.0,
        per_grid_size: float = 1000.0,
    ):
        """
        初始化策略

        参数:
            grid_count: 网格数量
            price_range_pct: 价格区间百分比
            per_grid_size: 每格买入金额
        """
        super().__init__(name=f"网格交易 {grid_count}格")
        self.grid_count = grid_count
        self.price_range_pct = price_range_pct
        self.per_grid_size = per_grid_size

        # 内部状态
        self.grid_prices = []          # 网格价格线（从低到高）
        self.grid_filled = []          # 每格是否已买入
        self.base_price = 0.0          # 基准价格

    def on_start(self):
        """策略启动：计算网格价格"""
        # 以第一根K线的收盘价作为基准
        if len(self.data) > 0:
            self.base_price = self.data.iloc[0]["close"]
        else:
            self.base_price = 10000  # 默认价格

        # 计算网格区间 [lower, upper]
        half_range = self.price_range_pct / 2 / 100
        lower = self.base_price * (1 - half_range)
        upper = self.base_price * (1 + half_range)

        # 等距生成网格线
        self.grid_prices = np.linspace(lower, upper, self.grid_count + 2)[1:-1]
        self.grid_filled = [False] * len(self.grid_prices)

    def on_bar(self, bar: pd.Series) -> None:
        """每根K线回调：检查网格触发"""
        current_price = bar["close"]

        for i, grid_price in enumerate(self.grid_prices):
            # 价格跌破网格线且该格未买入 → 买入
            if current_price <= grid_price and not self.grid_filled[i]:
                size = self.per_grid_size / current_price
                if size > 0 and self.portfolio["cash"] >= self.per_grid_size:
                    trade = self.buy(size=size, price=current_price)
                    if trade:
                        self.grid_filled[i] = True

            # 价格涨回网格线上方且该格已买入 → 卖出（盈利）
            elif current_price > grid_price and self.grid_filled[i]:
                # 计算该格对应的持仓量
                sell_size = self.per_grid_size / grid_price
                if sell_size <= self.portfolio["position"]:
                    self.sell(size=sell_size, price=current_price)
                    self.grid_filled[i] = False

    def on_finish(self):
        """策略结束：输出统计"""
        trades = len(self.portfolio["trades"])
        final_equity = self.equity()
        initial = self.portfolio.get("initial_capital", 10000)
        pnl_pct = (final_equity - initial) / initial * 100
        filled_count = sum(self.grid_filled)

        print(f"[{self.name}] 网格数: {self.grid_count}, "
              f"已成交格: {filled_count}, "
              f"交易次数: {trades}, "
              f"最终收益: {pnl_pct:+.2f}%")
