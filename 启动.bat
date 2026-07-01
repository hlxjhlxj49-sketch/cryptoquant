@echo off
chcp 65001 >nul 2>&1
title CryptoQuant Trading System

echo.
echo   ==========================================
echo     Crypto Quantitative Trading System
echo     **********************************
echo   ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERROR] Python not found! Please install Python 3.9+
    echo   Download: https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH" during install
    pause
    exit /b 1
)

echo   [OK] Python detected
python --version
echo.

:: Check and activate virtual environment
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" (
    echo   [OK] Virtual environment found, activating...
    call .venv\Scripts\activate.bat
    echo   [OK] Virtual environment activated
) else (
    echo   [WARN] Virtual environment not found!
    echo.
    echo   Please run the install script first:
    echo     tools\install.ps1
    echo.
    echo   Or create it manually:
    echo     python -m venv .venv
    echo     .venv\Scripts\activate
    echo     pip install -r requirements.txt
    echo.
    choice /C YN /M "Continue without virtual environment"
    if errorlevel 2 exit /b 1
)

echo.

:: Install / update dependencies
echo   [INFO] Checking dependencies...
python -m pip install -r "%~dp0requirements.txt" --disable-pip-version-check -q 2>nul
if %errorlevel% neq 0 (
    echo   [WARN] Default mirror failed, trying Tsinghua mirror...
    python -m pip install -r "%~dp0requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple --disable-pip-version-check
    if %errorlevel% neq 0 (
        echo   [ERROR] Failed to install dependencies!
        echo   Please run manually: pip install -r requirements.txt
        pause
        exit /b 1
    )
)
echo   [OK] Dependencies ready
echo.

:: Launch Streamlit
echo   [INFO] Starting CryptoQuant...
echo   [INFO] Open http://localhost:8501 in your browser
echo   [INFO] Press Ctrl+C to stop
echo.

python -m streamlit run ui\app.py --server.headless true

if %errorlevel% neq 0 (
    echo.
    echo   [ERROR] Failed to start. Trying alternative method...
    echo.
    python -c "import streamlit; print('Streamlit version:', streamlit.__version__)"
    python -c "import streamlit.web.cli; streamlit.web.cli.main()" -- run ui\app.py --server.headless true
)

pause
