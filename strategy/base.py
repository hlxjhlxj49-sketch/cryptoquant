"""
策略基类
所有交易策略的父类，提供极简的API接口

用户只需要继承此基类，实现以下核心方法即可：
  - on_bar(bar):     每根K线回调（编写策略逻辑的地方）
  - buy() / sell():  交易操作

也可以重写以下方法实现更复杂的需求：
  - on_start():      策略启动时执行一次
  - on_tick(tick):   每笔成交回调（需要tick数据）
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime
import pandas as pd


class Strategy(ABC):
    """
    交易策略基类

    使用示例:
        class MyStrategy(Strategy):
            def on_bar(self, bar):
                # 当5日均线上穿20日均线时买入
                if self.ma5[-1] > self.ma20[-1] and self.ma5[-2] <= self.ma20[-2]:
                    self.buy(size=1.0)

            def on_start(self):
                print("策略启动！")
    """

    def __init__(self, name: str = "Strategy"):
        """
        初始化策略

        参数:
            name: 策略名称
        """
        self.name = name                    # 策略名称
        self.data: pd.DataFrame = None      # 当前K线数据（DataFrame）
        self.portfolio: Dict = {            # 持仓信息
            "cash": 10000.0,                # 现金
            "position": 0.0,                # 持仓数量
            "position_value": 0.0,          # 持仓市值
            "equity": 10000.0,              # 总权益
            "trades": [],                   # 交易记录
        }
        self.indicators: Dict = {}          # 自定义指标存储
        self.params: Dict = {}              # 策略参数
        self.current_index: int = 0         # 当前K线索引
        self.is_running: bool = False       # 是否正在运行

    # ===== 用户需要实现的回调方法 =====

    @abstractmethod
    def on_bar(self, bar: pd.Series) -> None:
        """
        【核心方法】每根K线回调

        参数:
            bar: 当前K线数据（包含 open, high, low, close, volume）
                 可以通过 bar["close"] 获取收盘价

        示例:
            def on_bar(self, bar):
                # 简单的买入逻辑
                if not self.has_position():
                    self.buy(size=1.0)
        """
        pass

    def on_start(self) -> None:
        """
        策略启动时执行（可重写）
        用于初始化指标、设置参数等
        """
        pass

    def on_finish(self) -> None:
        """
        策略结束时执行（可重写）
        用于输出统计信息等
        """
        pass

    def on_tick(self, tick: Dict) -> None:
        """
        每笔成交回调（可重写，需要tick级别数据）

        参数:
            tick: 成交数据 {"price": ..., "amount": ..., "side": "buy"/"sell"}
        """
        pass

    # ===== 交易操作方法 =====

    def buy(self, size: float = 1.0, price: Optional[float] = None) -> Optional[Dict]:
        """
        买入/开多

        参数:
            size: 买入数量（对于合约，表示张数）
            price: 指定价格（None则以当前收盘价成交）

        返回:
            交易记录字典，如果资金不足返回None
        """
        if price is None:
            price = self.current_price()

        cost = size * price
        if cost > self.portfolio["cash"]:
            return None  # 资金不足

        self.portfolio["cash"] -= cost
        self.portfolio["position"] += size

        trade = {
            "time": self.current_time(),
            "side": "buy",
            "price": price,
            "size": size,
            "cost": cost,
            "equity": self.equity(),
        }
        self.portfolio["trades"].append(trade)
        return trade

    def sell(self, size: Optional[float] = None, price: Optional[float] = None) -> Optional[Dict]:
        """
        卖出/平多

        参数:
            size: 卖出数量（None则卖出全部持仓）
            price: 指定价格（None则以当前收盘价成交）

        返回:
            交易记录字典，如果持仓不足返回None
        """
        if price is None:
            price = self.current_price()

        if size is None:
            size = self.portfolio["position"]  # 默认全部卖出

        if size > self.portfolio["position"]:
            return None  # 持仓不足

        revenue = size * price
        self.portfolio["cash"] += revenue
        self.portfolio["position"] -= size

        trade = {
            "time": self.current_time(),
            "side": "sell",
            "price": price,
            "size": size,
            "revenue": revenue,
            "equity": self.equity(),
        }
        self.portfolio["trades"].append(trade)
        return trade

    def close_position(self, price: Optional[float] = None) -> Optional[Dict]:
        """
        平仓（卖出全部持仓）
        等价于 sell(size=None)
        """
        return self.sell(size=None, price=price)

    # ===== 信息查询方法 =====

    def current_price(self) -> float:
        """获取当前收盘价"""
        if self.data is not None and len(self.data) > 0:
            return float(self.data.iloc[self.current_index]["close"])
        return 0.0

    def current_bar(self) -> pd.Series:
        """获取当前K线数据"""
        if self.data is not None and len(self.data) > 0:
            return self.data.iloc[self.current_index]
        return pd.Series()

    def current_time(self) -> datetime:
        """获取当前K线时间"""
        if self.data is not None and len(self.data) > 0:
            return self.data.index[self.current_index]
        return datetime.now()

    def has_position(self) -> bool:
        """是否有持仓"""
        return self.portfolio["position"] > 0

    def position_size(self) -> float:
        """当前持仓数量"""
        return self.portfolio["position"]

    def cash(self) -> float:
        """当前现金"""
        return self.portfolio["cash"]

    def equity(self) -> float:
        """当前总权益（现金 + 持仓市值）"""
        pos_value = self.portfolio["position"] * self.current_price()
        return self.portfolio["cash"] + pos_value

    def pnl(self) -> float:
        """当前浮动盈亏"""
        return self.equity() - self.portfolio.get("initial_capital", self.portfolio["cash"])

    def pnl_pct(self) -> float:
        """当前浮动盈亏百分比"""
        initial = self.portfolio.get("initial_capital", self.portfolio["cash"])
        if initial == 0:
            return 0.0
        return (self.equity() - initial) / initial * 100

    # ===== 指标查询方法（在on_bar中使用） =====

    def ma(self, period: int = 20, offset: int = -1) -> float:
        """
        获取移动平均线值

        参数:
            period: 均线周期
            offset: 偏移（-1表示当前值，-2表示前一根K线的值）

        返回:
            均线值
        """
        col = f"MA{period}"
        if col in self.data.columns:
            idx = self.current_index + offset
            if 0 <= idx < len(self.data):
                val = self.data.iloc[idx][col]
                return float(val) if pd.notna(val) else 0.0
        return 0.0

    def get_indicator(self, name: str, offset: int = -1) -> float:
        """
        获取自定义指标值

        参数:
            name: 指标名称（列名）
            offset: 偏移

        返回:
            指标值
        """
        if name in self.data.columns:
            idx = self.current_index + offset
            if 0 <= idx < len(self.data):
                val = self.data.iloc[idx][name]
                return float(val) if pd.notna(val) else 0.0
        return 0.0

    # ===== 内部方法（框架调用） =====

    def _set_data(self, df: pd.DataFrame) -> None:
        """设置K线数据（框架内部使用）"""
        self.data = df

    def _set_params(self, params: Dict) -> None:
        """设置策略参数（框架内部使用）"""
        self.params = params

    def _reset_portfolio(self, initial_capital: float = 10000.0) -> None:
        """重置账户（框架内部使用）"""
        self.portfolio = {
            "cash": initial_capital,
            "position": 0.0,
            "position_value": 0.0,
            "equity": initial_capital,
            "trades": [],
            "initial_capital": initial_capital,
        }
