"""
模拟交易执行器（Paper Trading）
使用实时行情，虚拟资金模拟真实交易

与回测的区别：
  - 回测：用历史数据一次性跑完
  - 模拟交易：用实时数据，逐笔执行，模拟真实交易环境
"""

import pandas as pd
from typing import Dict, Optional, List, Callable
from datetime import datetime
from data.fetcher import DataFetcher
from execution.risk import RiskManager
from strategy.base import Strategy
from utils.logger import log


class PaperTrader:
    """
    模拟交易执行器

    使用示例:
        trader = PaperTrader(strategy=my_strategy, initial_capital=10000)
        trader.start()
    """

    def __init__(
        self,
        strategy: Strategy,
        initial_capital: float = 10000.0,
        exchange_name: str = "binance",
        risk_manager: Optional[RiskManager] = None,
    ):
        """
        初始化模拟交易器

        参数:
            strategy: 策略实例
            initial_capital: 初始资金
            exchange_name: 交易所（用于获取实时行情）
            risk_manager: 风险管理器
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.risk_manager = risk_manager or RiskManager()

        # 账户状态
        self.cash = initial_capital
        self.position = 0.0
        self.avg_entry_price = 0.0
        self.total_fees = 0.0

        # 交易记录
        self.trades: List[Dict] = []
        self.equity_history: List[Dict] = []

        # 行情获取
        self.fetcher = DataFetcher(exchange_name=exchange_name)

        # 运行状态
        self.is_running = False
        self.symbol = ""
        self.timeframe = "1h"

    def start(self, symbol: str = "BTC/USDT", timeframe: str = "1h"):
        """
        启动模拟交易

        参数:
            symbol: 交易对
            timeframe: K线周期
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.is_running = True

        # 初始化策略
        self.strategy._reset_portfolio(self.initial_capital)

        log.info(f"📊 模拟交易启动: {symbol} {timeframe}, 初始资金=${self.initial_capital:,.0f}")

    def stop(self):
        """停止模拟交易"""
        self.is_running = False
        log.info(f"📊 模拟交易停止: 最终权益=${self.equity():,.2f}")

    def on_new_bar(self, bar: pd.Series) -> Optional[Dict]:
        """
        处理新K线（由外部定时调用）

        参数:
            bar: 新K线数据

        返回:
            如果有新交易，返回交易记录
        """
        if not self.is_running:
            return None

        # 更新策略数据
        if self.strategy.data is None:
            self.strategy.data = pd.DataFrame([bar])
        else:
            self.strategy.data = pd.concat([self.strategy.data, pd.DataFrame([bar])])
        self.strategy.current_index = len(self.strategy.data) - 1

        # 执行策略逻辑
        try:
            self.strategy.on_bar(bar)
        except Exception as e:
            log.error(f"策略执行错误: {e}")
            return None

        # 同步交易
        result = self._sync_with_strategy(bar)
        return result

    def _sync_with_strategy(self, bar: pd.Series) -> Optional[Dict]:
        """同步策略信号到模拟账户"""
        strategy_trades = self.strategy.portfolio["trades"]
        if not strategy_trades:
            return None

        last_trade = strategy_trades[-1]
        broker_count = len(self.trades)

        # 只处理新交易
        if len(strategy_trades) <= broker_count:
            return None

        new_trades = strategy_trades[broker_count:]
        result = None

        for trade in new_trades:
            price = trade.get("price", bar["close"])
            size = trade.get("size", 0)
            side = trade.get("side", "buy")

            # 模拟滑点和手续费
            slippage = 0.0005
            fee_rate = 0.001

            if side == "buy":
                actual_price = price * (1 + slippage)
                cost = actual_price * size
                fee = cost * fee_rate

                if cost + fee <= self.cash:
                    self.cash -= (cost + fee)
                    self.position += size
                    self.avg_entry_price = actual_price
                    self.total_fees += fee

                    result = {
                        "time": bar.name if hasattr(bar, "name") else datetime.now(),
                        "side": "buy",
                        "price": actual_price,
                        "size": size,
                        "fee": fee,
                        "equity": self.equity(price),
                    }
                    self.trades.append(result)
                    log.info(f"✅ 模拟买入: {size:.4f} @ ${actual_price:,.2f}")

            elif side == "sell":
                actual_price = price * (1 - slippage)
                revenue = actual_price * size
                fee = revenue * fee_rate

                if size <= self.position:
                    self.cash += (revenue - fee)
                    self.position -= size
                    self.total_fees += fee

                    result = {
                        "time": bar.name if hasattr(bar, "name") else datetime.now(),
                        "side": "sell",
                        "price": actual_price,
                        "size": size,
                        "fee": fee,
                        "equity": self.equity(price),
                    }
                    self.trades.append(result)
                    log.info(f"✅ 模拟卖出: {size:.4f} @ ${actual_price:,.2f}")

        # 同步策略状态
        self.strategy.portfolio["cash"] = self.cash
        self.strategy.portfolio["position"] = self.position

        return result

    def equity(self, current_price: float = 0) -> float:
        """当前总权益"""
        return self.cash + self.position * current_price

    def get_status(self, current_price: float) -> Dict:
        """获取当前状态"""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "is_running": self.is_running,
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "position": self.position,
            "avg_entry_price": self.avg_entry_price,
            "equity": self.equity(current_price),
            "pnl": self.equity(current_price) - self.initial_capital,
            "pnl_pct": (self.equity(current_price) - self.initial_capital) / self.initial_capital * 100,
            "total_fees": self.total_fees,
            "trade_count": len(self.trades),
        }

    def get_trades_df(self) -> pd.DataFrame:
        """获取交易记录DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)
