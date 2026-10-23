$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$manifestPath = Join-Path $repoRoot "desktop\src-tauri\Cargo.toml"
$frontendPath = Join-Path $repoRoot "desktop"
$exePath = Join-Path $repoRoot "dist\SJTURunningMan.exe"

if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Missing Tauri desktop manifest: $manifestPath"
}

# Tauri 在编译期把前端资源嵌进 exe，因此必须先产出 desktop\dist。
if (-not (Test-Path -LiteralPath (Join-Path $frontendPath "node_modules"))) {
    pnpm --dir $frontendPath install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw "Frontend dependency install failed" }
}
pnpm --dir $frontendPath build
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
if (-not (Test-Path -LiteralPath (Join-Path $frontendPath "dist\index.html"))) {
    throw "Frontend build did not create desktop\dist\index.html"
}

cargo build --release --locked --features custom-protocol --manifest-path $manifestPath
if ($LASTEXITCODE -ne 0) { throw "Rust build failed" }
New-Item -ItemType Directory -Path (Join-Path $repoRoot "dist") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $repoRoot "target\release\sjturunningman.exe") -Destination $exePath

if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Rust build did not create expected exe: $exePath"
}

Write-Host "Built $exePath"
Write-Host ("Size: {0:N2} MiB" -f ((Get-Item -LiteralPath $exePath).Length / 1MB))
