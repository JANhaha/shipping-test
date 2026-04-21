$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$pythonExe = "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe"

if (-not (Test-Path $pythonExe)) {
  throw "Python executable not found: $pythonExe"
}

Write-Host "[1/2] Full refresh pipeline"
& $pythonExe "$projectRoot\scripts\full_refresh.py"
if ($LASTEXITCODE -ne 0) {
  Write-Warning "Full refresh failed. Archiving the latest available local static data instead."
}

Write-Host "[2/3] Sync latest public JSON snapshots from GitHub"
$ghExe = "C:\Program Files\GitHub CLI\gh.exe"
$dataDir = Join-Path $projectRoot "docs\data"
if (Test-Path $ghExe) {
  New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
  foreach ($name in @("dashboard.json", "shipping_data.json", "map_data.json")) {
    $apiPath = "repos/JANhaha/shipping-test/contents/docs/data/$name" + "?ref=main"
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
& $pythonExe "$projectRoot\scripts\archive_daily_snapshot.py"
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
