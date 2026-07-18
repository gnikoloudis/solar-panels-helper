$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$frontend = Join-Path $root "frontend"
$port = 8002

Write-Host "=== Solarpanels Launcher ===" -ForegroundColor Cyan

# --- Kill anything on our port ---
$proc = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
if ($proc) {
    Write-Host "Killing process on port $port (PID $proc)..." -ForegroundColor Yellow
    Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# --- Kill stale Vite / Node ---
$nodeProcs = Get-Process -Name "node" -ErrorAction SilentlyContinue
if ($nodeProcs) {
    Write-Host "Killing all Node processes ($($nodeProcs.Count) found)..." -ForegroundColor Yellow
    $nodeProcs | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# --- Clear all caches ---
Write-Host "Clearing caches..." -ForegroundColor Yellow

# Stale compiled .js files that shadow .tsx sources
Get-ChildItem -Path "$frontend\src" -Recurse -Filter "*.js" -Exclude "*.map" | Remove-Item -Force -ErrorAction SilentlyContinue

# Vite dev server cache
$viteCache = Join-Path $frontend "node_modules\.vite"
if (Test-Path $viteCache) { Remove-Item -Recurse -Force $viteCache -ErrorAction SilentlyContinue }

# TypeScript incremental build info
$tsCache = Join-Path $frontend "tsconfig.tsbuildinfo"
if (Test-Path $tsCache) { Remove-Item -Force $tsCache -ErrorAction SilentlyContinue }

# Production build output
$dist = Join-Path $frontend "dist"
if (Test-Path $dist) { Remove-Item -Recurse -Force $dist -ErrorAction SilentlyContinue }

# Python bytecode cache
Get-ChildItem -Path "$root\src" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path "$root\tests" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "All caches cleared" -ForegroundColor Yellow

$env:PYTHONPATH = "src"

Write-Host "Starting backend on http://127.0.0.1:$port ..." -ForegroundColor Cyan
$backend = Start-Process -NoNewWindow -PassThru -FilePath $python `
  -ArgumentList "-m", "uvicorn", "solarpanels.main:app", "--host", "127.0.0.1", "--port", $port

Start-Sleep -Seconds 2

Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Cyan
$front = Start-Process -PassThru -FilePath "cmd.exe" -ArgumentList "/k", "npm.cmd run dev" -WorkingDirectory $frontend

Write-Host ""
Write-Host "  Backend:  http://127.0.0.1:$port" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to stop both services."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

$backend.Kill()
$front.Kill()
