# PowerShell build script to create Windows .exe using PyInstaller
# Requirements: Python 3.9+ installed and available in PATH

param(
    [string]$Python = "python"
)

Write-Host "Installing dependencies..." -ForegroundColor Cyan
& $Python -m pip install -r requirements.txt --quiet

# Ensure PyInstaller installed
& $Python -m pip install pyinstaller --quiet

Write-Host "Building executable..." -ForegroundColor Cyan
# --windowed hides the console window; --onefile creates a single exe
& $Python -m PyInstaller --noconfirm --onefile --windowed --name ImageWatermarkTool src/main.py

$distPath = Join-Path -Path (Get-Location) -ChildPath "dist\ImageWatermarkTool.exe"
if (Test-Path $distPath) {
    Write-Host "Build succeeded: $distPath" -ForegroundColor Green
} else {
    Write-Host "Build may have failed. Check the logs above." -ForegroundColor Red
}