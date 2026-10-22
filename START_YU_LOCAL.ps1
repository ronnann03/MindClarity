param(
    [string]$PythonExe = 'python',
    [switch]$Supervise
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:AI_PROVIDER = 'ollama'
$env:OLLAMA_NO_CLOUD = '1'

function Start-YuLocal {
    $yuPort = if ($env:YU_PORT) { $env:YU_PORT } else { '8000' }
    try {
        $yuStatus = Invoke-RestMethod "http://127.0.0.1:$yuPort/api/status" -TimeoutSec 5
        if ($yuStatus.assistant_name -and $yuStatus.ai_provider) {
            Write-Output "YU ya está disponible en http://localhost:$yuPort"
            return
        }
    } catch { }

    $yuConfigJson = & $PythonExe -c "import json; from config.settings import settings; print(json.dumps({'url': settings.ollama_base_url, 'model': settings.ollama_model}))"
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo leer la configuración de YU con Python.' }
    $yuConfig = $yuConfigJson | ConvertFrom-Json
    $yuTagsUrl = $yuConfig.url.TrimEnd('/') + '/api/tags'
    $yuOllama = Get-Command ollama -ErrorAction SilentlyContinue
    $yuOllamaPath = if ($yuOllama) { $yuOllama.Source } else { Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe' }
    if (-not (Test-Path -LiteralPath $yuOllamaPath)) {
        throw 'Instala Ollama desde https://ollama.com/download/windows antes de iniciar YU.'
    }
    try {
        $yuModels = Invoke-RestMethod $yuTagsUrl -TimeoutSec 5
    } catch {
        $env:OLLAMA_HOST = $yuConfig.url
        Start-Process -FilePath $yuOllamaPath -ArgumentList 'serve' -WindowStyle Hidden
        $yuReady = $false
        for ($yuAttempt = 0; $yuAttempt -lt 30; $yuAttempt++) {
            Start-Sleep -Seconds 1
            try {
                $yuModels = Invoke-RestMethod $yuTagsUrl -TimeoutSec 5
                $yuReady = $true
                break
            } catch { }
        }
        if (-not $yuReady) { throw "Ollama no respondió en $($yuConfig.url)." }
    }
    if ($yuConfig.model -notin @($yuModels.models | ForEach-Object name)) {
        throw "Falta descargar el modelo. Ejecuta: ollama pull $($yuConfig.model)"
    }
    & $PythonExe -X utf8 main.py
    if ($LASTEXITCODE -ne 0) { throw "YU terminó con código $LASTEXITCODE." }
}

# Impide duplicados entre el inicio automático y el acceso del Escritorio.
$yuMutex = New-Object System.Threading.Mutex($false, 'Local\YU_Assistant_Local')
$yuOwned = $false
try {
    try { $yuOwned = $yuMutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $yuOwned = $true }
    if (-not $yuOwned) { Write-Output 'El iniciador de YU ya está activo.'; exit 0 }
    do {
        try { Start-YuLocal } catch {
            if (-not $Supervise) { throw }
            $yuErrorLog = Join-Path $PSScriptRoot 'logs\startup-errors.log'
            New-Item -ItemType Directory -Path (Split-Path $yuErrorLog) -Force | Out-Null
            Add-Content -LiteralPath $yuErrorLog -Value ("$(Get-Date -Format o) $_")
        }
        if ($Supervise) { Start-Sleep -Seconds 30 }
    } while ($Supervise)
} finally {
    if ($yuOwned) { $yuMutex.ReleaseMutex() }
    $yuMutex.Dispose()
}