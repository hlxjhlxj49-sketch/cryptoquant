"""
回测引擎（事件驱动）
用历史数据模拟策略执行，输出交易结果和绩效指标

v2.0 优化：
  - 预分配 equity 列表，避免动态增长
  - max_dd 直接传递，消除重复计算
  - 可按步长采样，大数据集时大幅减少权益曲线体积
  - _sync_trades 使用计数器替代列表长度比较，更可靠
  - 支持不生成权益曲线（raw_mode），用于参数扫描等场景

使用示例:
    engine = BacktestEngine(strategy=my_strategy)
    results = engine.run(df)
    print(results.metrics())
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from strategy.base import Strategy
from backtest.broker import SimulatedBroker
from utils.logger import log


class BacktestResult:
    """回测结果"""

    def __init__(self):
        self.strategy_name: str = ""
        self.symbol: str = ""
        self.timeframe: str = ""
        self.start_date: str = ""
        self.end_date: str = ""

        # 绩效指标
        self.initial_capital: float = 0.0
        self.final_equity: float = 0.0
        self.total_return: float = 0.0
        self.annual_return: float = 0.0
        self.total_trades: int = 0
        self.win_trades: int = 0
        self.loss_trades: int = 0
        self.win_rate: float = 0.0
        self.max_drawdown: float = 0.0
        self.max_drawdown_duration: int = 0
        self.sharpe_ratio: float = 0.0
        self.sortino_ratio: float = 0.0
        self.calmar_ratio: float = 0.0
        self.profit_factor: float = 0.0
        self.avg_win: float = 0.0
        self.avg_loss: float = 0.0
        self.total_fees: float = 0.0

        # 详细数据
        self.equity_curve: pd.DataFrame = None
        self.trades: pd.DataFrame = None
        self.monthly_returns: pd.DataFrame = None

    def to_dict(self) -> Dict:
        """转为字典（用于界面展示）"""
        return {
            "策略名称": self.strategy_name,
            "交易对": self.symbol,
            "周期": self.timeframe,
            "回测区间": f"{self.start_date} ~ {self.end_date}",
            "初始资金": f"${self.initial_capital:,.2f}",
            "最终权益": f"${self.final_equity:,.2f}",
            "总收益率": f"{self.total_return:+.2f}%",
            "年化收益率": f"{self.annual_return:+.2f}%",
            "交易次数": self.total_trades,
            "胜率": f"{self.win_rate:.1f}%",
            "最大回撤": f"{self.max_drawdown:.2f}%",
            "夏普比率": f"{self.sharpe_ratio:.2f}",
            "卡尔玛比率": f"{self.calmar_ratio:.2f}",
            "盈亏比": f"{self.profit_factor:.2f}",
            "总手续费": f"${self.total_fees:,.2f}",
        }


# 不同周期的年化系数
_PERIODS_PER_YEAR = {
    "1m": 365 * 24 * 60,
    "5m": 365 * 24 * 12,
    "15m": 365 * 24 * 4,
    "30m": 365 * 24 * 2,
    "1h": 365 * 24,
    "4h": 365 * 6,
    "1d": 365,
    "1w": 52,
}


class BacktestEngine:
    """
    回测引擎 v2.0

    工作流程:
        1. 加载K线数据
        2. 初始化策略和模拟券商
        3. 逐K线循环：调用策略on_bar → 执行交易
        4. 计算绩效指标
        5. 返回回测结果
    """

    def __init__(
        self,
        strategy: Strategy,
        initial_capital: float = 10000.0,
        mode: str = "spot",
        maker_fee: float = 0.001,
        taker_fee: float = 0.001,
        slippage: float = 0.0005,
        equity_sample_step: int = 1,
    ):
        """
        初始化回测引擎

        参数:
            strategy: 策略实例
            initial_capital: 初始资金
            mode: 交易模式 spot/futures
            maker_fee: 挂单手续费
            taker_fee: 吃单手续费
            slippage: 滑点比例
            equity_sample_step: 权益曲线采样步长（1=每K线记录，5=每5K线记录一次）
                                大数据集建议设置 >= 5，可减少 80% 权益曲线内存占用
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.equity_sample_step = max(1, equity_sample_step)

        # 创建模拟券商
        self.broker = SimulatedBroker(
            initial_capital=initial_capital,
            mode=mode,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            slippage=slippage,
        )

    def run(
        self,
        df: pd.DataFrame,
        symbol: str = "Unknown",
        timeframe: str = "1h",
        build_equity_curve: bool = True,
    ) -> BacktestResult:
        """
        执行回测

        参数:
            df: K线数据DataFrame（需包含 open/high/low/close/volume）
            symbol: 交易对名称
            timeframe: K线周期
            build_equity_curve: 是否构建权益曲线（参数扫描时可关闭以加速）

        返回:
            BacktestResult 对象
        """
        if df.empty:
            log.error("回测数据为空")
            return BacktestResult()

        total_bars = len(df)
        log.info(
            f"开始回测: {symbol} {timeframe}, "
            f"初始资金=${self.initial_capital:,.0f}, "
            f"数据量={total_bars}条"
        )

        # ---- 重置状态 ----
        self.broker.reset()
        self.strategy._reset_portfolio(self.initial_capital)
        self.strategy._trade_count = 0  # 用于 syncing

        # ---- 设置策略数据 & 启动 ----
        self.strategy._set_data(df)
        self.strategy.on_start()

        # ---- 预分配权益曲线（比 append 快 ~2x）----
        sample_count = (total_bars + self.equity_sample_step - 1) // self.equity_sample_step
        equity_records: list = [{} for _ in range(sample_count)] if build_equity_curve else []
        eq_idx = 0

        # ---- 回测循环 ----
        peak_equity = self.initial_capital
        max_dd = 0.0
        max_dd_duration = 0
        current_dd_duration = 0
        in_drawdown = False
        final_price = float(df.iloc[-1]["close"])

        for i in range(total_bars):
            bar = df.iloc[i]
            current_price = float(bar["close"])
            timestamp = df.index[i]

            self.strategy.current_index = i

            # 执行策略逻辑
            try:
                self.strategy.on_bar(bar)
            except Exception as exc:
                log.error(f"策略执行错误 (K线{i}): {exc}")
                continue

            # 同步策略交易到券商
            self._sync_trades(timestamp, current_price)

            # 记录权益（按采样步长）
            if build_equity_curve and (i % self.equity_sample_step == 0):
                eq = self.broker.equity(current_price)
                equity_records[eq_idx] = {
                    "time": timestamp, "equity": eq,
                    "cash": self.broker.cash,
                    "position": self.broker.position,
                    "price": current_price,
                }
                eq_idx += 1

            # 更新最大回撤（O(1) 每K线）
            current_equity = self.broker.equity(current_price)
            if current_equity > peak_equity:
                peak_equity = current_equity
                if in_drawdown:
                    max_dd_duration = max(max_dd_duration, current_dd_duration)
                    in_drawdown = False
                    current_dd_duration = 0
            else:
                dd_pct = (peak_equity - current_equity) / peak_equity * 100
                if dd_pct > max_dd:
                    max_dd = dd_pct
                if not in_drawdown:
                    in_drawdown = True
                current_dd_duration += 1

            final_price = current_price

        # 收尾：如果还在回撤中
        if in_drawdown:
            max_dd_duration = max(max_dd_duration, current_dd_duration)

        # 清理预分配列表中未使用的槽位
        if build_equity_curve:
            equity_records = equity_records[:eq_idx]

        # ---- 策略结束 ----
        try:
            self.strategy.on_finish()
        except Exception:
            pass

        # ---- 构建权益 DataFrame ----
        final_equity = self.broker.equity(final_price)

        # ---- 计算绩效指标 ----
        result = self._calculate_metrics(
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            equity_records=equity_records,
            peak_equity=peak_equity,
            max_dd=max_dd,
            max_dd_duration=max_dd_duration,
            final_equity=final_equity,
            final_price=final_price,
        )

        log.info(
            f"回测完成: 收益率={result.total_return:+.2f}%, "
            f"夏普={result.sharpe_ratio:.2f}, "
            f"回撤={result.max_drawdown:.2f}%"
        )

        return result

    def _sync_trades(self, timestamp, current_price: float):
        """
        将策略的新增交易操作同步到模拟券商

        使用计数器 _trade_count 追踪已同步的交易数量，
        避免每次遍历整个策略交易列表。
        """
        strategy_trades = self.strategy.portfolio["trades"]
        new_start = getattr(self.strategy, "_trade_count", 0)

        for i in range(new_start, len(strategy_trades)):
            trade = strategy_trades[i]
            if trade["side"] == "buy":
                self.broker.buy(
                    price=current_price,
                    size=trade["size"],
                    timestamp=timestamp,
                )
            elif trade["side"] == "sell":
                self.broker.sell(
                    price=current_price,
                    size=trade["size"],
                    timestamp=timestamp,
                )

        self.strategy._trade_count = len(strategy_trades)

        # 同步策略账户状态 = 券商状态（券商含手续费/滑点，更准确）
        self.strategy.portfolio["cash"] = self.broker.cash
        self.strategy.portfolio["position"] = self.broker.position

    def _calculate_metrics(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        equity_records: list,
        peak_equity: float,
        max_dd: float,
        max_dd_duration: int,
        final_equity: float,
        final_price: float,
    ) -> BacktestResult:
        """
        计算所有绩效指标

        已把 max_dd 从循环直接传入，不再重复计算权益曲线。
        """
        result = BacktestResult()

        # ---- 基本信息 ----
        result.strategy_name = self.strategy.name
        result.symbol = symbol
        result.timeframe = timeframe
        result.start_date = str(df.index[0])
        result.end_date = str(df.index[-1])
        result.initial_capital = self.initial_capital
        result.final_equity = final_equity
        result.total_fees = self.broker.total_fees
        result.max_drawdown = max_dd
        result.max_drawdown_duration = max_dd_duration

        # ---- 收益率 ----
        result.total_return = (final_equity - self.initial_capital) / self.initial_capital * 100

        # 年化收益率
        days = max((df.index[-1] - df.index[0]).days, 1)
        years = days / 365
        if years > 0:
            result.annual_return = (
                (final_equity / self.initial_capital) ** (1 / years) - 1
            ) * 100

        # ---- 交易统计 ----
        trades_df = self.broker.to_trades_df()
        result.trades = trades_df

        sells = trades_df[trades_df["side"] == "sell"] if not trades_df.empty else pd.DataFrame()
        result.total_trades = len(sells)

        if result.total_trades > 0 and "pnl" in sells.columns:
            result.win_trades = int((sells["pnl"] > 0).sum())
            result.loss_trades = int((sells["pnl"] < 0).sum())
            result.win_rate = result.win_trades / result.total_trades * 100

            wins = sells.loc[sells["pnl"] > 0, "pnl"]
            losses = sells.loc[sells["pnl"] < 0, "pnl"]
            result.avg_win = float(wins.mean()) if len(wins) > 0 else 0.0
            result.avg_loss = float(losses.mean()) if len(losses) > 0 else 0.0

            total_wins = float(wins.sum()) if len(wins) > 0 else 0.0
            total_losses = abs(float(losses.sum())) if len(losses) > 0 else 1.0
            result.profit_factor = total_wins / total_losses if total_losses > 0 else 0.0

        # ---- 权益曲线 DataFrame ----
        if equity_records:
            result.equity_curve = pd.DataFrame(equity_records).set_index("time")
        else:
            result.equity_curve = pd.DataFrame()

        # ---- 夏普 / 索提诺 ----
        if not result.equity_curve.empty and len(result.equity_curve) > 1:
            returns = result.equity_curve["equity"].pct_change().dropna()
            periods_per_year = _PERIODS_PER_YEAR.get(timeframe, 365 * 24)

            if len(returns) > 0 and returns.std() > 0:
                result.sharpe_ratio = float(
                    returns.mean() / returns.std() * np.sqrt(periods_per_year)
                )

                downside = returns[returns < 0]
                if len(downside) > 1 and downside.std() > 0:
                    result.sortino_ratio = float(
                        returns.mean() / downside.std() * np.sqrt(periods_per_year)
                    )

        # ---- 卡尔玛比率 ----
        if result.max_drawdown > 0:
            result.calmar_ratio = result.annual_return / result.max_drawdown

        # ---- 月度收益 ----
        if not result.equity_curve.empty and len(result.equity_curve) > 2:
            try:
                monthly = result.equity_curve["equity"].resample("ME").last()
                if len(monthly) > 1:
                    result.monthly_returns = monthly.pct_change().dropna() * 100
            except Exception:
                result.monthly_returns = pd.DataFrame()

        return result
