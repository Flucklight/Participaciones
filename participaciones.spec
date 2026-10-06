# -*- mode: python ; coding: utf-8 -*-
# Receta de PyInstaller. Uso (desde la raíz del proyecto):
#   .venv/Scripts/python.exe -m PyInstaller participaciones.spec --noconfirm --clean
# Resultado: dist/Participaciones/Participaciones.exe (carpeta completa; no se mueve el .exe solo).

from PyInstaller.utils.hooks import collect_data_files

datos = [("assets/icon/app.ico", "assets/icon")]
datos += collect_data_files("customtkinter")  # temas y fuentes que customtkinter lee en ejecución

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datos,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "tests", "tools"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Participaciones",
    icon="assets/icon/app.ico",
    console=False,          # app de ventanas: sin consola negra
    debug=False,
    strip=False,
    upx=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Participaciones",
)
