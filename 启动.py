"""
加密货币量化交易系统 - Python启动脚本（备用方案）
如果 启动.bat 出现编码问题，可以用这个：

使用方法：
    python 启动.py
    或
    python "E:\crypto_quant\启动.py"
"""

import subprocess
import sys
import os

# 切换到项目目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("  Crypto Quantitative Trading System")
print("  " + "*" * 34)
print("=" * 50)
print()

# 检查依赖
print("[INFO] Checking dependencies...")
try:
    import streamlit
    import ccxt
    import pandas
    import plotly
    print(f"[OK] Streamlit {streamlit.__version__}, CCXT {ccxt.__version__}")
except ImportError as e:
    print(f"[WARN] Missing dependency: {e}")
    print("[INFO] Installing dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        # 尝试国内镜像
        print("[WARN] Trying Tsinghua mirror...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt",
            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
        ])
    print("[OK] Dependencies installed")
    print()

print("[INFO] Starting CryptoQuant...")
print("[INFO] Open http://localhost:8501 in your browser")
print("[INFO] Press Ctrl+C to stop")
print()

# 启动 Streamlit
args = [
    sys.executable, "-m", "streamlit", "run", "ui/app.py",
    "--server.headless", "true",
    "--server.port", "8501",
]
subprocess.run(args)
