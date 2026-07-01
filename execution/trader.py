"""
实盘交易执行器
通过 CCXT 连接真实交易所，执行真实交易

⚠️ 警告：此模块涉及真实资金交易，使用前请充分测试和评估风险
"""

import ccxt
from typing import Dict, Optional, List
from datetime import datetime
from execution.risk import RiskManager
from utils.logger import log


class LiveTrader:
    """
    实盘交易执行器

    ⚠️ 使用前必须：
    1. 在交易所创建API Key
    2. 在 config/settings.yaml 中配置API信息
    3. 先在模拟盘中充分测试策略
    4. 从小资金开始，逐步增加

    使用示例:
        trader = LiveTrader(api_key="xxx", secret="xxx", exchange="binance")
        trader.connect()
        order = trader.market_buy("BTC/USDT", size=0.001)
    """

    def __init__(
        self,
        api_key: str = "",
        secret: str = "",
        password: str = "",
        exchange: str = "binance",
        test_mode: bool = True,
        risk_manager: Optional[RiskManager] = None,
    ):
        """
        初始化实盘交易器

        参数:
            api_key: API Key
            secret: API Secret
            password: API密码（部分交易所需要）
            exchange: 交易所名称
            test_mode: 测试模式（True=沙盒，False=实盘）
            risk_manager: 风险管理器
        """
        self.exchange_name = exchange
        self.test_mode = test_mode
        self.risk_manager = risk_manager or RiskManager()
        self.is_connected = False

        # 创建交易所实例
        exchange_class = getattr(ccxt, exchange, None)
        if exchange_class is None:
            raise ValueError(f"不支持的交易所: {exchange}")

        self.exchange = exchange_class({
            "apiKey": api_key,
            "secret": secret,
            "password": password,
            "enableRateLimit": True,
        })

        # 设置沙盒模式
        if test_mode and "test" in self.exchange.urls:
            self.exchange.urls["api"] = self.exchange.urls["test"]
            log.info("⚠️ 测试模式已启用（沙盒环境）")

        # 账户状态
        self.balances: Dict = {}
        self.positions: List[Dict] = []
        self.orders: List[Dict] = []
        self.trades: List[Dict] = []

    def connect(self) -> bool:
        """
        连接交易所并验证API

        返回:
            True 连接成功
        """
        try:
            self.exchange.load_markets()
            self.balances = self.exchange.fetch_balance()
            self.is_connected = True
            log.info(f"✅ 已连接到 {self.exchange_name} {'(测试模式)' if self.test_mode else '(实盘模式)'}")
            return True
        except Exception as e:
            log.error(f"❌ 连接失败: {e}")
            self.is_connected = False
            return False

    def get_balance(self, currency: str = "USDT") -> Dict:
        """
        获取账户余额

        参数:
            currency: 币种

        返回:
            {"free": 可用余额, "used": 冻结余额, "total": 总余额}
        """
        try:
            balance = self.exchange.fetch_balance()
            self.balances = balance
            info = balance.get(currency, {})
            return {
                "free": info.get("free", 0),
                "used": info.get("used", 0),
                "total": info.get("total", 0),
            }
        except Exception as e:
            log.error(f"获取余额失败: {e}")
            return {"free": 0, "used": 0, "total": 0}

    def market_buy(self, symbol: str, size: float, params: Dict = None) -> Optional[Dict]:
        """
        市价买入

        参数:
            symbol: 交易对
            size: 买入数量
            params: 额外参数

        返回:
            订单信息，失败返回None
        """
        if not self.is_connected:
            log.error("❌ 未连接交易所")
            return None

        if self.test_mode:
            log.info(f"🧪 [测试] 模拟买入: {symbol} {size}")
            mock_order = {
                "id": f"test_{datetime.now().timestamp()}",
                "symbol": symbol,
                "side": "buy",
                "type": "market",
                "amount": size,
                "status": "closed",
                "filled": size,
                "timestamp": datetime.now(),
            }
            self.orders.append(mock_order)
            return mock_order

        try:
            order = self.exchange.create_market_buy_order(symbol, size, params or {})
            self.orders.append(order)
            log.info(f"✅ 市价买入成功: {symbol} {size}")
            return order
        except Exception as e:
            log.error(f"❌ 买入失败: {e}")
            return None

    def market_sell(self, symbol: str, size: float, params: Dict = None) -> Optional[Dict]:
        """
        市价卖出

        返回:
            订单信息，失败返回None
        """
        if not self.is_connected:
            log.error("❌ 未连接交易所")
            return None

        if self.test_mode:
            log.info(f"🧪 [测试] 模拟卖出: {symbol} {size}")
            mock_order = {
                "id": f"test_{datetime.now().timestamp()}",
                "symbol": symbol,
                "side": "sell",
                "type": "market",
                "amount": size,
                "status": "closed",
                "filled": size,
                "timestamp": datetime.now(),
            }
            self.orders.append(mock_order)
            return mock_order

        try:
            order = self.exchange.create_market_sell_order(symbol, size, params or {})
            self.orders.append(order)
            log.info(f"✅ 市价卖出成功: {symbol} {size}")
            return order
        except Exception as e:
            log.error(f"❌ 卖出失败: {e}")
            return None

    def limit_buy(self, symbol: str, size: float, price: float, params: Dict = None) -> Optional[Dict]:
        """
        限价买入

        参数:
            symbol: 交易对
            size: 买入数量
            price: 限价价格
            params: 额外参数

        返回:
            订单信息
        """
        if not self.is_connected:
            log.error("❌ 未连接交易所")
            return None

        if self.test_mode:
            log.info(f"🧪 [测试] 限价买入: {symbol} {size} @ ${price:,.2f}")
            return {"id": f"test_{datetime.now().timestamp()}", "status": "open"}

        try:
            order = self.exchange.create_limit_buy_order(symbol, size, price, params or {})
            self.orders.append(order)
            log.info(f"✅ 限价买入挂单: {symbol} {size} @ ${price:,.2f}")
            return order
        except Exception as e:
            log.error(f"❌ 限价买入失败: {e}")
            return None

    def limit_sell(self, symbol: str, size: float, price: float, params: Dict = None) -> Optional[Dict]:
        """限价卖出"""
        if not self.is_connected:
            return None

        if self.test_mode:
            log.info(f"🧪 [测试] 限价卖出: {symbol} {size} @ ${price:,.2f}")
            return {"id": f"test_{datetime.now().timestamp()}", "status": "open"}

        try:
            order = self.exchange.create_limit_sell_order(symbol, size, price, params or {})
            self.orders.append(order)
            return order
        except Exception as e:
            log.error(f"❌ 限价卖出失败: {e}")
            return None

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        撤单

        返回:
            True 撤单成功
        """
        try:
            self.exchange.cancel_order(order_id, symbol)
            log.info(f"✅ 撤单成功: {order_id}")
            return True
        except Exception as e:
            log.error(f"❌ 撤单失败: {e}")
            return False

    def fetch_open_orders(self, symbol: str = None) -> List[Dict]:
        """获取未成交订单"""
        try:
            return self.exchange.fetch_open_orders(symbol)
        except Exception as e:
            log.error(f"获取未成交订单失败: {e}")
            return []

    def fetch_positions(self, symbols: List[str] = None) -> List[Dict]:
        """获取当前持仓"""
        try:
            return self.exchange.fetch_positions(symbols)
        except Exception:
            return []

    def get_ticker(self, symbol: str) -> Dict:
        """获取最新行情"""
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            log.error(f"获取行情失败: {e}")
            return {}

    def disconnect(self):
        """断开连接"""
        self.is_connected = False
        log.info("已断开交易所连接")
