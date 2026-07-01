@echo off
chcp 65001 >nul 2>&1
title WSL2 + Docker E盘配置

echo.
echo   ==========================================
echo     WSL2 + Docker E盘 一键配置
echo   ==========================================
echo.

:: 1. Enable Windows Features
echo   [1/4] Enabling Windows Features...
dism /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart >nul 2>&1
dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart >nul 2>&1
echo   [OK] WSL + VM Platform enabled

:: 2. Install WSL2
echo   [2/4] Installing WSL2...
wsl --update >nul 2>&1
wsl --set-default-version 2 >nul 2>&1
echo   [OK] WSL2 ready

:: 3. Create E: directories
echo   [3/4] Creating E: directories...
mkdir E:\wsl 2>nul
mkdir E:\docker\data 2>nul

:: Configure WSL2 settings
echo [wsl2] > "%USERPROFILE%\.wslconfig"
echo kernelCommandLine = vsyscall=emulate >> "%USERPROFILE%\.wslconfig"
echo memory = 4GB >> "%USERPROFILE%\.wslconfig"
echo processors = 2 >> "%USERPROFILE%\.wslconfig"
echo swap = 2GB >> "%USERPROFILE%\.wslconfig"
echo swapFile = E:\\wsl\\swap.vhdx >> "%USERPROFILE%\.wslconfig"
echo   [OK] WSL config -> E:\wsl

:: 4. Configure Docker
echo   [4/4] Configuring Docker data-root...
echo { > "%USERPROFILE%\.docker\daemon.json"
echo   "data-root": "E:\\docker\\data", >> "%USERPROFILE%\.docker\daemon.json"
echo   "builder": { >> "%USERPROFILE%\.docker\daemon.json"
echo     "gc": { >> "%USERPROFILE%\.docker\daemon.json"
echo       "defaultKeepStorage": "20GB", >> "%USERPROFILE%\.docker\daemon.json"
echo       "enabled": true >> "%USERPROFILE%\.docker\daemon.json"
echo     } >> "%USERPROFILE%\.docker\daemon.json"
echo   }, >> "%USERPROFILE%\.docker\daemon.json"
echo   "experimental": false >> "%USERPROFILE%\.docker\daemon.json"
echo } >> "%USERPROFILE%\.docker\daemon.json"
echo   [OK] Docker data-root -> E:\docker\data

echo.
echo   ==========================================
echo     Setup complete! RESTART your computer.
echo   ==========================================
echo.
echo   After reboot:
echo     1. Launch Docker Desktop
echo     2. Open E:\crypto_quant
echo     3. Run: docker-start.bat
echo.
pause
