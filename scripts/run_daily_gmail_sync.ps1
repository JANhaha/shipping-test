$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

py "$projectRoot\scripts\sync_gmail_shipping_data.py"

if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
