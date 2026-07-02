"""
多交易所数据抓取模块
基于 CCXT 库统一接口，支持币安、OKX、Bybit 等 100+ 交易所

支持的市场类型：
  - spot:    现货（如 BTC/USDT）
  - swap:    永续合约（如 BTC/USDT:USDT）
  - future:  交割合约（如 BTC/USDT-241229）
  - option:  期权（如 BTC/USDT-241229-50000-C）
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from utils.logger import log


class DataFetcher:
    """
    数据抓取器
    封装 CCXT，提供统一的数据获取接口

    使用示例:
        # 现货
        fetcher = DataFetcher(exchange_name="binance")
        df = fetcher.fetch_ohlcv("BTC/USDT", "1h", limit=100)

        # 永续合约
        fetcher = DataFetcher(exchange_name="binance", market_type="swap")
        df = fetcher.fetch_ohlcv("BTC/USDT:USDT", "1h", limit=100)

        # 自定义代理
        fetcher = DataFetcher(exchange_name="binance", proxies={"http": "...", "https": "..."})
    """

    # 支持的K线周期
    TIMEFRAMES = {
        "1m": "1分钟",
        "5m": "5分钟",
        "15m": "15分钟",
        "30m": "30分钟",
        "1h": "1小时",
        "4h": "4小时",
        "1d": "日线",
        "1w": "周线",
    }

    # 市场类型
    MARKET_TYPES = {
        "spot": "现货",
        "swap": "永续合约",
        "future": "交割合约",
        "option": "期权",
    }

    # 主流交易所列表
    POPULAR_EXCHANGES = {
        "binance": "币安 Binance",
        "binanceusdm": "币安合约 Binance Futures",
        "okx": "OKX",
        "bybit": "Bybit",
        "gate": "Gate.io",
        "kucoin": "KuCoin",
        "huobi": "火币 HTX",
        "bitget": "Bitget",
        "mexc": "MEXC",
    }

    # 不同交易所对 market_type 的 defaultType 映射
    MARKET_TYPE_MAP = {
        "spot": "spot",
        "swap": "swap",       # CCXT统一叫 swap（永续）
        "future": "future",   # CCXT统一叫 future（交割）
        "option": "option",
    }

    def __init__(
        self,
        exchange_name: str = "binance",
        market_type: str = "spot",
        test_mode: bool = True,
        proxies: Optional[Dict] = None,
        timeout: int = 30000,
    ):
        """
        初始化数据抓取器

        参数:
            exchange_name: 交易所名称（binance/okx/bybit等）
            market_type: 市场类型 spot/swap/future/option
            test_mode: 是否使用测试模式（默认True，不需要API Key）
            proxies: 代理配置，如 {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
            timeout: 请求超时时间（毫秒）
        """
        self.exchange_name = exchange_name
        self.market_type = market_type

        # 根据交易所名称动态获取CCXT类
        exchange_class = getattr(ccxt, exchange_name, None)
        if exchange_class is None:
            raise ValueError(
                f"不支持的交易所: {exchange_name}\n"
                f"可用交易所: {list(self.POPULAR_EXCHANGES.keys())}"
            )

        # 构建交易所配置
        config = {
            "enableRateLimit": True,              # 自动遵守API限速
            "timeout": timeout,                    # 请求超时
            "options": {
                "defaultType": self.MARKET_TYPE_MAP.get(market_type, "spot"),
            },
        }

        # 代理设置
        if proxies:
            config["proxies"] = proxies
            log.info(f"🔧 已配置代理: {proxies.get('https', proxies.get('http', ''))}")

        # 创建交易所实例
        try:
            self.exchange = exchange_class(config)
        except Exception as e:
            raise ConnectionError(
                f"无法初始化 {exchange_name} 交易所:\n"
                f"错误: {e}\n"
                f"可能的原因:\n"
                f"  1. 网络连接问题（尝试配置代理）\n"
                f"  2. CCXT版本过旧（运行 pip install --upgrade ccxt）\n"
                f"  3. 交易所暂时不可用"
            )

        # 测试模式提示
        if test_mode:
            log.info(f"⚠️ 测试模式 — 仅使用公开API获取数据（无需API Key）")

        market_label = self.MARKET_TYPES.get(market_type, market_type)
        exchange_label = self.POPULAR_EXCHANGES.get(exchange_name, exchange_name)
        log.info(f"✅ 已连接: {exchange_label} ({market_label})")

    def fetch_markets(self, reload: bool = False) -> Dict:
        """
        获取交易所所有交易对信息

        参数:
            reload: 是否强制重新加载

        返回:
            交易对字典，每个包含 symbol, base, quote, type, contractType 等字段
        """
        if reload or not self.exchange.markets:
            log.info(f"正在获取 {self.exchange_name} 交易对列表...")
            try:
                self.exchange.load_markets(reload=reload)
                log.info(f"获取到 {len(self.exchange.markets)} 个交易对")
            except Exception as e:
                log.error(f"获取交易对列表失败: {e}")
                log.info("💡 提示：可能需要配置代理或检查网络连接")
                return {}
        return self.exchange.markets or {}

    def get_symbols_by_type(self, market_type: Optional[str] = None) -> Dict[str, List[str]]:
        """
        按市场类型获取交易对

        参数:
            market_type: 市场类型（None则返回全部类型）

        返回:
            {"spot": [...], "swap": [...], "future": [...], "option": [...]}
        """
        markets = self.fetch_markets()
        if not markets or not isinstance(markets, dict):
            return {"spot": [], "swap": [], "future": [], "option": []}

        result = {"spot": [], "swap": [], "future": [], "option": []}

        for symbol, market in markets.items():
            mtype = market.get("type", "spot")  # spot/swap/future/option
            if mtype in result:
                result[mtype].append(symbol)

        # 排序
        for key in result:
            result[key].sort()

        return result

    def get_usdt_symbols(self) -> List[str]:
        """获取所有USDT计价的现货交易对"""
        self.fetch_markets()
        symbols = [
            s for s in self.exchange.symbols
            if s.endswith("/USDT")
            and not any(x in s for x in ["USDC/USDT", "BUSD/USDT", "TUSD/USDT", "FDUSD/USDT"])
            and ":" not in s  # 排除合约
        ]
        symbols.sort()
        return symbols

    def get_swap_symbols(self) -> List[str]:
        """获取所有永续合约交易对（USDT本位）"""
        self.fetch_markets()
        symbols = [
            s for s in self.exchange.symbols
            if ":USDT" in s or s.endswith("/USDT:USDT")
        ]
        symbols.sort()
        return symbols

    def search_symbols(self, keyword: str) -> List[str]:
        """
        搜索交易对

        参数:
            keyword: 搜索关键词（如 "BTC", "ETH"）

        返回:
            匹配的交易对列表
        """
        self.fetch_markets()
        keyword_upper = keyword.upper()
        matches = [s for s in self.exchange.symbols if keyword_upper in s.upper()]
        matches.sort()
        return matches

    def fetch_ohlcv(
        self,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        since: Optional[str] = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        """
        获取K线（OHLCV）数据

        参数:
            symbol: 交易对
                    现货: "BTC/USDT"
                    永续合约: "BTC/USDT:USDT" (币安) 或 "BTC-USDT-SWAP" (OKX)
                    交割合约: "BTC/USDT-241229"
                    期权: "BTC/USDT-241229-50000-C"
            timeframe: K线周期（1m/5m/15m/1h/4h/1d等）
            since: 起始时间（如 "2024-01-01"）
            limit: 获取K线数量

        返回:
            DataFrame: [timestamp, open, high, low, close, volume]
        """
        try:
            # 将since字符串转为毫秒时间戳
            since_ts = None
            if since:
                try:
                    dt = datetime.fromisoformat(since)
                    since_ts = int(dt.timestamp() * 1000)
                except ValueError:
                    log.warning(f"日期格式无效: {since}，使用 'YYYY-MM-DD' 格式")

            log.info(f"📥 {symbol} {timeframe} | limit={limit} | since={since or '最新'}")

            ohlcv = self.exchange.fetch_ohlcv(
                symbol, timeframe, since=since_ts, limit=limit
            )

            if not ohlcv:
                log.warning(f"⚠️ {symbol} 无数据返回")
                log.info(f"💡 排查建议:")
                log.info(f"   1. 确认交易对名称正确（大小写敏感）")
                log.info(f"   2. 检查交易所是否支持该交易对")
                log.info(f"   3. 尝试使用 search_symbols('BTC') 查找")
                return pd.DataFrame()

            # 转为DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df = df[df["volume"] > 0].copy()

            log.info(f"✅ {symbol}: {len(df)} 条数据")
            return df

        except ccxt.BadSymbol:
            log.error(f"❌ 交易对不存在: {symbol}")
            log.info(f"💡 可用 search_symbols() 方法查找正确的交易对名称")
            return pd.DataFrame()
        except ccxt.NetworkError as e:
            log.error(f"❌ 网络错误: {e}")
            log.info(f"💡 可能需要配置代理: DataFetcher(exchange_name='binance', proxies={{'https': 'http://127.0.0.1:7890'}})")
            return pd.DataFrame()
        except ccxt.ExchangeNotAvailable as e:
            log.error(f"❌ 交易所不可用: {e}")
            return pd.DataFrame()
        except ccxt.RateLimitExceeded:
            log.error(f"❌ API频率限制，请稍后重试")
            return pd.DataFrame()
        except Exception as e:
            log.error(f"❌ 数据抓取失败: {type(e).__name__}: {e}")
            return pd.DataFrame()

    def fetch_batch(
        self,
        symbols: List[str],
        timeframe: str = "1h",
        limit: int = 500,
        since: Optional[str] = None,
        pause_seconds: float = 0.5,
    ) -> Dict[str, pd.DataFrame]:
        """
        批量抓取多个交易对

        参数:
            symbols: 交易对列表
            timeframe: K线周期
            limit: 每个交易对数量
            since: 起始时间
            pause_seconds: 请求间隔（秒）

        返回:
            {交易对: DataFrame}
        """
        import time
        results = {}
        total = len(symbols)

        for i, symbol in enumerate(symbols, 1):
            log.info(f"📥 [{i}/{total}] {symbol}...")
            df = self.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            if not df.empty:
                results[symbol] = df

            # 请求间隔
            if i < total:
                time.sleep(pause_seconds)

        log.info(f"✅ 批量完成: {len(results)}/{total}")
        return results

    def fetch_ticker(self, symbol: str = "BTC/USDT") -> Dict:
        """获取24小时行情概览"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "last": ticker.get("last"),
                "change_pct": ticker.get("percentage"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
                "volume": ticker.get("baseVolume"),
                "quote_volume": ticker.get("quoteVolume"),
            }
        except Exception as e:
            log.error(f"获取行情失败: {e}")
            return {}

    def fetch_order_book(self, symbol: str = "BTC/USDT", depth: int = 20) -> Dict:
        """获取订单簿深度"""
        try:
            ob = self.exchange.fetch_order_book(symbol, limit=depth)
            return {
                "bids": ob["bids"][:depth],
                "asks": ob["asks"][:depth],
                "timestamp": ob.get("datetime"),
            }
        except Exception as e:
            log.error(f"获取订单簿失败: {e}")
            return {"bids": [], "asks": [], "timestamp": None}

    def test_connection(self) -> Tuple[bool, str]:
        """
        测试交易所连接

        返回:
            (是否成功, 消息)
        """
        try:
            self.exchange.fetch_time()
            return True, "连接正常"
        except ccxt.NetworkError:
            return False, "网络无法访问交易所，可能需要代理"
        except Exception as e:
            return False, f"连接失败: {str(e)[:100]}"


# ===== 便捷函数 =====

def create_fetcher(
    exchange: str = "binance",
    market_type: str = "spot",
    test_mode: bool = True,
    proxies: Optional[Dict] = None,
) -> DataFetcher:
    """快速创建数据抓取器"""
    return DataFetcher(
        exchange_name=exchange,
        market_type=market_type,
        test_mode=test_mode,
        proxies=proxies,
    )
