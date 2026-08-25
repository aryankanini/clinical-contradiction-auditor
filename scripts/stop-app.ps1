$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
$patterns = @(
    'uvicorn module_4_api_ui.backend.main:app',
    'npm run dev',
    'vite',
    [regex]::Escape($repoRoot)
)

function Get-ListeningPidsOnPort {
    param([int]$Port)

    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        $connections = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
        foreach ($connection in $connections) {
            if ($null -ne $connection.OwningProcess) {
                [int]$connection.OwningProcess
            }
        }
        return
    }

    $pattern = ":$Port"
    $lines = netstat -ano | Select-String -Pattern $pattern
    foreach ($line in $lines) {
        $parts = ($line -replace '^\s+', '') -split '\s+'
        if ($parts.Length -ge 5 -and $parts[3] -eq 'LISTENING') {
            $listenerPid = 0
            if ([int]::TryParse($parts[4], [ref]$listenerPid)) {
                $listenerPid
            }
        }
    }
}

$matches = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine -match 'powershell|python|node' -and
    (
        $_.CommandLine -match $patterns[0] -or
        $_.CommandLine -match $patterns[1] -or
        $_.CommandLine -match $patterns[2] -or
        $_.CommandLine -match $patterns[3]
    )
}

if (-not $matches) {
    Write-Host 'No running app processes were found.'
    return
}

foreach ($process in $matches) {
    Write-Host "Stopping PID $($process.ProcessId) - $($process.CommandLine)"
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

$portPids = @()
foreach ($port in @(8000, 8001, 18080, 5173)) {
    $portPids += Get-ListeningPidsOnPort -Port $port
}

foreach ($listenerPid in ($portPids | Sort-Object -Unique)) {
    if ($listenerPid -le 0) {
        continue
    }

    try {
        $process = Get-Process -Id $listenerPid -ErrorAction Stop
        Write-Host "Stopping port listener PID $listenerPid - $($process.ProcessName)"
        Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue
    }
    catch {
        # Process exited between netstat and kill.
    }
}

Write-Host 'Stopped the app processes.'
