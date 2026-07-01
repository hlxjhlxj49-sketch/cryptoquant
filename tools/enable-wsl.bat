@echo off
echo Enabling WSL2 features...
dism /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
echo.
dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
echo.
echo Done! Restart your computer now.
pause
