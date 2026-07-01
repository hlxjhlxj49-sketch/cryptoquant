# 回测模块 v2.0
from backtest.engine import BacktestEngine, BacktestResult
from backtest.broker import SimulatedBroker
from backtest.metrics import (
    sharpe_ratio, sortino_ratio, calmar_ratio,
    max_drawdown, win_rate, profit_factor,
    comprehensive_metrics,
)
