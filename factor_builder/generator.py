"""
策略代码生成器
将用户描述 + 匹配的模板 → 生成完整的策略Python代码
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional
from factor_builder.templates import search_templates, get_all_templates
from factor_builder.parser import parse, extract_params


def _to_class_name(name: str) -> str:
    """
    将中文名称转为合法的Python类名

    示例:
        双均线金叉死叉 → MACrossGoldenDeathStrategy
    """
    # 如果已经是英文类名格式，直接返回
    if re.match(r'^[A-Z][a-zA-Z0-9_]*$', name):
        return name

    # 中英文混合，生成唯一名称
    # 使用时间戳确保不重复
    timestamp = datetime.now().strftime("%H%M%S")
    return f"CustomStrategy_{timestamp}"


def generate_strategy_code(
    user_input: str,
    template_name: Optional[str] = None,
    params_override: Optional[Dict] = None,
) -> Dict:
    """
    根据用户描述生成策略代码

    参数:
        user_input: 用户的自然语言描述
        template_name: 强制使用某个模板（None则自动匹配）
        params_override: 手动覆盖参数

    返回:
        {
            "code": str,           # 生成的Python策略代码
            "template": str,       # 使用的模板名称
            "params": dict,        # 使用的参数
            "description": str,    # 策略描述
        }
    """
    # 1. 解析用户输入
    parsed = parse(user_input)

    # 2. 匹配模板
    if template_name:
        # 手动指定模板
        templates = [t for t in get_all_templates() if t["name"] == template_name]
    else:
        # 自动搜索匹配
        templates = search_templates(user_input)

    if not templates:
        # 无匹配模板：使用默认的双均线策略
        templates = [t for t in get_all_templates() if t["name"] == "双均线金叉死叉"]

    template = templates[0]

    # 3. 提取参数
    params = dict(template["default_params"])  # 默认参数
    for indicator in parsed.indicators:
        extracted = extract_params(user_input, indicator["name"])
        params.update(extracted)

    # 用户手动覆盖
    if params_override:
        params.update(params_override)

    # 4. 生成类名
    class_name = _to_class_name(template["name"])

    # 5. 填充模板
    code = template["code_template"]
    code = code.replace("{name}", template["name"])
    code = code.replace("{description}", template["description"])
    code = code.replace("{class_name}", class_name)

    # 填充参数（模板中使用 {param_name} 格式）
    for key, value in params.items():
        code = code.replace(f"{{{key}}}", str(value))

    # 6. 添加生成标记
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


def save_strategy(code: str, name: str, output_dir: str = None) -> str:
    """
    保存策略代码到文件

    参数:
        code: 策略Python代码
        name: 策略名称（用作文件名）
        output_dir: 输出目录（默认为 strategy/examples/）

    返回:
        保存的文件路径
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "strategy", "examples",
        )

    os.makedirs(output_dir, exist_ok=True)

    # 生成安全的文件名
    safe_name = re.sub(r'[^\w\-_]', '_', name)
    filename = f"{safe_name}.py"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)

    return filepath


def list_generated_strategies(output_dir: str = None) -> List[Dict]:
    """
    列出所有已生成的策略文件

    返回:
        [{"name": ..., "path": ..., "modified": ...}, ...]
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "strategy", "examples",
        )

    if not os.path.exists(output_dir):
        return []

    strategies = []
    for fname in os.listdir(output_dir):
        if fname.endswith(".py") and fname != "__init__.py":
            fpath = os.path.join(output_dir, fname)
            # 检查是否为自动生成的
            with open(fpath, "r", encoding="utf-8") as f:
                first_line = f.readline()
                is_generated = "自动生成的策略代码" in first_line

            strategies.append({
                "name": fname.replace(".py", ""),
                "path": fpath,
                "is_generated": is_generated,
                "modified": datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M"),
            })

    return sorted(strategies, key=lambda x: x["modified"], reverse=True)


def load_strategy_code(filepath: str) -> str:
    """
    加载已保存的策略代码

    参数:
        filepath: 策略文件路径

    返回:
        Python代码字符串
    """
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def extract_strategy_info(filepath: str) -> Dict:
    """
    从已保存的策略 .py 文件中提取结构化信息

    解析文件头部的元数据注释（由 generate_strategy_code 生成）：
      # 用户描述: xxx
      # 匹配模板: xxx

    再从 docstring 中提取描述，从 class 定义提取类名

    参数:
        filepath: 策略 .py 文件路径

    返回:
        {
            "name": str,            # 策略名称（类名）
            "display_name": str,    # 显示名称（模板名或类名）
            "description": str,     # 策略描述（来自用户描述或docstring）
            "template": str,        # 匹配的模板名
            "code": str,            # 完整代码
            "generated_time": str,  # 生成时间
        }
    """
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

    for line in code.split("\n")[:20]:  # 只扫描头部
        line = line.strip()
        if line.startswith("# 用户描述:"):
            info["description"] = line.replace("# 用户描述:", "").strip()
        elif line.startswith("# 匹配模板:"):
            info["template"] = line.replace("# 匹配模板:", "").strip()
        elif line.startswith("# 生成时间:"):
            info["generated_time"] = line.replace("# 生成时间:", "").strip()

    # 如果头部有模板名，优先当作显示名
    if info["template"]:
        info["display_name"] = info["template"]
    elif info["description"]:
        info["display_name"] = info["description"][:30]
    else:
        info["display_name"] = info["name"]

    # 如果没有 description，尝试从 docstring 提取
    if not info["description"]:
        match = re.search(r'"""(.*?)"""', code, re.DOTALL)
        if match:
            doc = match.group(1).strip()
            # 取第一行非空内容
            for doc_line in doc.split("\n"):
                doc_line = doc_line.strip()
                if doc_line and not doc_line.startswith("参数") and not doc_line.startswith("描述"):
                    info["description"] = doc_line
                    break

    return info


def update_strategy_description(filepath: str, description: str) -> None:
    """
    在已有策略文件中追加或更新用户描述元数据行

    参数:
        filepath: 策略文件路径
        description: 用户原始描述
    """
    code = load_strategy_code(filepath)
    if not code:
        return

    lines = code.split("\n")
    new_lines = []
    found_desc = False
    inserted = False

    for line in lines:
        if line.startswith("# 用户描述:") and not inserted:
            new_lines.append(f"# 用户描述: {description}")
            found_desc = True
            inserted = True
        else:
            new_lines.append(line)

    # 如果文件中不存在该行，在文件头注释区域末尾插入
    if not found_desc:
        output = []
        header_done = False
        for line in new_lines:
            output.append(line)
            if not header_done and line.startswith("# ======="):
                output.insert(-1, f"# 用户描述: {description}")
                header_done = True

        final_code = "\n".join(output)
    else:
        final_code = "\n".join(new_lines)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_code)


def save_strategy_with_meta(
    code: str,
    name: str,
    description: str = "",
    template: str = "",
    output_dir: str = None,
) -> str:
    """
    保存策略代码并附带结构化元数据

    参数:
        code: 策略Python代码
        name: 策略名称（用作文件名）
        description: 用户原始策略描述
        template: 匹配的模板名
        output_dir: 输出目录

    返回:
        保存的文件路径
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "strategy", "examples",
        )

    os.makedirs(output_dir, exist_ok=True)

    safe_name = re.sub(r'[^\w\-_]', '_', name)
    filename = f"{safe_name}.py"
    filepath = os.path.join(output_dir, filename)

    # 如果 code 已有元数据头则直接用，否则插入
    if "# 用户描述:" not in code and description:
        # 在第一个 """ 之前插入元数据行
        lines = code.split("\n")
        new_lines = []
        inserted = False
        for line in lines:
            if not inserted and line.strip().startswith('"""'):
                new_lines.append(f"# 用户描述: {description}")
                if template:
                    new_lines.append(f"# 匹配模板: {template}")
                new_lines.append(f"# 保存时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                inserted = True
            new_lines.append(line)
        code = "\n".join(new_lines)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)

    return filepath
