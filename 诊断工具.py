"""
网络诊断工具 - 检查交易所连接问题
用法: python "E:\crypto_quant\诊断工具.py"
"""

import sys
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("  🔍 加密货币量化交易系统 - 网络诊断工具")
print("=" * 60)
print()

# ===== 1. 检查Python版本 =====
print("【1/6】检查 Python 版本...")
import platform
print(f"  Python: {sys.version}")
print(f"  系统: {platform.platform()}")
print()

# ===== 2. 检查依赖包 =====
print("【2/6】检查依赖包...")
deps = {
    "ccxt": "交易所API",
    "pandas": "数据处理",
    "streamlit": "Web界面",
    "plotly": "图表",
    "numpy": "数值计算",
}
all_ok = True
for pkg, desc in deps.items():
    try:
        mod = __import__(pkg)
        version = getattr(mod, "__version__", "unknown")
        print(f"  ✅ {pkg} {version} ({desc})")
    except ImportError:
        print(f"  ❌ {pkg} 未安装 ({desc})")
        all_ok = False

if not all_ok:
    print()
    print("  💡 请运行: pip install -r requirements.txt")
    sys.exit(1)
print()

# ===== 3. 检查网络连通性 =====
print("【3/6】检查基础网络连接...")
import socket
test_hosts = [
    ("www.baidu.com", 80, "百度"),
    ("api.binance.com", 443, "币安API"),
    ("www.okx.com", 443, "OKX"),
]
for host, port, name in test_hosts:
    try:
        sock = socket.create_connection((host, port), timeout=5)
        sock.close()
        print(f"  ✅ {name} ({host}:{port}) - 直连可达")
    except Exception as e:
        print(f"  ⚠️ {name} ({host}:{port}) - 直连不可达: {e}")
print()

# ===== 4. 检查代理环境变量 =====
print("【4/6】检查代理配置...")
proxy_vars = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]
found_proxy = False
for var in proxy_vars:
    val = os.environ.get(var, "")
    if val:
        print(f"  ✅ {var} = {val}")
        found_proxy = True

if not found_proxy:
    print("  ⚠️ 系统环境变量中未检测到代理设置")
    print("  💡 Clash 默认代理地址通常是 http://127.0.0.1:7890")
    print("  💡 确认 Clash 已开启「系统代理」或「TUN模式」")
print()

# ===== 5. 测试Clash代理端口 =====
print("【5/6】探测 Clash 代理端口...")
common_clash_ports = [7890, 7891, 7892, 9090, 8080]
clash_found = False
for port in common_clash_ports:
    try:
        sock = socket.create_connection(("127.0.0.1", port), timeout=1)
        sock.close()
        print(f"  ✅ 端口 {port} 开放 → 代理地址: http://127.0.0.1:{port}")
        clash_found = True
        clash_port = port
        break
    except:
        pass

if not clash_found:
    print("  ❌ 未找到 Clash 代理端口")
    print("  常见 Clash 端口: 7890, 7891")
    print("  请检查 Clash 是否正在运行")
    print()
    print("  如果使用其他代理软件:")
    print("    V2Ray: 通常是 10809")
    print("    SSR: 通常是 1080")
    print("    Trojan: 通常是 10808")
    clash_port = 7890
print()

# ===== 6. 通过代理测试交易所连接 =====
print(f"【6/6】通过代理测试交易所连接...")

import ccxt

# 要测试的交易所
exchanges_to_test = ["binance", "okx", "bybit", "gate"]

for ex_name in exchanges_to_test:
    print(f"\n--- {ex_name} ---")
    try:
        exchange_class = getattr(ccxt, ex_name)
    except AttributeError:
        print(f"  ❌ CCXT不支持该交易所")
        continue

    # 测试1: 直连
    print(f"  ① 直连...")
    try:
        ex = exchange_class({"enableRateLimit": True, "timeout": 10000})
        t = ex.fetch_time()
        print(f"  ✅ 直连成功! 服务器时间: {t}")
    except Exception as e:
        err_msg = str(e)[:120]
        print(f"  ❌ 直连失败: {err_msg}")

    # 测试2: 通过代理
    if clash_found:
        proxy_url = f"http://127.0.0.1:{clash_port}"
        proxies = {"http": proxy_url, "https": proxy_url}
        print(f"  ② 通过代理 {proxy_url}...")
        try:
            ex = exchange_class({
                "enableRateLimit": True,
                "timeout": 15000,
                "proxies": proxies,
            })
            t = ex.fetch_time()
            print(f"  ✅ 代理连接成功! 服务器时间: {t}")

            # 进一步测试: 获取交易对
            print(f"  ③ 获取BTC/USDT行情...")
            try:
                ticker = ex.fetch_ticker("BTC/USDT")
                print(f"  ✅ 行情获取成功!")
                print(f"     BTC价格: ${ticker.get('last', 'N/A')}")
                print(f"     24h涨跌: {ticker.get('percentage', 'N/A')}%")
            except Exception as e:
                print(f"  ❌ 行情获取失败: {str(e)[:120]}")
        except Exception as e:
            err_msg = str(e)[:120]
            print(f"  ❌ 代理连接失败: {err_msg}")
    else:
        print(f"  ② 跳过代理测试（未找到Clash端口）")

print()
print("=" * 60)
print("  诊断完成！")
print()
print("  如果以上全部失败，可能的原因:")
print("  1. Clash 没有开启「系统代理」或 TUN 模式")
print("  2. Clash 规则中没有包含币安域名")
print("  3. 需要开启 Clash 的「允许局域网连接」")
print("  4. 防火墙拦截了 Python 的网络请求")
print()
print("  解决方法:")
print("  1. 打开 Clash → 确保「系统代理」已开启")
print("  2. 打开 Clash → 切换到「全局模式」(Global)")
print("  3. 或者使用 TUN 模式（需要管理员权限）")
print("=" * 60)

input("\n按回车键退出...")
