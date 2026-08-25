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
            if (
                $null -ne $connection.OwningProcess -and
                (Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue)
            ) {
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
    $_.ProcessId -ne $PID -and
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
    Write-Host 'No matching app parent processes were found; checking listeners.'
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
    if ($listenerPid -le 0 -or $listenerPid -eq $PID) {
        continue
    }

    try {
        $process = Get-Process -Id $listenerPid -ErrorAction Stop
        $listenerProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $listenerPid" -ErrorAction SilentlyContinue
        $cmdLine = if ($listenerProcess) { $listenerProcess.CommandLine } else { $null }
        if (
            -not $cmdLine -or
            (
                -not ($cmdLine -match $patterns[0]) -and
                -not ($cmdLine -match $patterns[1]) -and
                -not ($cmdLine -match $patterns[2]) -and
                -not ($cmdLine -match $patterns[3])
            )
        ) {
            continue
        }
        Write-Host "Stopping port listener PID $listenerPid - $($process.ProcessName)"
        Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue
    }
    catch {
        # Process exited between netstat and kill.
    }
}

for ($attempt = 1; $attempt -le 40; $attempt++) {
    $remainingListenerPids = @()
    foreach ($port in @(8000, 8001, 18080, 5173)) {
        $remainingListenerPids += Get-ListeningPidsOnPort -Port $port
    }

    $remainingListenerPids = $remainingListenerPids | Sort-Object -Unique
    if (-not $remainingListenerPids) {
        break
    }

    foreach ($listenerPid in $remainingListenerPids) {
        if ($listenerPid -gt 0 -and $listenerPid -ne $PID) {
            Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue
        }
    }

    Start-Sleep -Milliseconds 250
}

$stillListening = @()
foreach ($port in @(8000, 8001, 18080, 5173)) {
    $stillListening += Get-ListeningPidsOnPort -Port $port
}

if ($stillListening) {
    $remainingPids = ($stillListening | Sort-Object -Unique) -join ', '
    throw "Unable to stop listeners on application ports: $remainingPids."
}

Write-Host 'Stopped the app processes.'
