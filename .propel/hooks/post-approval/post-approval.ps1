#requires -Version 5.1
param(
  [Parameter(Mandatory)][string]$RunId,
  [Parameter(Mandatory)][string]$StepId,
  [Parameter(Mandatory)][string]$Decision,
  [Parameter(Mandatory)][string]$Actor,
  [Parameter(ValueFromRemainingArguments)][string[]]$Artifacts
)
$ErrorActionPreference = 'Stop'
if (-not $Artifacts) { throw "no artifacts to commit" }
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "gh CLI not found on PATH" }

$AutoMerge = $env:AUTO_MERGE -eq 'true'
$Base   = if ($env:BASE) { $env:BASE } else { 'main' }
$Branch = "propel/$RunId/$StepId"

git checkout -b $Branch 2>$null; if ($LASTEXITCODE -ne 0) { git checkout $Branch }
git add -- @Artifacts
git commit -m "propel($StepId): $Decision by $Actor [run:$RunId]" 2>$null | Out-Null
git push -u origin $Branch

$PrUrl = gh pr create --base $Base --head $Branch `
  --title "Propel $StepId - $RunId" `
  --body "Approved by $Actor. Run: $RunId. Artifacts: $($Artifacts -join ', ')" 2>$null
if (-not $PrUrl) { $PrUrl = gh pr view $Branch --json url -q .url }

$Merged = 'false'
if ($AutoMerge) { gh pr merge $PrUrl --squash --auto --delete-branch; $Merged = 'queued' }

[pscustomobject]@{
  pr_url = $PrUrl; branch = $Branch; sha = (git rev-parse HEAD); merged = $Merged; actor = $Actor
} | ConvertTo-Json -Compress
