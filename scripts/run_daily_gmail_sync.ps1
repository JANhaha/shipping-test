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
Write-Host "[1/1] Full refresh pipeline"
if ((Split-Path -Leaf $pythonExe) -ieq "py.exe") {
  & $pythonExe -3 "$projectRoot\scripts\full_refresh.py"
} else {
  & $pythonExe "$projectRoot\scripts\full_refresh.py"
}
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
