$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = 'utf-8'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousDirectory = Get-Location
try {
    Set-Location -LiteralPath (Join-Path $projectRoot 'backend')
    & (Join-Path $projectRoot '.venv\Scripts\python.exe') -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { throw '后端检查未通过。' }
    Set-Location -LiteralPath (Join-Path $projectRoot 'frontend')
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw '前端检查未通过。' }
    Write-Host '后端测试、前端类型检查与构建全部通过。' -ForegroundColor Green
} finally { Set-Location -LiteralPath $previousDirectory }
