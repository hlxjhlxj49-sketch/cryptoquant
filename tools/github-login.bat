@echo off
chcp 65001 >nul 2>&1
title GitHub Login

echo.
echo   ==========================================
echo     GitHub CLI - Login
echo   ==========================================
echo.

REM Add gh to PATH for this session
set "PATH=E:\tools\gh\bin;%PATH%"

echo   Starting GitHub authentication...
echo   A browser window will open automatically.
echo   Follow the instructions to log in.
echo.

E:\tools\gh\bin\gh.exe auth login --hostname github.com --web

echo.
echo   ==========================================
echo   Login complete! You can now close this window.
echo   ==========================================
pause
