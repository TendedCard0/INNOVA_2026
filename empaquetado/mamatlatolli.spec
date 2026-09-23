# -*- mode: python ; coding: utf-8 -*-
"""Empaqueta Mamatlatolli en una carpeta (onedir) para el instalador.

PyInstaller no cruza de sistema: este spec se ejecuta en Windows.
No incluye ``datos/*.json``: las señas locales no deben viajar dentro del .exe.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

RAIZ = Path(SPECPATH).resolve().parent

datas: list[tuple[str, str]] = [(str(RAIZ / "assets"), "assets")]
binaries: list[tuple[str, str]] = []
hiddenimports: list[str] = [
    "winsound",
    "mediapipe",
    "mediapipe.python.solutions.hands",
    "mediapipe.python.solutions.pose",
    "mediapipe.python.solutions.face_mesh",
]

for paquete in ("mediapipe", "customtkinter"):
    datos_paquete, binarios_paquete, ocultos_paquete = collect_all(paquete)
    datas += datos_paquete
    binaries += binarios_paquete
    hiddenimports += ocultos_paquete

hiddenimports += collect_submodules("innova")

a = Analysis(
    [str(RAIZ / "app.py")],
    pathex=[str(RAIZ)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "IPython", "notebook"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Mamatlatolli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(RAIZ / "assets" / "icono.ico"),
    contents_directory="_internal",
)

# La carpeta _internal la define el EXE (contents_directory). COLLECT la hereda.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Mamatlatolli",
)
