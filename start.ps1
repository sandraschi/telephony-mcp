Param([switch]$Headless, [switch]$WebappOnly, [switch]$McpOnly)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$BackendPort  = 10952
$FleetStartPath = Join-Path $ProjectRoot "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath

$FrontendPort = 10953

# Clear ports
foreach ($port in @($BackendPort, $FrontendPort)) {
    $procs = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($procs) {
        $procs | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        Write-Host "Cleared port $port" -ForegroundColor DarkGray
    }
}

# Ensure data + audio dirs
New-Item -ItemType Directory -Force -Path "$PSScriptRoot\data"        | Out-Null
New-Item -ItemType Directory -Force -Path "$PSScriptRoot\audio\tts"   | Out-Null
New-Item -ItemType Directory -Force -Path "$PSScriptRoot\audio\fallback" | Out-Null

if (-not $WebappOnly) {
    Write-Host "Starting MCP server (stdio)..." -ForegroundColor Cyan
    # MCP server runs stdio - started by Claude Desktop, not here.
    # This script manages the webapp pair only.
    Write-Host "  MCP server is managed by Claude Desktop (stdio transport)" -ForegroundColor DarkGray
}

if (-not $McpOnly) {
    # Install frontend deps if needed
    $nodeModules = "$PSScriptRoot\webapp\frontend\node_modules"
    if (-not (Test-Path $nodeModules)) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
        Push-Location "$PSScriptRoot\webapp\frontend"
        & "C:\Program Files\nodejs\npm.cmd" install
        Pop-Location
    }

    # Start backend
    Write-Host "Starting webapp backend on :$BackendPort..." -ForegroundColor Cyan
    $backendJob = Start-Process pwsh -ArgumentList @(
        '-NoProfile', '-Command',
        "Set-Location '$PSScriptRoot'; uv run python webapp/backend/main.py"
    ) -PassThru -WindowStyle Normal

    # Wait for backend
    $deadline = (Get-Date).AddSeconds(15)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:$BackendPort/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    if ($ready) {
        Write-Host "Backend ready." -ForegroundColor Green
    } else {
        Write-Host "Backend did not respond in time - check logs." -ForegroundColor Yellow
    }

    # Start frontend
    Write-Host "Starting webapp frontend on :$FrontendPort..." -ForegroundColor Cyan
    Push-Location "$PSScriptRoot\webapp\frontend"
    $frontendJob = Start-Process pwsh -ArgumentList @(
        '-NoProfile', '-Command',
        "Set-Location '$PSScriptRoot\webapp\frontend'; & 'C:\Program Files\nodejs\npm.cmd' run dev"
    ) -PassThru -WindowStyle Normal
    Pop-Location

    Start-Sleep -Seconds 3
    Write-Host ""
    Write-Host "Telephony MCP Audit Dashboard" -ForegroundColor Green
    Write-Host "  Frontend : http://localhost:$FrontendPort" -ForegroundColor White
    Write-Host "  Backend  : http://localhost:$BackendPort/api/health" -ForegroundColor White
    Write-Host ""
    Start-Process "http://localhost:$FrontendPort"
}
