"""
通用工具函数
"""

import yaml
import os
from typing import Dict, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载YAML配置文件

    参数:
        config_path: 配置文件路径，默认为项目根目录下的 config/settings.yaml

    返回:
        配置字典
    """
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "settings.yaml",
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def save_config(config: Dict[str, Any], config_path: str = None) -> None:
    """
    保存配置到YAML文件

    参数:
        config: 配置字典
        config_path: 配置文件路径
    """
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "settings.yaml",
        )

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def format_number(num: float, decimals: int = 2) -> str:
    """
    格式化数字显示

    参数:
        num: 数字
        decimals: 小数位数

    返回:
        格式化后的字符串，如 "12,345.67"
    """
    if num is None:
        return "--"
    return f"{num:,.{decimals}f}"


def format_percent(pct: float, decimals: int = 2) -> str:
    """
    格式化百分比显示

    参数:
        pct: 百分比值（如 5.23 表示 5.23%）
        decimals: 小数位数

    返回:
        格式化后的字符串，如 "+5.23%" 或 "-3.15%"
    """
    if pct is None:
        return "--"
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.{decimals}f}%"


def truncate_string(text: str, max_len: int = 20) -> str:
    """
    截断过长字符串

    参数:
        text: 原始字符串
        max_len: 最大长度

    返回:
        截断后的字符串
    """
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def get_proxy_config() -> Dict[str, str]:
    """
    从配置文件读取代理设置

    返回:
        {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
        如果配置中未启用代理，返回空字典
    """
    try:
        config = load_config()
        proxy = config.get("proxy", {})
        if proxy.get("enabled", False):
            result = {}
            if proxy.get("http"):
                result["http"] = proxy["http"]
            if proxy.get("https"):
                result["https"] = proxy["https"]
            return result
    except Exception:
        pass
    return {}
