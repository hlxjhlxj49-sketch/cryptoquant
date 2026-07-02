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
    获取代理设置（环境变量优先，配置文件兜底）

    Docker 容器内通过环境变量传入 host.docker.internal:7897
    本地运行读取 config/settings.yaml 中的 127.0.0.1:7897

    返回:
        {"http": "...", "https": "..."}  或空字典
    """
    # 优先使用环境变量（Docker 模式）
    env_http = os.environ.get("http_proxy", "") or os.environ.get("HTTP_PROXY", "")
    env_https = os.environ.get("https_proxy", "") or os.environ.get("HTTPS_PROXY", "")
    if env_http or env_https:
        result = {}
        if env_http:
            result["http"] = env_http
        if env_https:
            result["https"] = env_https
        return result

    # 回退到配置文件（本地模式）
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
