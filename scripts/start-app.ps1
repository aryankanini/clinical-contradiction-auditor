param(
    [switch]$SkipSeed,
    [switch]$DisableAI,
    [int]$BackendPort = 18080
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$frontendDir = Join-Path $repoRoot 'module_4_api_ui\frontend'

function Assert-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

function Assert-PortAvailable {
    param([int]$Port)

    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Where-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue } |
        Select-Object -First 1

    if ($listener) {
        throw "Port $Port is already in use by PID $($listener.OwningProcess). Stop the existing service or choose a different -BackendPort."
    }
}

function Wait-ForBackend {
    param([int]$Port)

    $healthUri = "http://127.0.0.1:$Port/api/v1/health"
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $healthUri -UseBasicParsing -TimeoutSec 1
            if ($response.StatusCode -eq 200) {
                return
            }
        }
        catch {
            # Uvicorn has not completed startup yet.
        }

        Start-Sleep -Seconds 1
    }

    throw "Backend did not become healthy at $healthUri."
}

Assert-Command python
Assert-Command npm
Assert-PortAvailable -Port $BackendPort

if (-not (Test-Path $venvPython)) {
    Write-Host 'Creating Python virtual environment...'
    & python -m venv (Join-Path $repoRoot '.venv')
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to create the Python virtual environment.'
    }
}

if (-not $SkipSeed) {
    Write-Host 'Seeding the local demo database...'
    & $venvPython -m module_4_api_ui.backend.seed --database-url 'sqlite+pysqlite:///./dev.db' --reset
    if ($LASTEXITCODE -ne 0) {
        throw 'Database seeding failed.'
    }
}

$aiEnabled = if ($DisableAI) { 'false' } else { 'true' }

$backendCommand = @"
Set-Location '$repoRoot'
`$env:DATABASE_URL = 'sqlite+pysqlite:///./dev.db'
`$env:AI_ENABLED = '$aiEnabled'
& '$venvPython' -m uvicorn module_4_api_ui.backend.main:app --reload --host 127.0.0.1 --port $BackendPort
"@

Write-Host 'Starting backend...'
Start-Process powershell -ArgumentList '-NoExit', '-Command', $backendCommand -WorkingDirectory $repoRoot | Out-Null
Wait-ForBackend -Port $BackendPort

if (-not (Test-Path (Join-Path $frontendDir 'node_modules'))) {
    Write-Host 'Installing frontend dependencies...'
    Push-Location $frontendDir
    try {
        & npm install
        if ($LASTEXITCODE -ne 0) {
            throw 'npm install failed.'
        }
    }
    finally {
        Pop-Location
    }
}

$frontendCommand = @"
Set-Location '$frontendDir'
`$env:VITE_API_PROXY_TARGET = 'http://127.0.0.1:$BackendPort'
npm run dev
"@

Write-Host 'Starting frontend...'
Start-Process powershell -ArgumentList '-NoExit', '-Command', $frontendCommand -WorkingDirectory $frontendDir | Out-Null

Write-Host ''
Write-Host 'The app is starting.'
Write-Host "Backend: http://127.0.0.1:$BackendPort"
Write-Host 'Frontend: http://localhost:5173'
Write-Host "AI explanations enabled: $aiEnabled"
Write-Host 'Use scripts\stop-app.ps1 to stop both services.'
