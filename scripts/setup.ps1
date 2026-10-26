param()
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = 'utf-8'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousDirectory = Get-Location
try {
    Set-Location -LiteralPath $projectRoot
    Write-Host '正在准备青禾运营助手的本地环境…' -ForegroundColor Green
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw '请先安装 Node.js 22.12+ 或 24 LTS。' }
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw '请先安装 Python 3.11+，并将 Python 加入 PATH。' }
    $projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $projectPython)) {
        if (Get-Command uv -ErrorAction SilentlyContinue) { & uv venv --python python .venv }
        else { & python -m venv .venv }
        if ($LASTEXITCODE -ne 0) { throw '虚拟环境创建失败。' }
    }
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv --cache-dir (Join-Path $projectRoot '.cache\uv') pip install --python $projectPython -r backend/requirements.lock.txt
    } else {
        & $projectPython -m ensurepip --upgrade
        if ($LASTEXITCODE -ne 0) { throw 'pip 初始化失败。' }
        & $projectPython -m pip install -r backend/requirements.lock.txt
    }
    if ($LASTEXITCODE -ne 0) { throw '后端依赖安装失败，请检查网络后重新执行。' }
    Set-Location -LiteralPath (Join-Path $projectRoot 'frontend')
    & npm.cmd ci --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败，请检查网络后重新执行。' }
    Write-Host '环境准备完成。执行 scripts\start.ps1 -Demo 启动演示。' -ForegroundColor Green
} finally { Set-Location -LiteralPath $previousDirectory }
