"""Rutas de recursos y de datos de usuario de Mamatlatolli.

En desarrollo (``python app.py`` o ``python -m innova``) no cambia nada:
los recursos salen de ``assets/`` y las señas, la configuración y el récord
siguen en ``datos/`` del repositorio.

Empaquetado con PyInstaller, el programa puede vivir en una carpeta de solo
lectura. Las plantillas, ``config.json`` y el récord de Mini juego se escriben
en una carpeta del usuario:

- Windows: ``%LOCALAPPDATA%\\Mamatlatolli``
- macOS: ``~/Library/Application Support/Mamatlatolli``
- Linux: ``~/.local/share/Mamatlatolli``

``MAMATLATOLLI_DATOS`` fuerza esa carpeta si se define antes de arrancar.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Mapping
from pathlib import Path

NOMBRE_CARPETA_DATOS = "Mamatlatolli"
VARIABLE_DATOS = "MAMATLATOLLI_DATOS"


def aplicacion_empaquetada() -> bool:
    """True cuando el proceso es el ejecutable de PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def raiz_repositorio() -> Path:
    """Carpeta que contiene ``app.py`` cuando se corre desde el código."""
    return Path(__file__).resolve().parent.parent


def resolver_recursos(*, empaquetada: bool, meipass: str | None, raiz: Path) -> Path:
    """Raíz de solo lectura: ``_MEIPASS`` empaquetado, o el repositorio."""
    if empaquetada and meipass:
        return Path(meipass)
    return raiz


def resolver_datos_usuario(
    *,
    empaquetada: bool,
    plataforma: str,
    entorno: Mapping[str, str],
    home: Path,
    raiz: Path,
) -> Path:
    """Carpeta escribible de plantillas, configuración y récord."""
    override = entorno.get(VARIABLE_DATOS)
    if override:
        return Path(override)
    if not empaquetada:
        return raiz / "datos"
    if plataforma == "win32":
        base = entorno.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        return Path(base) / NOMBRE_CARPETA_DATOS
    if plataforma == "darwin":
        return home / "Library" / "Application Support" / NOMBRE_CARPETA_DATOS
    return home / ".local" / "share" / NOMBRE_CARPETA_DATOS


def ruta_recursos() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    return resolver_recursos(
        empaquetada=aplicacion_empaquetada(),
        meipass=str(meipass) if meipass else None,
        raiz=raiz_repositorio(),
    )


def ruta_datos_usuario() -> Path:
    return resolver_datos_usuario(
        empaquetada=aplicacion_empaquetada(),
        plataforma=sys.platform,
        entorno=os_entorno(),
        home=Path.home(),
        raiz=raiz_repositorio(),
    )


def os_entorno() -> Mapping[str, str]:
    import os

    return os.environ


def ruta_plantillas() -> Path:
    return ruta_datos_usuario() / "plantillas"


def ruta_ajustes() -> Path:
    return ruta_datos_usuario() / "config.json"


def ruta_assets() -> Path:
    return ruta_recursos() / "assets"


def ruta_sonidos() -> Path:
    return ruta_assets() / "sonidos"


def ruta_plantillas_incluidas() -> Path:
    """Plantillas de fábrica que viajan dentro del ejecutable, si las hay."""
    return ruta_recursos() / "datos" / "plantillas"


def carpeta_para_dialogos() -> Path:
    """Dónde abrir Exportar / Importar: Documentos, o la carpeta personal."""
    documentos = Path.home() / "Documents"
    if documentos.is_dir():
        return documentos
    return Path.home()


def sembrar_plantillas(origen: Path, destino: Path) -> int:
    """Copia JSON de fábrica que el usuario todavía no tiene.

    No pisa un archivo que ya existe. Si origen y destino son la misma
    carpeta, no hace nada.
    """
    origen = Path(origen)
    destino = Path(destino)
    if not origen.is_dir():
        return 0
    try:
        if origen.resolve() == destino.resolve():
            return 0
    except OSError:
        return 0
    copiadas = 0
    for archivo in sorted(p for p in origen.rglob("*.json") if p.is_file()):
        salida = destino / archivo.relative_to(origen)
        if salida.exists():
            continue
        try:
            salida.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(archivo, salida)
        except OSError:
            continue
        copiadas += 1
    return copiadas


def preparar_datos_usuario(
    *,
    empaquetada: bool | None = None,
    origen_plantillas: Path | None = None,
) -> Path:
    """Crea la carpeta de datos y, si está empaquetada, siembra plantillas nuevas."""
    datos = ruta_datos_usuario()
    destino = datos / "plantillas"
    try:
        destino.mkdir(parents=True, exist_ok=True)
    except OSError:
        return datos
    activa = aplicacion_empaquetada() if empaquetada is None else empaquetada
    if activa:
        origen = ruta_plantillas_incluidas() if origen_plantillas is None else origen_plantillas
        sembrar_plantillas(origen, destino)
    return datos
