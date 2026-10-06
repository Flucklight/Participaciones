# Genera el ejecutable de Windows: dist\Participaciones\Participaciones.exe
# Uso (desde la raíz del proyecto):  powershell -ExecutionPolicy Bypass -File scripts\construir_exe.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = ".\.venv\Scripts\python.exe"

& $py -m pip install -q -r requirements-build.txt
& $py tools\crear_icono.py

# OneDrive bloquea archivos mientras los sincroniza: se borra dist\ antes de reconstruir
# y los temporales de PyInstaller se mandan a una carpeta fuera de OneDrive.
if (Test-Path -LiteralPath dist) { Remove-Item -LiteralPath dist -Recurse -Force }
$temporal = Join-Path $env:TEMP "participaciones_build"
& $py -m PyInstaller participaciones.spec --noconfirm --clean --workpath $temporal
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló (código $LASTEXITCODE)" }

$exe = Resolve-Path "dist\Participaciones\Participaciones.exe"
Write-Host "`nListo: $exe" -ForegroundColor Green
