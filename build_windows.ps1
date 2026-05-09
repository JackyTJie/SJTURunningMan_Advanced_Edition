$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$specPath = Join-Path $repoRoot "main.spec"
$iconPath = Join-Path $repoRoot "assets\SJTURM.ico"
$exePath = Join-Path $repoRoot "dist\SJTURunningMan.exe"

if (-not (Test-Path -LiteralPath $specPath)) {
    throw "Missing PyInstaller spec: $specPath"
}

if (-not (Test-Path -LiteralPath $iconPath)) {
    throw "Missing Windows icon: $iconPath"
}

python -m PyInstaller --clean --noconfirm $specPath

if (-not (Test-Path -LiteralPath $exePath)) {
    throw "PyInstaller did not create expected exe: $exePath"
}

Write-Host "Built $exePath"
Write-Host "Embedded icon source: $iconPath"
