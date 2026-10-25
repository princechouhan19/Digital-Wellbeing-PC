param([Parameter(Mandatory = $true)][string]$Path)

# Optional code signing. The build is intentionally usable without a
# certificate (local dev / forks); release CI provides cert.pfx and
# SIGN_PASSWORD as secrets.
$repoRoot = Split-Path $PSScriptRoot -Parent
$cert = Join-Path $repoRoot "cert.pfx"
if (-not (Test-Path $cert)) {
    Write-Host "Skipping signing (cert.pfx not found): $Path"
    return
}

$signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending |
    Select-Object -First 1
if (-not $signtool) {
    Write-Warning "signtool.exe not found; skipping $Path"
    return
}

& $signtool.FullName sign /f $cert /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /p "$env:SIGN_PASSWORD" "$Path"
if ($LASTEXITCODE -ne 0) {
    throw "Code signing failed for $Path"
}
Write-Host "Signed $Path"
