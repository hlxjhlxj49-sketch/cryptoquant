"""
日志模块
提供统一的日志记录功能，支持控制台输出和文件记录
"""

import logging
import os
from datetime import datetime

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# 日志文件路径（按日期命名）
log_file = os.path.join(LOG_DIR, f"crypto_quant_{datetime.now().strftime('%Y%m%d')}.log")


def setup_logger(name: str = "crypto_quant", level: int = logging.INFO) -> logging.Logger:
    """
    创建日志记录器

    参数:
        name: 日志记录器名称
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）

    返回:
        配置好的Logger对象
    """
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# 全局默认logger
log = setup_logger()
