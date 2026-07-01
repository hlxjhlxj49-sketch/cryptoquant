# CryptoQuant - WSL2 + Docker 一键配置（E盘）
# 以管理员身份运行此脚本
# 右键 → 使用 PowerShell 运行

$ErrorActionPreference = "Stop"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  WSL2 + Docker E盘配置" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# ---- 1. Enable WSL2 ----
Write-Host "[1/5] Enabling WSL2..." -ForegroundColor Yellow
wsl --install --no-launch 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Trying alternative: enable Windows features..."
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
}
Write-Host "  [OK] WSL2 features enabled" -ForegroundColor Green
Write-Host "  [INFO] A system restart may be required" -ForegroundColor Yellow
Write-Host ""

# ---- 2. Set WSL default version ----
Write-Host "[2/5] Setting WSL2 as default..." -ForegroundColor Yellow
wsl --set-default-version 2
Write-Host "  [OK] WSL2 is default" -ForegroundColor Green
Write-Host ""

# ---- 3. Create WSL distro directory on E: ----
$WslRoot = "E:\wsl"
$DistroName = "docker-desktop"
New-Item -ItemType Directory -Force -Path $WslRoot | Out-Null
Write-Host "[3/5] WSL data root: $WslRoot" -ForegroundColor Green
Write-Host ""

# ---- 4. Configure WSL config to use E: drive ----
Write-Host "[4/5] Configuring WSL..." -ForegroundColor Yellow
$WslConfig = @"
[wsl2]
kernelCommandLine = vsyscall=emulate
memory = 4GB
processors = 2
swap = 2GB
swapFile = E:\\wsl\\swap.vhdx
"@
$WslConfig | Out-File -FilePath "$env:USERPROFILE\.wslconfig" -Encoding UTF8 -Force
Write-Host "  [OK] .wslconfig written (E:\\wsl\\swap.vhdx)" -ForegroundColor Green
Write-Host ""

# ---- 5. Restart Docker Desktop ----
Write-Host "[5/5] Docker post-install..." -ForegroundColor Yellow
$DockerDaemon = @"
{
  "data-root": "E:\\docker\\data",
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false
}
"@
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.docker" | Out-Null
$DockerDaemon | Out-File -FilePath "$env:USERPROFILE\.docker\daemon.json" -Encoding UTF8 -Force
New-Item -ItemType Directory -Force -Path "E:\docker\data" | Out-Null
Write-Host "  [OK] Docker data-root = E:\\docker\\data" -ForegroundColor Green
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "  1. RESTART your computer (WSL2 activation)" -ForegroundColor White
Write-Host "  2. After reboot, launch Docker Desktop" -ForegroundColor White
Write-Host "  3. Wait for Docker engine to be ready" -ForegroundColor White
Write-Host "  4. Run: cd E:\crypto_quant && docker compose up -d" -ForegroundColor White
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to exit"
