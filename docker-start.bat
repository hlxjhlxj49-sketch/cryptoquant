@echo off
chcp 65001 >nul 2>&1
title CryptoQuant Docker

echo.
echo   ==========================================
echo     CryptoQuant - Docker Mode
echo   ==========================================
echo.

:: Check Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERROR] Docker not found!
    echo   Please install Docker Desktop first.
    echo   https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo   [OK] Docker detected
docker --version
echo.

:: Build and start
echo   [INFO] Building and starting containers...
docker compose up -d --build

if %errorlevel% neq 0 (
    echo   [ERROR] Failed to start Docker containers
    pause
    exit /b 1
)

echo   [OK] Container started
echo.
echo   [INFO] Opening http://localhost:8501 ...
start http://localhost:8501

echo.
echo   Useful commands:
echo     docker compose logs -f    # View logs
echo     docker compose down       # Stop and remove
echo     docker compose restart    # Restart
echo.

pause
