# CLAUDE.md — 加密货币量化交易系统 (CryptoQuant)

## 语言要求
**Always respond in Chinese. 始终用中文回复。所有解释、注释、对话都使用中文。**

## 项目概况
- **技术栈**: Python 3.13 + Streamlit + CCXT + pandas + Plotly + SQLite
- **入口**: `启动.bat` 或 `python 启动.py`
- **配置**: `config/settings.yaml`（代理、风控参数）

## 项目结构
```
├── data/              # 数据层 (fetcher + storage + manager)
├── strategy/          # 策略层 (base + factors + signals + examples/)
├── backtest/          # 回测 (engine + broker + metrics)
├── execution/         # 执行层 (trader + paper_trader + risk)
├── factor_builder/    # 策略生成器 (templates + parser + generator)
├── ui/                # Streamlit 界面 (app.py + pages/ + components/)
└── utils/             # 工具 (logger + helpers)
```

## 关键设计约束
- **纯本地回测**: 回测页面只用 `DataStorage` 从 SQLite 只读，不触发网络请求（`auto_sync=False`）
- **代理**: `config/settings.yaml` 中 `proxy.enabled: true`（默认 `http://127.0.0.1:7897`）
- **主题**: 全局浅色主题（白底 `#FAFBFC`、黑字 `#1A1A1A`、蓝按钮 `#2E86C1`）
- **策略元数据**: 保存时在 .py 文件头注入 `# 用户描述:` `# 匹配模板:` 注释行

## 修改注意事项
- 修改 .py 文件后需清除 `__pycache__`，否则可能报 ImportError
- 回测相关改动不要引入网络依赖
- pandas 在开发沙箱中可能有问题（C 扩展崩溃），但用户实机正常
- 颜色遵循：页面白底 → 容器浅灰（色差小），文字黑（对比强），警告容器 → 红/橙色底 + 黑字
