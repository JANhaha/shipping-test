$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

function Resolve-Python {
  $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
  if (Test-Path $venvPython) {
    return $venvPython
  }

  $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if ($pythonCommand) {
    return $pythonCommand.Source
  }

  $pyCommand = Get-Command py -ErrorAction SilentlyContinue
  if ($pyCommand) {
    return $pyCommand.Source
  }

  throw "Python executable not found. Create .venv or install Python on PATH."
}

$pythonExe = Resolve-Python

function Invoke-ProjectPython {
  param([Parameter(Mandatory = $true)][string]$ScriptPath)

  if ((Split-Path -Leaf $pythonExe) -ieq "py.exe") {
    & $pythonExe -3 $ScriptPath
  } else {
    & $pythonExe $ScriptPath
  }
}

Write-Host "[1/3] Full refresh pipeline"
Invoke-ProjectPython "$projectRoot\scripts\full_refresh.py"
if ($LASTEXITCODE -ne 0) {
  Write-Warning "Full refresh failed. Archiving the latest available local static data instead."
}

Write-Host "[2/3] Sync latest public JSON snapshots from GitHub"
$ghExe = "C:\Program Files\GitHub CLI\gh.exe"
$dataDir = Join-Path $projectRoot "docs\data"
if (Test-Path $ghExe) {
  New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
  foreach ($name in @("dashboard.json", "shipping_data.json", "map_data.json")) {
    $apiPath = "repos/JANhaha/shipping-test/contents/docs/data/$name" + "?ref=stable"
    try {
      $encoded = & $ghExe api $apiPath --jq .content
      $clean = ($encoded -join "").Replace("`n", "")
      $bytes = [Convert]::FromBase64String($clean)
      [IO.File]::WriteAllBytes((Join-Path $dataDir $name), $bytes)
      Write-Host "synced $name"
    } catch {
      Write-Warning "Unable to sync $name from GitHub. Local copy will be used. $_"
    }
  }
} else {
  Write-Warning "GitHub CLI not found. Local static data will be used."
}

Write-Host "[3/3] Archive Beijing daily snapshot"
Invoke-ProjectPython "$projectRoot\scripts\archive_daily_snapshot.py"
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
