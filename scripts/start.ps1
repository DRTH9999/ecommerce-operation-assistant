param(
    [ValidateRange(1024,65535)][int]$Port = 8765,
    [switch]$Demo,
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = 'utf-8'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousDirectory = Get-Location
try {
    Set-Location -LiteralPath $projectRoot
    $projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $projectPython) -or -not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\node_modules'))) {
        & (Join-Path $PSScriptRoot 'setup.ps1')
    }
    if (-not $SkipBuild -or -not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\dist\index.html'))) {
        Set-Location -LiteralPath (Join-Path $projectRoot 'frontend')
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw '前端构建失败，请先修复上方错误。' }
    }
    $portCheck = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try { $portCheck.Start() }
    catch { throw "端口 $Port 不可用（可能被占用或被 Windows 保留）。请改用 -Port 指定可用端口。" }
    finally { $portCheck.Stop() }
    Set-Location -LiteralPath (Join-Path $projectRoot 'backend')
    & $projectPython scripts/init_db.py
    if ($LASTEXITCODE -ne 0) { throw '数据库初始化失败。' }
    if ($Demo) {
        & $projectPython scripts/init_db.py --demo
        if ($LASTEXITCODE -ne 0) { throw '演示数据初始化失败。' }
    }
    Write-Host "工作台：http://127.0.0.1:$Port" -ForegroundColor Green
    Write-Host "接口文档：http://127.0.0.1:$Port/docs"
    Write-Host '保持此窗口开启，按 Ctrl+C 停止服务。'
    & $projectPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw '服务启动失败，请检查上方错误。' }
} finally { Set-Location -LiteralPath $previousDirectory }
