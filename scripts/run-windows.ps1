$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$DataRoot = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE "AppData\Local" }
$RuntimeDir = Join-Path $DataRoot "CaseLight\runtime"
$Python = Join-Path $RuntimeDir "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    py -3 -m venv $RuntimeDir
    & $Python -m pip install --upgrade pip
}
& $Python -m pip install --quiet -e $ProjectDir
& $Python -m caselight @args
