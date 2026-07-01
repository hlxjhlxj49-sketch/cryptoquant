"""
模拟券商（Broker）
模拟真实交易所的交易执行，包括：
  - 现货和合约两种模式
  - 手续费计算（Maker/Taker）
  - 滑点模拟
  - 持仓/余额追踪
"""

from typing import Dict, Optional, List, Tuple
from datetime import datetime
import pandas as pd


class SimulatedBroker:
    """
    模拟券商

    使用示例:
        broker = SimulatedBroker(initial_capital=10000, mode="spot")
        broker.buy(price=50000, size=0.1, timestamp="2024-01-01 12:00")
        broker.sell(price=51000, size=0.1, timestamp="2024-01-01 13:00")
        print(broker.equity(51000))
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        mode: str = "spot",                # "spot" 现货 / "futures" 合约
        maker_fee: float = 0.001,          # 挂单手续费 0.1%
        taker_fee: float = 0.001,          # 吃单手续费 0.1%
        slippage: float = 0.0005,          # 滑点 0.05%
        min_position: float = 0.0001,      # 最小持仓
    ):
        """
        初始化模拟券商

        参数:
            initial_capital: 初始资金（USDT）
            mode: 交易模式 spot/futures
            maker_fee: 挂单手续费率
            taker_fee: 吃单手续费率
            slippage: 滑点比例
            min_position: 最小持仓数量
        """
        self.mode = mode
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage = slippage
        self.min_position = min_position

        # 账户状态
        self.initial_capital = initial_capital
        self.cash = initial_capital                # 可用现金
        self.position = 0.0                        # 持仓数量
        self.avg_entry_price = 0.0                 # 平均入场价
        self.total_fees = 0.0                      # 累计手续费

        # 交易记录
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []         # 权益曲线

    def reset(self):
        """重置账户状态"""
        self.cash = self.initial_capital
        self.position = 0.0
        self.avg_entry_price = 0.0
        self.total_fees = 0.0
        self.trades = []
        self.equity_curve = []

    def buy(self, price: float, size: float, timestamp=None) -> Optional[Dict]:
        """
        买入/开多

        参数:
            price: 成交价格
            size: 买入数量（币本位）
            timestamp: 成交时间

        返回:
            交易记录，资金不足返回None
        """
        if size <= 0:
            return None

        # 计算滑点后的实际成交价（买入时略高）
        actual_price = price * (1 + self.slippage)

        # 计算成本（含手续费）
        cost = actual_price * size
        fee = cost * self.taker_fee
        total_cost = cost + fee

        # 检查资金
        if total_cost > self.cash:
            return None  # 资金不足

        # 更新账户
        self.cash -= total_cost
        self.total_fees += fee

        # 更新持仓均价
        if self.position > 0:
            total_value = self.position * self.avg_entry_price + size * actual_price
            self.position += size
            self.avg_entry_price = total_value / self.position
        else:
            self.position = size
            self.avg_entry_price = actual_price

        # 记录交易
        trade = {
            "time": timestamp or datetime.now(),
            "side": "buy",
            "price": actual_price,
            "size": size,
            "cost": total_cost,
            "fee": fee,
            "equity": self.equity(price),  # 用原始价格计算权益
        }
        self.trades.append(trade)

        return trade

    def sell(self, price: float, size: float, timestamp=None) -> Optional[Dict]:
        """
        卖出/平多

        参数:
            price: 成交价格
            size: 卖出数量（None则全部卖出）
            timestamp: 成交时间

        返回:
            交易记录，持仓不足返回None
        """
        if size <= 0:
            return None

        if size > self.position:
            size = self.position  # 最多卖出全部持仓

        if size < self.min_position:
            return None

        # 计算滑点后的实际成交价（卖出时略低）
        actual_price = price * (1 - self.slippage)

        # 计算收入（扣除手续费）
        revenue = actual_price * size
        fee = revenue * self.taker_fee
        net_revenue = revenue - fee

        # 计算该笔交易的盈亏
        cost_basis = self.avg_entry_price * size
        pnl = net_revenue - cost_basis

        # 更新账户
        self.cash += net_revenue
        self.position -= size
        self.total_fees += fee

        # 如果清仓，重置均价
        if self.position < self.min_position:
            self.position = 0.0
            self.avg_entry_price = 0.0

        # 记录交易
        trade = {
            "time": timestamp or datetime.now(),
            "side": "sell",
            "price": actual_price,
            "size": size,
            "revenue": net_revenue,
            "fee": fee,
            "pnl": pnl,
            "equity": self.equity(price),
        }
        self.trades.append(trade)

        return trade

    def close_position(self, price: float, timestamp=None) -> Optional[Dict]:
        """平仓全部持仓"""
        if self.position <= 0:
            return None
        return self.sell(price, self.position, timestamp)

    def equity(self, current_price: float) -> float:
        """
        计算当前总权益

        参数:
            current_price: 当前市场价格

        返回:
            总权益 = 现金 + 持仓市值
        """
        position_value = self.position * current_price
        return self.cash + position_value

    def pnl(self, current_price: float) -> float:
        """
        当前浮动盈亏

        返回:
            浮动盈亏金额
        """
        return self.equity(current_price) - self.initial_capital

    def pnl_pct(self, current_price: float) -> float:
        """
        当前浮动盈亏百分比

        返回:
            盈亏百分比
        """
        return (self.equity(current_price) - self.initial_capital) / self.initial_capital * 100

    def drawdown(self, peak_equity: float, current_price: float) -> float:
        """
        计算当前回撤

        参数:
            peak_equity: 历史最高权益
            current_price: 当前价格

        返回:
            回撤百分比（正数）
        """
        current = self.equity(current_price)
        if peak_equity <= 0:
            return 0.0
        return (peak_equity - current) / peak_equity * 100

    def record_equity(self, timestamp, current_price: float):
        """记录权益曲线数据点"""
        self.equity_curve.append({
            "time": timestamp,
            "equity": self.equity(current_price),
            "cash": self.cash,
            "position": self.position,
            "price": current_price,
        })

    def get_stats(self) -> Dict:
        """获取账户统计信息"""
        return {
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "position": self.position,
            "total_fees": self.total_fees,
            "trade_count": len(self.trades),
            "mode": self.mode,
        }

    def to_equity_df(self) -> pd.DataFrame:
        """将权益曲线转为DataFrame"""
        if not self.equity_curve:
            return pd.DataFrame()
        df = pd.DataFrame(self.equity_curve)
        df.set_index("time", inplace=True)
        return df

    def to_trades_df(self) -> pd.DataFrame:
        """将交易记录转为DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)
