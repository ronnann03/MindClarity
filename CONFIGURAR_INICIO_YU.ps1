$ErrorActionPreference = 'Stop'
$yuPython = (Get-Command python -ErrorAction Stop).Source
$yuLauncher = Join-Path $PSScriptRoot 'START_YU_LOCAL.ps1'
$yuPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$yuArguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $yuLauncher + '" -PythonExe "' + $yuPython + '" -Supervise'
$yuCommand = '"' + $yuPowerShell + '" ' + $yuArguments
$yuDesktop = [Environment]::GetFolderPath('Desktop')
$yuDesktopScript = Join-Path $yuDesktop 'start_yu.bat'
if (Test-Path -LiteralPath $yuDesktopScript) {
    $yuExisting = [System.IO.File]::ReadAllText($yuDesktopScript)
    if ($yuExisting -notmatch [regex]::Escape($yuLauncher)) {
        Copy-Item -LiteralPath $yuDesktopScript -Destination ($yuDesktopScript + '.' + (Get-Date -Format 'yyyyMMddHHmmss') + '.backup')
    }
}
$yuBatch = "@echo off`r`nstart `"`" $yuCommand`r`n"
[System.IO.File]::WriteAllText($yuDesktopScript, $yuBatch, [System.Text.Encoding]::Default)
$yuRunKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
if (-not (Test-Path -LiteralPath $yuRunKey)) { New-Item -Path $yuRunKey | Out-Null }
New-ItemProperty -LiteralPath $yuRunKey -Name 'YU_Assistant' -Value $yuCommand -PropertyType String -Force | Out-Null
Write-Output "Inicio de sesión configurado: YU_Assistant"
Write-Output "Acceso en Escritorio: $yuDesktopScript"
