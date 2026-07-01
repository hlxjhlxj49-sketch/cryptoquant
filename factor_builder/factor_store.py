"""
因子保存库 — 用户自定义因子的 CRUD 操作

存储结构（镜像 strategy/user_strategies/）:
  factor_builder/user_factors/
  ├── 我的MA7快线/
  │   ├── factor.json    # 因子定义
  │   └── meta.json      # 元数据
  └── 趋势类/            # 分类文件夹
      └── .category
"""

import os
import re
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional


# ============================================================
# 内置因子清单（供因子面板使用）
# ============================================================

BUILTIN_FACTORS = [
    # 📈 趋势类
    {"type": "MA", "name": "简单移动均线", "category": "趋势",
     "params": {"period": 20, "column": "close"},
     "description": "反映价格的平均走势，最基础的趋势指标"},
    {"type": "EMA", "name": "指数移动均线", "category": "趋势",
     "params": {"period": 12, "column": "close"},
     "description": "比MA更灵敏，近期价格权重更高"},
    {"type": "MACD", "name": "MACD", "category": "趋势",
     "params": {"fast": 12, "slow": 26, "signal": 9},
     "description": "判断趋势方向和强度，金叉/死叉信号"},
    {"type": "ADX", "name": "平均趋向指数", "category": "趋势",
     "params": {"period": 14},
     "description": "衡量趋势强度（不判断方向），>25强趋势"},

    # 🔄 震荡类
    {"type": "KDJ", "name": "KDJ随机指标", "category": "震荡",
     "params": {"n": 9, "m1": 3, "m2": 3},
     "description": "超买超卖判断：K>80超买，K<20超卖"},
    {"type": "RSI", "name": "相对强弱指标", "category": "震荡",
     "params": {"period": 14},
     "description": "衡量价格变动速度：>70超买，<30超卖"},
    {"type": "Stochastic", "name": "慢速随机指标", "category": "震荡",
     "params": {"k_period": 14, "d_period": 3},
     "description": "与KDJ类似，判断超买超卖区域"},
    {"type": "CCI", "name": "商品通道指数", "category": "震荡",
     "params": {"period": 20},
     "description": ">100超买，<-100超卖"},

    # 📊 波动类
    {"type": "BOLL", "name": "布林带", "category": "波动",
     "params": {"period": 20, "std_dev": 2.0},
     "description": "价格触及上轨可能回调，触及下轨可能反弹"},
    {"type": "ATR", "name": "平均真实波幅", "category": "波动",
     "params": {"period": 14},
     "description": "衡量市场波动性，常用于设置止损距离"},

    # 📉 成交量类
    {"type": "Volume_MA", "name": "成交量均线", "category": "成交量",
     "params": {"period": 20},
     "description": "成交量>均量=放量，<均量=缩量"},
    {"type": "OBV", "name": "能量潮", "category": "成交量",
     "params": {},
     "description": "通过成交量变化判断资金流向"},
    {"type": "VWAP", "name": "成交量加权均价", "category": "成交量",
     "params": {},
     "description": "机构交易者常用参考价，>VWAP买方占优"},
]

# 条件类型
CONDITION_TYPES = [
    {"type": "CROSSOVER", "name": "上穿 (金叉)", "icon": "🔺"},
    {"type": "CROSSUNDER", "name": "下穿 (死叉)", "icon": "🔻"},
    {"type": "GREATER", "name": "大于 (>）", "icon": ">"},
    {"type": "LESS", "name": "小于 (<）", "icon": "<"},
    {"type": "AND", "name": "且 (AND)", "icon": "&"},
    {"type": "OR", "name": "或 (OR)", "icon": "|"},
]


def _get_user_factors_dir() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "user_factors",
    )


# ============================================================
# CRUD
# ============================================================

def save_user_factor(
    name: str,
    factor_def: Dict,
    description: str = "",
    category: str = "",
) -> str:
    """保存用户自定义因子"""
    base_dir = _get_user_factors_dir()
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', name).strip()
    folder = os.path.join(base_dir, safe_name)
    os.makedirs(folder, exist_ok=True)

    with open(os.path.join(folder, "factor.json"), "w", encoding="utf-8") as f:
        json.dump(factor_def, f, ensure_ascii=False, indent=2)

    meta = {
        "name": name,
        "description": description,
        "category": category,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(os.path.join(folder, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return folder


def list_user_factors() -> List[Dict]:
    """列出所有用户因子（含内置因子清单）"""
    results = list(BUILTIN_FACTORS)  # 内置因子始终可用

    base_dir = _get_user_factors_dir()
    if not os.path.exists(base_dir):
        return results

    for entry in sorted(os.listdir(base_dir)):
        full = os.path.join(base_dir, entry)
        if not os.path.isdir(full) or entry.startswith("."):
            continue
        fp = os.path.join(full, "factor.json")
        mp = os.path.join(full, "meta.json")
        if not os.path.exists(fp):
            continue

        try:
            with open(fp, "r", encoding="utf-8") as f:
                factor_def = json.load(f)
        except Exception:
            continue

        meta = {}
        if os.path.exists(mp):
            try:
                with open(mp, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                pass

        is_category = os.path.exists(os.path.join(full, ".category"))

        results.append({
            "type": factor_def.get("type", "unknown"),
            "name": meta.get("name", entry),
            "category": meta.get("category", factor_def.get("category", "自定义")),
            "params": factor_def.get("params", {}),
            "description": meta.get("description", factor_def.get("description", "")),
            "display_name": factor_def.get("display_name", entry),
            "path": full,
            "is_builtin": False,
            "is_category": is_category,
            "is_combo": factor_def.get("type") == "combo",
            "modified": meta.get("modified", ""),
        })

    return results


def load_user_factor(path: str) -> Dict:
    """加载因子定义"""
    fp = os.path.join(path, "factor.json") if os.path.isdir(path) else path
    if not os.path.exists(fp):
        return {}
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_user_factor(path: str) -> bool:
    """删除因子文件夹"""
    if not os.path.exists(path):
        return False
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    return True


def rename_user_factor(path: str, new_name: str) -> str:
    """重命名因子文件夹"""
    if not os.path.exists(path):
        return ""
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', new_name).strip()
    parent = os.path.dirname(path)
    new_path = os.path.join(parent, safe_name)
    try:
        os.rename(path, new_path)
    except OSError:
        return ""
    # update meta.json
    mp = os.path.join(new_path, "meta.json")
    if os.path.exists(mp):
        try:
            with open(mp, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["name"] = new_name
            meta["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(mp, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return new_path


def create_factor_category(name: str) -> str:
    """创建因子分类文件夹"""
    base_dir = _get_user_factors_dir()
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', name).strip()
    folder = os.path.join(base_dir, safe_name)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, ".category"), "w") as f:
        f.write("")
    return folder
