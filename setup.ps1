# !/usr/bin/env pwsh
# setup.ps1 - One-Click Setup for Snapchat Lab

$ErrorActionPreference = "Stop"
Clear-Host

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   🚀 SNAPCHAT LAB - AUTO-INSTALLER & CONFIGURATOR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Check Python
Write-Host "[*] Checking Python installation..." -NoNewline
try {
    $pythonVer = python --version
    Write-Host " OK ($pythonVer)" -ForegroundColor Green
} catch {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host "Error: Python is not installed or not in PATH. Please install Python 3.10+." -ForegroundColor Yellow
    exit 1
}

# 2. Create Virtual Environment
if (!(Test-Path "venv")) {
    Write-Host "[*] Creating virtual environment (venv)..." -NoNewline
    python -m venv venv
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host "[*] Venv already exists. Skipping..." -ForegroundColor Gray
}

# 3. Install Dependencies
Write-Host "[*] Installing dependencies from requirements.txt..." -NoNewline
.\venv\Scripts\pip install --upgrade pip | Out-Null
.\venv\Scripts\pip install -r requirements.txt | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
    exit 1
}

# 4. Playwright Install (if needed)
Write-Host "[*] Installing Playwright browsers..." -NoNewline
.\venv\Scripts\python -m playwright install | Out-Null
Write-Host " OK" -ForegroundColor Green

# 5. Final Message
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " ✅ INSTALLATION COMPLETE!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " To start the lab, run: " -NoNewline
Write-Host ".\venv\Scripts\python main.py" -ForegroundColor Yellow
Write-Host " Or (if venv is active): " -NoNewline
Write-Host "python main.py" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
