# CryptoQuant 一键安装脚本
# 用法：在项目根目录右键 → "使用 PowerShell 运行"，或：
#   powershell -ExecutionPolicy Bypass -File tools/install.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "    CryptoQuant - Environment Setup" -ForegroundColor Cyan
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""

# ---- 1. Check Python ----
Write-Host "  [1/4] Checking Python..." -ForegroundColor Yellow
try {
    $pyVer = python --version 2>&1
    Write-Host "  [OK] $pyVer" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Python not found! Please install Python 3.9+" -ForegroundColor Red
    Write-Host "  Download: https://www.python.org/downloads/" -ForegroundColor Red
    pause
    exit 1
}

# ---- 2. Create/update virtual environment ----
Write-Host "  [2/4] Setting up virtual environment..." -ForegroundColor Yellow
$venvPath = Join-Path $ProjectRoot ".venv"

if (-not (Test-Path $venvPath)) {
    Write-Host "  Creating .venv..." -ForegroundColor Gray
    python -m venv $venvPath
    Write-Host "  [OK] Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "  [OK] Virtual environment already exists" -ForegroundColor Green
}

# Activate
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    . $activateScript
    Write-Host "  [OK] Virtual environment activated" -ForegroundColor Green
}

# ---- 3. Install dependencies ----
Write-Host "  [3/4] Installing dependencies..." -ForegroundColor Yellow
$reqFile = Join-Path $ProjectRoot "requirements.txt"

# Try default mirror first
try {
    python -m pip install -r $reqFile --disable-pip-version-check -q
    Write-Host "  [OK] Dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Default mirror failed, trying Tsinghua..." -ForegroundColor Yellow
    python -m pip install -r $reqFile `
        -i https://pypi.tuna.tsinghua.edu.cn/simple `
        --disable-pip-version-check
    Write-Host "  [OK] Dependencies installed (Tsinghua mirror)" -ForegroundColor Green
}

# ---- 4. Done ----
Write-Host "  [4/4] Done!" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "    Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "    Start the system:" -ForegroundColor White
Write-Host "      .\启动.bat" -ForegroundColor White
Write-Host ""
Write-Host "    Or activate manually:" -ForegroundColor White
Write-Host "      .venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "      streamlit run ui/app.py" -ForegroundColor White
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""

$choice = Read-Host "  Launch CryptoQuant now? (Y/n)"
if ($choice -eq "" -or $choice -eq "Y" -or $choice -eq "y") {
    $startBat = Join-Path $ProjectRoot "启动.bat"
    if (Test-Path $startBat) {
        Start-Process -FilePath $startBat
    } else {
        python -m streamlit run ui/app.py --server.headless true
    }
}
