$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$BuildEnv = Join-Path $env:TEMP "caselight-build"
$Python = Join-Path $BuildEnv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    py -3 -m venv $BuildEnv
}
& $Python -m pip install --upgrade pip
& $Python -m pip install "$ProjectDir[build]"
Push-Location $ProjectDir
try {
    & (Join-Path $BuildEnv "Scripts\pyinstaller.exe") --noconfirm --clean CaseLight.spec
} finally {
    Pop-Location
}
Write-Host "Built $ProjectDir\dist\CaseLight.exe"
