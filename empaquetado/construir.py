"""Construye el instalador de Mamatlatolli en Windows.

Desde la raíz del repositorio, en PowerShell::

    python empaquetado/construir.py

En Linux o macOS no genera un .exe: el instalador lo produce el workflow
de GitHub Actions en ``windows-latest``. ``--comprobar`` solo revisa que
estén los archivos de empaquetado y sí puede correr en cualquier sistema.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

MENSAJE_SOLO_WINDOWS = """\
Mamatlatolli: el instalador .exe solo se puede construir en Windows.

Este equipo no es Windows, así que aquí no se genera un binario fingido.
En GitHub, el workflow «Instalador Windows de Mamatlatolli» corre en
windows-latest y publica el artifact Mamatlatolli-Windows con:

  - Mamatlatolli-Setup.exe
  - Mamatlatolli-portable.zip

Para descargarlo: repositorio → Actions → Instalador Windows de Mamatlatolli
→ el run más reciente → Artifacts. También se lanza a mano con «Run workflow».
"""

SONIDOS = ("acierto.wav", "error.wav", "record.wav", "tic.wav", "tac.wav")


def raiz_repositorio() -> Path:
    return Path(__file__).resolve().parent.parent


def version_del_producto(raiz: Path | None = None) -> str:
    base = raiz if raiz is not None else raiz_repositorio()
    texto = (base / "innova" / "__init__.py").read_text(encoding="utf-8")
    coincidencia = re.search(r'__version__\s*=\s*"([^"]+)"', texto)
    if coincidencia is None:
        raise RuntimeError("No encontré __version__ en innova/__init__.py")
    return coincidencia.group(1)


def version_info_windows(version: str) -> str:
    """Cuatro números para el recurso de versión de Windows."""
    partes = [trozo for trozo in version.split(".") if trozo != ""]
    if not partes or any(not trozo.isdigit() for trozo in partes):
        raise RuntimeError(f"Versión no numérica: {version}")
    while len(partes) < 4:
        partes.append("0")
    return ".".join(partes[:4])


def comando_pyinstaller(python: str, raiz: Path) -> list[str]:
    return [
        python,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(raiz / "dist"),
        "--workpath",
        str(raiz / "build"),
        str(raiz / "empaquetado" / "mamatlatolli.spec"),
    ]


def buscar_iscc() -> Path | None:
    import os

    variable = os.environ.get("ISCC") or os.environ.get("INNO_SETUP_ISCC")
    if variable and Path(variable).is_file():
        return Path(variable)
    programas_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    programas = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidatos = [
        Path(programas_x86) / "Inno Setup 6" / "ISCC.exe",
        Path(programas) / "Inno Setup 6" / "ISCC.exe",
    ]
    for candidato in candidatos:
        if candidato.is_file():
            return candidato
    encontrado = shutil.which("ISCC") or shutil.which("iscc")
    if encontrado:
        return Path(encontrado)
    return None


def comando_iscc(iscc: Path, iss: Path, version: str, *, maquina: bool) -> list[str]:
    comando = [
        str(iscc),
        f"/DMyAppVersion={version}",
        f"/DMyVersionInfo={version_info_windows(version)}",
    ]
    if maquina:
        comando.append("/DInstalacionDeMaquina")
    comando.append(str(iss))
    return comando


def empaquetar_portable(origen: Path, destino: Path) -> None:
    if destino.exists():
        destino.unlink()
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED) as archivo:
        for ruta in origen.rglob("*"):
            if ruta.is_file():
                dentro = (Path("Mamatlatolli") / ruta.relative_to(origen)).as_posix()
                archivo.write(ruta, dentro)


def comprobar(raiz: Path | None = None) -> list[str]:
    """Revisa archivos de empaquetado. No construye nada."""
    base = raiz if raiz is not None else raiz_repositorio()
    errores: list[str] = []
    necesarios = [
        base / "app.py",
        base / "assets" / "icono.ico",
        base / "assets" / "icono.png",
        base / "assets" / "logo.png",
        base / "empaquetado" / "mamatlatolli.spec",
        base / "empaquetado" / "mamatlatolli.iss",
        base / "empaquetado" / "aviso-instalacion.txt",
        base / "innova" / "__init__.py",
    ]
    for ruta in necesarios:
        if not ruta.is_file():
            errores.append(f"Falta {ruta.relative_to(base)}")
    for nombre in SONIDOS:
        if not (base / "assets" / "sonidos" / nombre).is_file():
            errores.append(f"Falta assets/sonidos/{nombre}")
    spec = base / "empaquetado" / "mamatlatolli.spec"
    if spec.is_file():
        texto = spec.read_text(encoding="utf-8")
        for fragmento in ("Mamatlatolli", "icono.ico", "assets", "console=False", "upx=False"):
            if fragmento not in texto:
                errores.append(f"El spec no menciona {fragmento}")
        if re.search(r'RAIZ\s*/\s*"datos"', texto) or "datos/plantillas" in texto:
            errores.append("El spec no debe empaquetar datos/plantillas")
    iss = base / "empaquetado" / "mamatlatolli.iss"
    if iss.is_file():
        texto = iss.read_text(encoding="utf-8-sig")
        for fragmento in (
            "Mamatlatolli",
            "icono.ico",
            "autodesktop",
            "Desinstalar",
            "localappdata",
            "UninstallDisplayIcon",
        ):
            if fragmento not in texto:
                errores.append(f"El instalador no menciona {fragmento}")
    try:
        version_del_producto(base)
    except (OSError, RuntimeError) as exc:
        errores.append(str(exc))
    return errores


def dependencias_listas() -> str | None:
    faltan: list[str] = []
    for nombre in ("cv2", "mediapipe", "customtkinter", "numpy", "PIL", "PyInstaller"):
        try:
            __import__(nombre)
        except ImportError:
            faltan.append(nombre)
    if not faltan:
        return None
    return (
        "Faltan paquetes para construir Mamatlatolli: "
        + ", ".join(faltan)
        + ".\nInstala requirements.txt y empaquetado/requirements-build.txt."
    )


def construir(raiz: Path, *, maquina: bool, python: str | None = None) -> int:
    interprete = python or sys.executable
    aviso = dependencias_listas()
    if aviso:
        print(aviso, file=sys.stderr)
        return 1
    carpeta = raiz / "dist" / "Mamatlatolli"
    codigo = _ejecutar(comando_pyinstaller(interprete, raiz))
    if codigo != 0:
        return codigo
    exe = carpeta / "Mamatlatolli.exe"
    if not exe.is_file():
        print(f"PyInstaller no dejó {exe}", file=sys.stderr)
        return 1
    shutil.copyfile(raiz / "assets" / "icono.ico", carpeta / "icono.ico")
    portable = raiz / "dist" / "Mamatlatolli-portable.zip"
    empaquetar_portable(carpeta, portable)
    iscc = buscar_iscc()
    if iscc is None:
        print(
            "No encontré ISCC.exe (Inno Setup 6). Instálalo y vuelve a correr, "
            "o define la variable ISCC con la ruta del compilador.\n"
            f"La carpeta portable sí quedó en {portable}",
            file=sys.stderr,
        )
        return 1
    version = version_del_producto(raiz)
    iss = raiz / "empaquetado" / "mamatlatolli.iss"
    codigo = _ejecutar(comando_iscc(iscc, iss, version, maquina=maquina))
    if codigo != 0:
        return codigo
    setup = raiz / "dist" / "Mamatlatolli-Setup.exe"
    if not setup.is_file():
        print(f"Inno Setup no dejó {setup}", file=sys.stderr)
        return 1
    print()
    print("Listo. Mamatlatolli quedó empaquetado:")
    print(f"  Instalador: {setup}")
    print(f"  Portable:   {portable}")
    print("Las señas, la configuración y el récord se guardan en %LOCALAPPDATA%\\Mamatlatolli")
    return 0


def _ejecutar(comando: list[str]) -> int:
    print(">", subprocess.list2cmdline(comando) if sys.platform == "win32" else " ".join(comando))
    resultado = subprocess.run(comando, check=False)
    return resultado.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Construye el instalador de Mamatlatolli para Windows.",
    )
    parser.add_argument(
        "--comprobar",
        action="store_true",
        help="Solo revisa que estén los archivos de empaquetado. No crea un .exe.",
    )
    parser.add_argument(
        "--maquina",
        action="store_true",
        help="Instala en Program Files para toda la máquina (hace falta administrador). Por omisión se instala en el perfil del usuario.",
    )
    args = parser.parse_args(argv)
    if args.comprobar:
        errores = comprobar()
        if errores:
            print("\n".join(errores), file=sys.stderr)
            return 1
        print("Listo para construir Mamatlatolli en Windows.")
        return 0
    if sys.platform != "win32":
        print(MENSAJE_SOLO_WINDOWS)
        return 2
    return construir(raiz_repositorio(), maquina=args.maquina)


if __name__ == "__main__":
    sys.exit(main())
