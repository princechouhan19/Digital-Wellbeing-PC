# Digital Wellbeing full build pipeline — run from anywhere; it always operates on the repo root.
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

# Ensure running instances don't lock binaries during rebuild
Get-Process -Name "DigitalWellbeing", "Uninstall Digital Wellbeing" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

$venvScripts = Join-Path $repoRoot "venv\Scripts"
if (Test-Path $venvScripts) {
    $env:PATH = "$venvScripts;$env:PATH"
}

Write-Host "== 1/4  Building Digital Wellbeing app ==" -ForegroundColor Cyan
pyinstaller digital_wellbeing.spec --noconfirm
if (Test-Path "assets") {
    Copy-Item "assets" "dist\DigitalWellbeing\assets" -Recurse -Force
}

Write-Host "== 2/4  Building uninstaller ==" -ForegroundColor Cyan
pyinstaller installer\uninstaller.spec --noconfirm

Write-Host "== 3/4  Staging payload ==" -ForegroundColor Cyan
$payload = "build\installer_payload"
if (Test-Path $payload) { Remove-Item -Recurse -Force $payload }
New-Item -ItemType Directory -Force $payload | Out-Null
Copy-Item dist\DigitalWellbeing\* $payload -Recurse -Force
Copy-Item "dist\Uninstall Digital Wellbeing.exe" $payload -Force

Write-Host "== 4/4  Building installer ==" -ForegroundColor Cyan
$env:DW_PAYLOAD = (Resolve-Path $payload).Path
pyinstaller installer\installer.spec --noconfirm

Write-Host ""
Write-Host "Done. Output: dist\Digital Wellbeing Setup.exe" -ForegroundColor Green
