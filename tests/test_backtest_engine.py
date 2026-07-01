"""
回测引擎核心流程测试

使用合成数据验证 BacktestEngine 的关键路径：
- 空数据处理
- 无交易策略
- 简单买入持有
- 指标计算正确性
- 绩效指标计算
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from strategy.base import Strategy
from strategy.factors import sma
from backtest.engine import BacktestEngine, BacktestResult
from backtest.metrics import (
    total_return, sharpe_ratio, max_drawdown,
    win_rate, profit_factor, comprehensive_metrics,
)


# ---- 辅助：创建合成K线数据 ----

def make_ohlcv(n_bars: int = 500, trend: float = 0.0, volatility: float = 0.5) -> pd.DataFrame:
    """
    生成合成K线数据

    参数:
        n_bars: K线数量
        trend: 价格趋势（正=上涨，负=下跌）
        volatility: 日波动率
    """
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="1h")
    close = 100.0
    data = []
    for i in range(n_bars):
        close = close * (1 + trend / n_bars + np.random.normal(0, volatility / 100))
        open_ = close * (1 + np.random.normal(0, 0.001))
        high = max(open_, close) * (1 + abs(np.random.normal(0, 0.003)))
        low = min(open_, close) * (1 - abs(np.random.normal(0, 0.003)))
        volume = abs(np.random.normal(1000, 200))
        data.append([open_, high, low, close, volume])

    return pd.DataFrame(data, columns=["open", "high", "low", "close", "volume"], index=dates)


# ---- 测试策略 ----

class NoTradeStrategy(Strategy):
    """永不交易的策略"""
    def __init__(self):
        super().__init__(name="NoTrade")
    def on_bar(self, bar):
        pass


class BuyAndHoldStrategy(Strategy):
    """买入持有策略——第一根K线全仓买入"""
    def __init__(self):
        super().__init__(name="BuyHold")
        self.bought = False

    def on_bar(self, bar):
        if not self.bought and self.current_index > 0:
            size = self.portfolio["cash"] / bar["close"] * 0.95
            self.buy(size=size, price=bar["close"])
            self.bought = True


class MAStrategy(Strategy):
    """双均线策略——用于验证指标计算"""
    def __init__(self, fast=5, slow=20):
        super().__init__(name=f"MA{fast}/{slow}")
        self.fast = fast
        self.slow = slow

    def on_start(self):
        self.data[f"MA{self.fast}"] = sma(self.data, self.fast)
        self.data[f"MA{self.slow}"] = sma(self.data, self.slow)

    def on_bar(self, bar):
        idx = self.current_index
        if idx < self.slow + 1:
            return
        fast_now = self.data[f"MA{self.fast}"].iloc[idx]
        slow_now = self.data[f"MA{self.slow}"].iloc[idx]
        fast_prev = self.data[f"MA{self.fast}"].iloc[idx - 1]
        slow_prev = self.data[f"MA{self.slow}"].iloc[idx - 1]

        if fast_prev <= slow_prev and fast_now > slow_now and not self.has_position():
            size = self.portfolio["cash"] / bar["close"] * 0.95
            self.buy(size=size, price=bar["close"])
        elif fast_prev >= slow_prev and fast_now < slow_now and self.has_position():
            self.close_position(price=bar["close"])


# ============================================================
# 测试用例
# ============================================================

class TestBacktestEngine:

    def test_empty_data(self):
        """空数据应返回空结果"""
        engine = BacktestEngine(NoTradeStrategy())
        result = engine.run(pd.DataFrame())
        assert result.total_trades == 0
        # 空数据时 equity_curve 为 None 或空 DataFrame 均可
        assert result.equity_curve is None or result.equity_curve.empty

    def test_no_trade_strategy(self):
        """不交易策略：权益不变"""
        df = make_ohlcv(200)
        engine = BacktestEngine(NoTradeStrategy(), initial_capital=10000)
        result = engine.run(df)
        assert result.total_trades == 0
        assert result.total_return == pytest.approx(0.0, abs=0.5)
        # 权益应接近初始资金
        assert result.final_equity == pytest.approx(10000, rel=0.01)

    def test_buy_and_hold(self):
        """买入持有策略：上涨市场应盈利（只有买入，无卖出）"""
        df = make_ohlcv(500, trend=0.3)  # 上涨30%
        engine = BacktestEngine(BuyAndHoldStrategy(), initial_capital=10000)
        result = engine.run(df)
        # 只买入不卖出 → total_trades (卖单数) = 0
        # 但权益应偏离初始值（有持仓市值变化）
        assert result.total_return > 0

    def test_buy_and_hold_bear_market(self):
        """买入持有策略：下跌市场应亏损"""
        df = make_ohlcv(500, trend=-0.3)  # 下跌30%
        engine = BacktestEngine(BuyAndHoldStrategy(), initial_capital=10000)
        result = engine.run(df)
        assert result.total_return < 0

    def test_ma_strategy_generates_trades(self):
        """双均线策略应产生交易信号"""
        df = make_ohlcv(1000, trend=0.1, volatility=1.0)
        engine = BacktestEngine(MAStrategy(), initial_capital=10000)
        result = engine.run(df)
        # 应有至少几次交易
        assert result.total_trades >= 1

    def test_equity_curve_length(self):
        """权益曲线数据点数应与K线数匹配（考虑采样步长）"""
        df = make_ohlcv(300)
        engine = BacktestEngine(
            MAStrategy(),
            equity_sample_step=5,
        )
        result = engine.run(df, build_equity_curve=True)
        assert result.equity_curve is not None
        # 300 bars / step 5 ≈ 60 points
        assert len(result.equity_curve) > 0
        assert len(result.equity_curve) <= 300

    def test_no_equity_curve_mode(self):
        """build_equity_curve=False 应跳过权益曲线"""
        df = make_ohlcv(200)
        engine = BacktestEngine(MAStrategy())
        result = engine.run(df, build_equity_curve=False)
        assert result.equity_curve.empty
        assert result.total_return != 0

    def test_metrics_complete(self):
        """所有绩效指标应计算且合理"""
        df = make_ohlcv(500, trend=0.05)
        engine = BacktestEngine(BuyAndHoldStrategy(), initial_capital=10000)
        result = engine.run(df)

        metrics = result.to_dict()
        required_keys = ["总收益率", "年化收益率", "夏普比率", "最大回撤", "胜率", "盈亏比"]
        for key in required_keys:
            assert key in metrics, f"Missing metric: {key}"

        # 最大回撤应在合理范围
        assert result.max_drawdown >= 0
        assert result.max_drawdown < 100

    def test_result_to_dict_matches(self):
        """to_dict 输出指标与直接属性一致"""
        df = make_ohlcv(300)
        engine = BacktestEngine(BuyAndHoldStrategy(), initial_capital=10000)
        result = engine.run(df)
        d = result.to_dict()

        assert float(d["初始资金"].replace("$", "").replace(",", "")) == pytest.approx(10000, rel=0.01)
        assert d["交易次数"] == result.total_trades


# ============================================================
# 独立指标函数测试
# ============================================================

class TestMetrics:

    def test_total_return_positive(self):
        eq = pd.Series([100, 110, 120], index=pd.date_range("2024-01-01", periods=3))
        assert total_return(eq) == pytest.approx(20.0)

    def test_total_return_negative(self):
        eq = pd.Series([100, 90, 80], index=pd.date_range("2024-01-01", periods=3))
        assert total_return(eq) == pytest.approx(-20.0)

    def test_max_drawdown(self):
        eq = pd.Series([100, 120, 90, 110], index=pd.date_range("2024-01-01", periods=4))
        dd, _ = max_drawdown(eq)
        # 从120跌到90 = 25% 回撤
        assert dd == pytest.approx(25.0, abs=0.5)

    def test_sharpe_ratio_constant_returns(self):
        """恒定收益率（无波动）时夏普比率极高但不为零"""
        returns = pd.Series([0.01] * 100)
        sr = sharpe_ratio(returns)
        # 几乎恒定的正收益 → 极低波动 → 极高夏普
        assert sr > 1000  # 极小 std 导致极大比率

    def test_win_rate(self):
        trades = pd.DataFrame([
            {"side": "buy", "pnl": 0},
            {"side": "sell", "pnl": 100},
            {"side": "buy", "pnl": 0},
            {"side": "sell", "pnl": -50},
            {"side": "sell", "pnl": 30},
        ])
        wr = win_rate(trades)
        # 3 sells, 2 wins → 66.7%
        assert wr == pytest.approx(66.67, abs=0.1)

    def test_profit_factor(self):
        trades = pd.DataFrame([
            {"side": "sell", "pnl": 100},
            {"side": "sell", "pnl": -50},
        ])
        pf = profit_factor(trades)
        # 100 / 50 = 2.0
        assert pf == pytest.approx(2.0)

    def test_comprehensive_metrics(self):
        eq = pd.Series([100, 102, 105, 103, 108], index=pd.date_range("2024-01-01", periods=5))
        trades = pd.DataFrame([
            {"side": "sell", "pnl": 8},
        ])
        m = comprehensive_metrics(eq, trades, periods_per_year=365)
        assert "total_return" in m
        assert "sharpe_ratio" in m
        assert m["total_trades"] == 1
