# acquire-knowledge-hook.ps1
# Propel-IQ Knowledge Map — Post-write hook (PowerShell wrapper)
# Use for: Windsurf and Copilot on Windows

$ErrorActionPreference = "SilentlyContinue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonHook = Join-Path $ScriptDir "acquire-knowledge-hook.py"

if (-not (Test-Path $PythonHook)) {
    Write-Error "[acquire-knowledge-hook] Python hook not found at $PythonHook"
    exit 0
}

$input | python3 $PythonHook
exit 0
