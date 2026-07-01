"""
SQLite 数据库存储模块
将K线数据存入本地SQLite，支持高效的读取和查询

数据库设计：
  每张表的命名规则：{交易所}_{交易对}_{周期}
  例如：binance_BTC_USDT_1h

  表结构：
    - timestamp   TEXT    时间戳（主键，ISO格式）
    - open        REAL    开盘价
    - high        REAL    最高价
    - low         REAL    最低价
    - close       REAL    收盘价
    - volume      REAL    成交量
"""

import sqlite3
import pandas as pd
import os
from typing import Optional, List
from datetime import datetime
from utils.logger import log


class DataStorage:
    """
    SQLite 数据存储管理器

    使用示例:
        storage = DataStorage("E:/crypto_quant/data/market.db")
        storage.save_ohlcv(df, "binance", "BTC/USDT", "1h")
        df = storage.load_ohlcv("binance", "BTC/USDT", "1h")
    """

    def __init__(self, db_path: str = "E:/crypto_quant/data/market.db"):
        """
        初始化数据库连接

        参数:
            db_path: SQLite数据库文件路径
        """
        # 确保数据库目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self.db_path = db_path
        log.info(f"📦 数据库路径: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")   # 提高并发写入性能
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    @staticmethod
    def _table_name(exchange: str, symbol: str, timeframe: str) -> str:
        """
        生成表名

        参数:
            exchange: 交易所名称
            symbol: 交易对（如 BTC/USDT）
            timeframe: K线周期

        返回:
            表名，如 "binance_BTC_USDT_1h"
        """
        # BTC/USDT -> BTC_USDT
        # BTC/USDT:USDT -> BTC_USDT_USDT (合约/期权包含冒号)
        # BTC/USDT-241229-50000-C -> BTC_USDT_241229_50000_C
        symbol_clean = symbol.replace("/", "_").replace(":", "_").replace("-", "_")
        return f"{exchange}_{symbol_clean}_{timeframe}"

    def table_exists(self, exchange: str, symbol: str, timeframe: str) -> bool:
        """检查数据表是否存在"""
        table = self._table_name(exchange, symbol, timeframe)
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def save_ohlcv(
        self,
        df: pd.DataFrame,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> int:
        """
        保存K线数据到数据库（自动去重，增量插入）

        参数:
            df: K线DataFrame（index为timestamp）
            exchange: 交易所名称
            symbol: 交易对
            timeframe: K线周期

        返回:
            新插入的数据条数
        """
        if df.empty:
            log.warning(f"⚠️ 空数据，跳过保存")
            return 0

        table = self._table_name(exchange, symbol, timeframe)
        conn = self._get_connection()

        try:
            # 自动建表（如果不存在）
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS "{table}" (
                    timestamp TEXT PRIMARY KEY,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL
                )
            """)

            # 准备插入数据
            df_copy = df.copy()
            df_copy.index = df_copy.index.strftime("%Y-%m-%d %H:%M:%S")

            # 使用 INSERT OR IGNORE 自动去重
            new_count = 0
            for idx, row in df_copy.iterrows():
                try:
                    conn.execute(
                        f"""INSERT OR IGNORE INTO "{table}"
                            (timestamp, open, high, low, close, volume)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                        (str(idx), float(row["open"]), float(row["high"]),
                         float(row["low"]), float(row["close"]), float(row["volume"]))
                    )
                    if conn.changes > 0:
                        new_count += 1
                except Exception:
                    continue

            conn.commit()
            log.info(f"💾 保存到 {table}: 新增 {new_count} 条（共 {len(df)} 条输入）")
            return new_count

        except Exception as e:
            log.error(f"❌ 数据保存失败 ({table}): {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def load_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        从数据库加载K线数据

        参数:
            exchange: 交易所名称
            symbol: 交易对
            timeframe: K线周期
            start_date: 起始日期（如 "2024-01-01"）
            end_date: 结束日期（如 "2024-12-31"）
            limit: 限制返回条数（取最近N条）

        返回:
            DataFrame（index为timestamp datetime）
        """
        table = self._table_name(exchange, symbol, timeframe)

        if not self.table_exists(exchange, symbol, timeframe):
            log.warning(f"⚠️ 数据表不存在: {table}")
            return pd.DataFrame()

        conn = self._get_connection()

        try:
            # 构建SQL查询
            query = f'SELECT * FROM "{table}"'
            conditions = []
            params = []

            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date + " 23:59:59")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY timestamp ASC"

            if limit:
                # 取最近N条
                query = f"""
                    SELECT * FROM (
                        {query.replace(" ORDER BY timestamp ASC", " ORDER BY timestamp DESC")}
                        LIMIT ?
                    ) ORDER BY timestamp ASC
                """
                params.append(limit)

            df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                return pd.DataFrame()

            # 转为DataFrame标准格式
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)

            log.info(f"📖 从 {table} 加载 {len(df)} 条数据")
            return df

        except Exception as e:
            log.error(f"❌ 数据加载失败 ({table}): {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    def get_data_summary(self) -> pd.DataFrame:
        """
        获取数据库中所有数据的概览

        返回:
            DataFrame: 包含每个表的名称、数据条数、时间范围
        """
        conn = self._get_connection()

        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()

            summaries = []
            for (table,) in tables:
                try:
                    # 获取数据条数
                    count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

                    # 获取时间范围
                    first = conn.execute(
                        f'SELECT MIN(timestamp) FROM "{table}"'
                    ).fetchone()[0]
                    last = conn.execute(
                        f'SELECT MAX(timestamp) FROM "{table}"'
                    ).fetchone()[0]

                    summaries.append({
                        "表名": table,
                        "数据条数": count,
                        "最早时间": first or "--",
                        "最新时间": last or "--",
                    })
                except Exception:
                    continue

            conn.close()
            return pd.DataFrame(summaries)

        except Exception as e:
            log.error(f"获取数据库概览失败: {e}")
            conn.close()
            return pd.DataFrame()

    def delete_table(self, exchange: str, symbol: str, timeframe: str) -> bool:
        """删除指定数据表"""
        table = self._table_name(exchange, symbol, timeframe)
        conn = self._get_connection()
        try:
            conn.execute(f'DROP TABLE IF EXISTS "{table}"')
            conn.commit()
            log.info(f"🗑️ 已删除数据表: {table}")
            return True
        except Exception as e:
            log.error(f"删除失败: {e}")
            return False
        finally:
            conn.close()


# ===== 便捷函数 =====

def create_storage(db_path: str = "E:/crypto_quant/data/market.db") -> DataStorage:
    """快速创建存储管理器"""
    return DataStorage(db_path)
