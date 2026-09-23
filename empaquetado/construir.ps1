# Construye el instalador de Mamatlatolli. Hay que ejecutarlo en Windows.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
python empaquetado\construir.py @args
exit $LASTEXITCODE
