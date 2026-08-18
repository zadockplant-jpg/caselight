$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$Executable = Join-Path $ProjectDir "dist\CaseLight.exe"
$Icon = Join-Path $ProjectDir "assets\caselight.ico"

if (-not (Test-Path $Executable)) {
    $DownloadedExecutable = Join-Path $ProjectDir "dist\windows-ci\CaseLight.exe"
    if (Test-Path $DownloadedExecutable) {
        $Executable = $DownloadedExecutable
    } else {
        throw "CaseLight executable is missing. Run .\scripts\build-windows.ps1 first."
    }
}

$Shell = New-Object -ComObject WScript.Shell
$Destinations = @(
    [Environment]::GetFolderPath("Desktop"),
    (Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs")
)

foreach ($Destination in $Destinations) {
    $ShortcutPath = Join-Path $Destination "CaseLight.lnk"
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $Executable
    $Shortcut.WorkingDirectory = $ProjectDir
    $Shortcut.IconLocation = "$Icon,0"
    $Shortcut.Description = "Case lighting, tempo effects, and music visualization"
    $Shortcut.Save()
    Write-Host "Installed shortcut: $ShortcutPath"
}
