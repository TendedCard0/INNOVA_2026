"""Foto de apoyo de Mini juego: recorte de la cámara, junto a la plantilla.

No hay imágenes de fábrica. Si quien captura una letra estática lo pide,
se guarda un JPEG del recorte de la mano en ``plantillas/referencias/``,
dentro de la carpeta de datos del usuario (la misma de ``innova/rutas.py``).
La plantilla solo guarda la ruta relativa. Si el archivo no está, el juego
sigue y muestra un aviso en lugar de la foto.
"""

from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np

from innova.detector import ManoDetectada
from innova.esquema import (
    CARPETA_REFERENCIAS,
    MAX_BYTES_IMAGEN_APOYO,
    ImagenApoyo,
    archivo_apoyo_permitido,
)

LADO_MAX_RECORTE = 240
CALIDAD_JPEG = 80
_MARGEN_CAJA = 0.45


def recortar_mano_jpeg(
    frame_bgr: np.ndarray | None,
    mano: ManoDetectada | None,
    *,
    lado_max: int = LADO_MAX_RECORTE,
    calidad: int = CALIDAD_JPEG,
) -> bytes | None:
    """JPEG del recorte alrededor de la mano, o None si el fotograma no sirve."""
    if mano is None or not mano.puntos:
        return None
    if not isinstance(frame_bgr, np.ndarray) or frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
        return None
    if frame_bgr.size == 0:
        return None
    alto, ancho = frame_bgr.shape[:2]
    if alto < 8 or ancho < 8:
        return None
    xmin, ymin, xmax, ymax = mano.caja()
    x0, y0 = xmin * ancho, ymin * alto
    x1, y1 = xmax * ancho, ymax * alto
    ancho_caja = max(1.0, x1 - x0)
    alto_caja = max(1.0, y1 - y0)
    pad_x = max(12.0, ancho_caja * _MARGEN_CAJA)
    pad_y = max(12.0, alto_caja * _MARGEN_CAJA)
    ix0 = max(0, int(np.floor(x0 - pad_x)))
    iy0 = max(0, int(np.floor(y0 - pad_y)))
    ix1 = min(ancho, int(np.ceil(x1 + pad_x)))
    iy1 = min(alto, int(np.ceil(y1 + pad_y)))
    if ix1 - ix0 < 8 or iy1 - iy0 < 8:
        return None
    recorte = frame_bgr[iy0:iy1, ix0:ix1]
    h, w = recorte.shape[:2]
    escala = lado_max / max(h, w)
    if escala < 1.0:
        nuevo = (max(1, int(round(w * escala))), max(1, int(round(h * escala))))
        recorte = cv2.resize(recorte, nuevo, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(
        ".jpg",
        recorte,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(calidad)],
    )
    if not ok:
        return None
    datos = bytes(buf)
    if not datos or len(datos) > MAX_BYTES_IMAGEN_APOYO or datos[:2] != b"\xff\xd8":
        return None
    return datos


def guardar_jpeg_apoyo(
    datos: bytes,
    etiqueta: str,
    directorio_plantillas: Path,
    marca: str = "",
) -> str | None:
    """Escribe el JPEG y devuelve la ruta relativa ``referencias/<nombre>.jpg``."""
    if not datos or len(datos) > MAX_BYTES_IMAGEN_APOYO or datos[:2] != b"\xff\xd8":
        return None
    directorio = Path(directorio_plantillas)
    rel = _nombre_libre(directorio, etiqueta, marca)
    destino = directorio / rel
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(datos)
    except OSError:
        return None
    return rel


def ruta_imagen_segura(directorio_plantillas: Path, archivo: str) -> Path | None:
    """Resuelve la foto dentro de la carpeta de plantillas, o None si la ruta no es segura."""
    rel = archivo_apoyo_permitido(archivo)
    if rel is None:
        return None
    base = Path(directorio_plantillas).resolve()
    destino = (base / rel).resolve()
    try:
        destino.relative_to(base / CARPETA_REFERENCIAS)
    except ValueError:
        return None
    return destino


def materializar_imagen(muestra: object, directorio_plantillas: Path) -> None:
    """Si la muestra trae bytes de una foto, los escribe y deja solo la ruta.

    Sirve al importar un paquete. Si la ruta no existe y tampoco hay bytes,
    la seña se queda sin foto y el resto de la plantilla no cambia.
    """
    imagen = getattr(muestra, "imagen_apoyo", None)
    if not isinstance(imagen, ImagenApoyo):
        return
    directorio = Path(directorio_plantillas)
    if imagen.datos:
        rel = archivo_apoyo_permitido(imagen.archivo) or _nombre_libre(
            directorio,
            getattr(muestra, "etiqueta", "") or "letra",
            "",
        )
        destino = directorio / rel
        try:
            if destino.is_file() and destino.read_bytes() != imagen.datos:
                rel = _nombre_libre(directorio, getattr(muestra, "etiqueta", "") or "letra", "importada")
                destino = directorio / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(imagen.datos)
        except OSError:
            muestra.imagen_apoyo = None  # type: ignore[attr-defined]
            return
        muestra.imagen_apoyo = ImagenApoyo(archivo=rel, datos=None)  # type: ignore[attr-defined]
        return
    ruta = ruta_imagen_segura(directorio, imagen.archivo)
    if ruta is None or not ruta.is_file():
        muestra.imagen_apoyo = None  # type: ignore[attr-defined]


def leer_jpeg(directorio_plantillas: Path, archivo: str) -> bytes | None:
    ruta = ruta_imagen_segura(directorio_plantillas, archivo)
    if ruta is None or not ruta.is_file():
        return None
    try:
        datos = ruta.read_bytes()
    except OSError:
        return None
    if not datos or len(datos) > MAX_BYTES_IMAGEN_APOYO or datos[:2] != b"\xff\xd8":
        return None
    return datos


def _nombre_libre(directorio: Path, etiqueta: str, marca: str) -> str:
    base = _trozo(etiqueta) or "letra"
    sello = _trozo(marca)[:15]
    tallo = f"{base}_{sello}" if sello else base
    rel = f"{CARPETA_REFERENCIAS}/{tallo}.jpg"
    candidato = Path(directorio) / rel
    n = 2
    while candidato.exists():
        rel = f"{CARPETA_REFERENCIAS}/{tallo}_{n}.jpg"
        candidato = Path(directorio) / rel
        n += 1
    permitido = archivo_apoyo_permitido(rel)
    if permitido is None:
        return f"{CARPETA_REFERENCIAS}/letra.jpg"
    return permitido


def _trozo(texto: str) -> str:
    limpio = re.sub(r"[^A-Za-z0-9_-]", "", texto or "")
    return limpio[:40]
