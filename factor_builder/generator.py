"""
策略代码生成器 + 策略库管理
将用户描述 + 匹配的模板 → 生成完整的策略Python代码
管理策略文件夹结构、删除、重命名、分类
"""

import os
import re
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from factor_builder.templates import search_templates, get_all_templates
from factor_builder.parser import parse, extract_params


# 用户策略根目录（文件夹结构）
def _get_user_strategies_dir() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "strategy", "user_strategies",
    )


def _get_preset_dir() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "strategy", "examples",
    )


def _to_class_name(name: str) -> str:
    """将中文名称转为合法的Python类名"""
    if re.match(r'^[A-Z][a-zA-Z0-9_]*$', name):
        return name
    timestamp = datetime.now().strftime("%H%M%S")
    return f"CustomStrategy_{timestamp}"


# ============================================================
# 策略代码生成
# ============================================================

def generate_strategy_code(
    user_input: str,
    template_name: Optional[str] = None,
    params_override: Optional[Dict] = None,
) -> Dict:
    """根据用户描述生成策略代码"""
    parsed = parse(user_input)

    if template_name:
        templates = [t for t in get_all_templates() if t["name"] == template_name]
    else:
        templates = search_templates(user_input)

    if not templates:
        templates = [t for t in get_all_templates() if t["name"] == "双均线金叉死叉"]

    template = templates[0]
    params = dict(template["default_params"])
    for indicator in parsed.indicators:
        extracted = extract_params(user_input, indicator["name"])
        params.update(extracted)
    if params_override:
        params.update(params_override)

    class_name = _to_class_name(template["name"])
    code = template["code_template"]
    code = code.replace("{name}", template["name"])
    code = code.replace("{description}", template["description"])
    code = code.replace("{class_name}", class_name)
    for key, value in params.items():
        code = code.replace(f"{{{key}}}", str(value))

    header = f"""# ============================================================
# 自动生成的策略代码
# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# 用户描述: {user_input}
# 匹配模板: {template['name']}
# ============================================================

"""
    code = header + code

    return {
        "code": code,
        "template": template["name"],
        "params": params,
        "description": template["description"],
        "class_name": class_name,
    }


# ============================================================
# 策略存储（文件夹结构）
# ============================================================

def save_strategy(code: str, name: str, output_dir: str = None) -> str:
    """兼容旧API：扁平保存到 examples/"""
    if output_dir is None:
        output_dir = _get_preset_dir()
    os.makedirs(output_dir, exist_ok=True)
    safe_name = re.sub(r'[^\w\-_]', '_', name)
    filename = f"{safe_name}.py"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    return filepath


def save_strategy_with_meta(
    code: str,
    name: str,
    description: str = "",
    template: str = "",
    category: str = "",
) -> str:
    """
    保存策略到文件夹结构

    创建 user_strategies/{name}/ 文件夹，内含:
      - strategy.py    策略代码
      - meta.json      元数据 {name, description, template, created, category}

    返回: 策略文件夹路径
    """
    base_dir = _get_user_strategies_dir()
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', name).strip()
    folder = os.path.join(base_dir, safe_name)
    os.makedirs(folder, exist_ok=True)

    # 写入策略代码
    strategy_path = os.path.join(folder, "strategy.py")
    with open(strategy_path, "w", encoding="utf-8") as f:
        f.write(code)

    # 写入元数据
    meta = {
        "name": name,
        "description": description,
        "template": template,
        "category": category,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    meta_path = os.path.join(folder, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return folder


# ============================================================
# 策略列表（递归扫描）
# ============================================================

def _read_meta(folder: str) -> Dict:
    """读取策略文件夹的 meta.json"""
    meta_path = os.path.join(folder, "meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _is_strategy_folder(folder: str) -> bool:
    """判断是否为策略文件夹（含 strategy.py）"""
    return os.path.exists(os.path.join(folder, "strategy.py"))


def _is_category_folder(folder: str) -> bool:
    """判断是否为分类文件夹（含 .category 标记 或 不含 strategy.py）"""
    return os.path.exists(os.path.join(folder, ".category"))


def list_generated_strategies(include_preset: bool = False) -> List[Dict]:
    """
    列出所有用户策略（文件夹结构 + 旧扁平结构兼容）

    返回:
        [{"name": str, "path": str, "is_generated": bool,
          "is_category": bool, "children": [...], "modified": str,
          "description": str, "template": str}, ...]
    """
    results = []

    # ---- 1. 扫描新文件夹结构 ----
    base_dir = _get_user_strategies_dir()
    if os.path.exists(base_dir):
        for entry in sorted(os.listdir(base_dir)):
            full = os.path.join(base_dir, entry)
            if not os.path.isdir(full):
                continue
            if entry.startswith(".") or entry == "__pycache__":
                continue

            if _is_category_folder(full):
                # 分类文件夹
                children = _scan_children(full)
                meta = _read_meta(full)
                results.append({
                    "name": entry,
                    "path": full,
                    "is_generated": True,
                    "is_category": True,
                    "children": children,
                    "modified": meta.get("modified", ""),
                    "description": meta.get("description", ""),
                    "template": meta.get("template", ""),
                })
            elif _is_strategy_folder(full):
                meta = _read_meta(full)
                results.append({
                    "name": meta.get("name", entry),
                    "display_name": meta.get("template") or meta.get("name", entry),
                    "path": full,
                    "is_generated": True,
                    "is_category": False,
                    "children": [],
                    "modified": meta.get("modified", ""),
                    "description": meta.get("description", ""),
                    "template": meta.get("template", ""),
                })

    # ---- 2. 兼容旧扁平结构 (strategy/examples/) ----
    old_dir = _get_preset_dir()
    if os.path.exists(old_dir):
        for fname in sorted(os.listdir(old_dir)):
            if not fname.endswith(".py") or fname == "__init__.py":
                continue
            fpath = os.path.join(old_dir, fname)
            # 排除预置示例
            preset_names = {"ma_cross.py", "rsi_strategy.py", "grid_trading.py"}
            if fname in preset_names:
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                first_line = f.readline()
                is_generated = "自动生成的策略代码" in first_line
            results.append({
                "name": fname.replace(".py", ""),
                "display_name": fname.replace(".py", ""),
                "path": fpath,
                "is_generated": is_generated,
                "is_category": False,
                "children": [],
                "modified": datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M"),
                "description": "",
                "template": "",
                "_legacy": True,
            })

    return sorted(results, key=lambda x: (
        not x["is_category"],  # 分类先显示
        x["name"],
    ))


def _scan_children(parent_dir: str) -> List[Dict]:
    """递归扫描分类文件夹下的子策略"""
    children = []
    if not os.path.isdir(parent_dir):
        return children
    for entry in sorted(os.listdir(parent_dir)):
        full = os.path.join(parent_dir, entry)
        if not os.path.isdir(full) or entry.startswith("."):
            continue
        if _is_strategy_folder(full):
            meta = _read_meta(full)
            children.append({
                "name": meta.get("name", entry),
                "display_name": meta.get("template") or meta.get("name", entry),
                "path": full,
                "is_generated": True,
                "is_category": False,
                "modified": meta.get("modified", ""),
                "description": meta.get("description", ""),
                "template": meta.get("template", ""),
            })
    return children


# ============================================================
# 策略读取
# ============================================================

def load_strategy_code(filepath: str) -> str:
    """加载策略代码（兼容文件夹和扁平结构）"""
    if os.path.isdir(filepath):
        py_path = os.path.join(filepath, "strategy.py")
        if os.path.exists(py_path):
            filepath = py_path
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def extract_strategy_info(filepath: str) -> Dict:
    """
    从策略文件夹/.py 文件提取结构化信息

    优先读取 meta.json，回退到头部注释解析
    """
    # 优先读 meta.json
    if os.path.isdir(filepath):
        meta = _read_meta(filepath)
        if meta:
            code = load_strategy_code(filepath)
            return {
                "name": meta.get("name", ""),
                "display_name": meta.get("template") or meta.get("name", ""),
                "description": meta.get("description", ""),
                "template": meta.get("template", ""),
                "code": code,
                "generated_time": meta.get("created", ""),
            }

    # 回退：旧扁平 .py 文件
    code = load_strategy_code(filepath)
    if not code:
        return {"name": "", "display_name": "", "description": "",
                "template": "", "code": "", "generated_time": ""}

    info = {
        "name": os.path.splitext(os.path.basename(filepath))[0],
        "display_name": "",
        "description": "",
        "template": "",
        "code": code,
        "generated_time": "",
    }
    for line in code.split("\n")[:20]:
        line = line.strip()
        if line.startswith("# 用户描述:"):
            info["description"] = line.replace("# 用户描述:", "").strip()
        elif line.startswith("# 匹配模板:"):
            info["template"] = line.replace("# 匹配模板:", "").strip()
        elif line.startswith("# 生成时间:"):
            info["generated_time"] = line.replace("# 生成时间:", "").strip()

    if info["template"]:
        info["display_name"] = info["template"]
    elif info["description"]:
        info["display_name"] = info["description"][:30]
    else:
        info["display_name"] = info["name"]

    if not info["description"]:
        match = re.search(r'"""(.*?)"""', code, re.DOTALL)
        if match:
            doc = match.group(1).strip()
            for doc_line in doc.split("\n"):
                doc_line = doc_line.strip()
                if doc_line and not doc_line.startswith("参数") and not doc_line.startswith("描述"):
                    info["description"] = doc_line
                    break
    return info


def update_strategy_description(filepath: str, description: str) -> None:
    """更新策略描述"""
    if os.path.isdir(filepath):
        meta = _read_meta(filepath)
        meta["description"] = description
        meta["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join(filepath, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        return
    # 旧扁平文件
    code = load_strategy_code(filepath)
    if not code:
        return
    lines = code.split("\n")
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("# 用户描述:") and not found:
            new_lines.append(f"# 用户描述: {description}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        output = []
        for line in new_lines:
            output.append(line)
            if line.startswith("# ======="):
                output.insert(-1, f"# 用户描述: {description}")
        final_code = "\n".join(output)
    else:
        final_code = "\n".join(new_lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_code)


# ============================================================
# 策略管理（删除、重命名、分类）
# ============================================================

def delete_strategy(folder_path: str) -> bool:
    """
    删除策略文件夹（含 strategy.py + meta.json）

    返回: True 成功
    """
    if not os.path.exists(folder_path):
        return False
    if os.path.isdir(folder_path):
        shutil.rmtree(folder_path)
    else:
        os.remove(folder_path)
    return True


def rename_strategy(folder_path: str, new_name: str) -> str:
    """
    重命名策略文件夹 + 更新 meta.json

    返回: 新路径
    """
    if not os.path.exists(folder_path):
        return ""

    safe_name = re.sub(r'[\\/:*?"<>|]', '_', new_name).strip()
    parent = os.path.dirname(folder_path)
    new_path = os.path.join(parent, safe_name)

    try:
        os.rename(folder_path, new_path)
    except OSError:
        return ""

    # 更新 meta.json
    meta = _read_meta(new_path)
    meta["name"] = new_name
    meta["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_path = os.path.join(new_path, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return new_path


def create_category(name: str) -> str:
    """
    创建分类文件夹

    返回: 文件夹路径
    """
    base_dir = _get_user_strategies_dir()
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', name).strip()
    folder = os.path.join(base_dir, safe_name)
    os.makedirs(folder, exist_ok=True)

    # 标记为分类文件夹
    marker = os.path.join(folder, ".category")
    with open(marker, "w") as f:
        f.write("")

    return folder


def move_strategy(folder_path: str, target_category: str) -> str:
    """
    将策略文件夹移动到目标分类下

    返回: 新路径
    """
    if not os.path.exists(folder_path):
        return ""

    base_dir = _get_user_strategies_dir()
    target_dir = os.path.join(base_dir, target_category)
    if not os.path.exists(target_dir):
        return ""

    folder_name = os.path.basename(folder_path)
    new_path = os.path.join(target_dir, folder_name)
    try:
        shutil.move(folder_path, new_path)
    except shutil.Error:
        return ""
    return new_path


# ============================================================
# 数据迁移
# ============================================================

def migrate_legacy_strategies() -> int:
    """
    将 strategy/examples/ 中的旧扁平 .py 策略迁移到 user_strategies/

    预置示例 (ma_cross, rsi_strategy, grid_trading) 不迁移

    返回: 迁移数量
    """
    old_dir = _get_preset_dir()
    new_dir = _get_user_strategies_dir()

    if not os.path.exists(old_dir):
        return 0

    preset_names = {"ma_cross.py", "rsi_strategy.py", "grid_trading.py", "__init__.py"}
    migrated = 0

    for fname in sorted(os.listdir(old_dir)):
        if fname in preset_names or not fname.endswith(".py"):
            continue
        fpath = os.path.join(old_dir, fname)
        if not os.path.isfile(fpath):
            continue

        code = load_strategy_code(fpath)
        if not code:
            continue

        info = extract_strategy_info(fpath)
        strategy_name = info.get("display_name") or fname.replace(".py", "")

        # 如果目标已存在，跳过
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', strategy_name).strip()
        target_folder = os.path.join(new_dir, safe_name)
        if os.path.exists(target_folder):
            continue

        save_strategy_with_meta(
            code=code,
            name=strategy_name,
            description=info.get("description", ""),
            template=info.get("template", ""),
        )
        migrated += 1

    return migrated
