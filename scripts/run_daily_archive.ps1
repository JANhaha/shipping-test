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

Write-Host "[2/2] Archive Beijing daily snapshot"
& $pythonExe "$projectRoot\scripts\archive_daily_snapshot.py"
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
