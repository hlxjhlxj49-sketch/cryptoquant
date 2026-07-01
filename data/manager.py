"""
数据管理器
封装数据抓取和存储，提供一站式的数据同步和管理功能
"""

import pandas as pd
from typing import Optional, List, Callable, Dict
from datetime import datetime, timedelta
from data.fetcher import DataFetcher
from data.storage import DataStorage
from utils.logger import log


class DataManager:
    """
    数据管理器 - 统一的数据操作入口

    使用示例:
        manager = DataManager()
        manager.sync_history("BTC/USDT", "1h", days=30)
        df = manager.get_data("BTC/USDT", "1h")
    """

    def __init__(
        self,
        exchange_name: str = "binance",
        market_type: str = "spot",
        db_path: str = "E:/crypto_quant/data/market.db",
        test_mode: bool = True,
        proxies: Optional[Dict] = None,
    ):
        """
        初始化数据管理器

        参数:
            exchange_name: 交易所名称
            market_type: 市场类型 spot/swap/future/option
            db_path: 数据库路径
            test_mode: 测试模式（不需要API Key）
            proxies: 代理配置 {"https": "http://127.0.0.1:7890"}
        """
        self.exchange_name = exchange_name
        self.market_type = market_type
        self.fetcher = DataFetcher(
            exchange_name=exchange_name,
            market_type=market_type,
            test_mode=test_mode,
            proxies=proxies,
        )
        self.storage = DataStorage(db_path=db_path)
        log.info(f"📊 数据管理器已就绪: {exchange_name} ({market_type})")

    def sync_history(
        self,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        days: int = 30,
        progress_callback: Optional[Callable] = None,
    ) -> int:
        """
        同步历史数据（自动处理交易所单次获取限制，分批下载）

        参数:
            symbol: 交易对
            timeframe: K线周期
            days: 回溯天数
            progress_callback: 进度回调函数 progress(current, total)

        返回:
            同步的总数据条数
        """
        log.info(f"🔄 开始同步 {symbol} {timeframe}，回溯 {days} 天")

        # 计算需要获取的批次数
        # 每次最多获取1000条，1h周期每天24条 → 1000条约41天
        # 稳妥起见，每次500条
        batch_limit = 500
        total_bars = days * 24  # 粗略估计（按1h周期）
        batches = max(1, total_bars // batch_limit + (1 if total_bars % batch_limit else 0))

        total_saved = 0
        end_date = datetime.now()

        for batch in range(batches):
            # 计算本批次的起始时间
            batch_days = (batch + 1) * (batch_limit // 24) + 1
            since = (end_date - timedelta(days=min(batch_days, days))).strftime("%Y-%m-%d")

            # 抓取数据
            df = self.fetcher.fetch_ohlcv(symbol, timeframe, since=since, limit=batch_limit)

            if df.empty:
                log.warning(f"⚠️ 批次 {batch+1}/{batches} 无数据返回")
                continue

            # 保存到数据库
            saved = self.storage.save_ohlcv(df, self.exchange_name, symbol, timeframe)
            total_saved += saved

            # 更新进度
            if progress_callback:
                progress_callback(batch + 1, batches)

            log.info(f"📊 批次 {batch+1}/{batches}: 保存 {saved} 条")

        log.info(f"✅ 同步完成: 共保存 {total_saved} 条数据")
        return total_saved

    def get_data(
        self,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        auto_sync: bool = True,
    ) -> pd.DataFrame:
        """
        获取K线数据（优先从本地数据库读取，无数据时自动下载）

        参数:
            symbol: 交易对
            timeframe: K线周期
            start_date: 起始日期
            end_date: 结束日期
            limit: 限制返回条数
            auto_sync: 数据库无数据时是否自动从交易所下载

        返回:
            DataFrame
        """
        # 先从数据库加载
        df = self.storage.load_ohlcv(
            self.exchange_name, symbol, timeframe,
            start_date=start_date, end_date=end_date, limit=limit,
        )

        # 如果有数据，直接返回
        if not df.empty:
            return df

        # 数据库无数据且允许自动下载
        if auto_sync:
            log.info(f"📥 本地无数据，自动从交易所下载 {symbol} {timeframe}...")

            # 确定下载天数
            if start_date:
                days = (datetime.now() - datetime.fromisoformat(start_date)).days + 1
            else:
                days = 90  # 默认下载90天

            self.sync_history(symbol, timeframe, days=min(days, 365))

            # 再次从数据库加载
            df = self.storage.load_ohlcv(
                self.exchange_name, symbol, timeframe,
                start_date=start_date, end_date=end_date, limit=limit,
            )

        return df

    def get_available_symbols(self) -> List[str]:
        """获取交易所支持的USDT交易对列表"""
        return self.fetcher.get_usdt_symbols()

    def get_data_summary(self) -> pd.DataFrame:
        """获取数据库中所有数据的概览"""
        return self.storage.get_data_summary()

    def download_top_coins(
        self,
        timeframe: str = "1h",
        days: int = 30,
        top_n: int = 20,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """
        一键下载主流币种数据

        参数:
            timeframe: K线周期
            days: 回溯天数
            top_n: 下载前N个主流币
            progress_callback: 进度回调

        返回:
            {"success": 成功数, "failed": 失败数, "results": {symbol: count}}
        """
        # 主流币种列表（按市值排序）
        top_symbols = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
            "MATIC/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "ETC/USDT",
            "FIL/USDT", "APT/USDT", "ARB/USDT", "OP/USDT", "NEAR/USDT",
            "INJ/USDT", "TIA/USDT", "SEI/USDT", "SUI/USDT", "ORDI/USDT",
        ]

        symbols = top_symbols[:top_n]
        results = {}
        success = 0
        failed = 0

        log.info(f"🚀 开始批量下载 {top_n} 个主流币种数据...")

        for i, symbol in enumerate(symbols):
            try:
                count = self.sync_history(symbol, timeframe, days=days)
                results[symbol] = count
                if count > 0:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                log.error(f"❌ {symbol} 下载失败: {e}")
                results[symbol] = 0
                failed += 1

            if progress_callback:
                progress_callback(i + 1, len(symbols))

        log.info(f"✅ 批量下载完成: 成功 {success}, 失败 {failed}")
        return {"success": success, "failed": failed, "results": results}


# ===== 便捷函数 =====

def create_manager(
    exchange: str = "binance",
    market_type: str = "spot",
    db_path: str = "E:/crypto_quant/data/market.db",
    proxies: Optional[Dict] = None,
) -> DataManager:
    """快速创建数据管理器"""
    return DataManager(
        exchange_name=exchange,
        market_type=market_type,
        db_path=db_path,
        proxies=proxies,
    )
