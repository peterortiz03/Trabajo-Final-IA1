$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    & "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\src\interfaz.py" --config "$PSScriptRoot\config\aplicacion.json"
    $codigoSalida = $LASTEXITCODE
} finally { Pop-Location }
exit $codigoSalida
