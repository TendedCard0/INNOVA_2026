"""Dibujo de landmarks, conexiones y caja sobre el fotograma."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from innova import tema
from innova.config import CONEXIONES_MANO
from innova.detector import ManoDetectada

_FUENTES_CANDIDATAS = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/System/Library/Fonts/Helvetica.ttc"),
)


def dibujar_manos(frame_bgr: np.ndarray, manos: list[ManoDetectada]) -> np.ndarray:
    """Devuelve una copia del fotograma con el overlay de cada mano."""
    salida = frame_bgr.copy()
    alto, ancho = salida.shape[:2]
    for mano in manos:
        _dibujar_una_mano(salida, mano, ancho, alto)
    return salida


def poner_banner(frame_bgr: np.ndarray, texto: str, color_bgr: tuple[int, int, int]) -> np.ndarray:
    """Franja superior con texto (admite acentos)."""
    salida = frame_bgr.copy()
    alto, ancho = salida.shape[:2]
    franja = max(36, alto // 14)
    overlay = salida.copy()
    cv2.rectangle(overlay, (0, 0), (ancho, franja), tema.BGR_SOMBRA, -1)
    cv2.addWeighted(overlay, 0.72, salida, 0.28, 0, salida)
    return _texto_unicode(salida, texto, (16, 8), tamano=18, color_bgr=color_bgr)


def frame_mensaje(
    lineas: list[str],
    ancho: int,
    alto: int,
    color_titulo_bgr: tuple[int, int, int] | None = None,
) -> np.ndarray:
    """Fotograma estático con un recado centrado (errores, espera, etc.)."""
    if color_titulo_bgr is None:
        color_titulo_bgr = tema.BGR_CAJA
    img = np.zeros((alto, ancho, 3), dtype=np.uint8)
    img[:] = (32, 26, 22)
    cv2.rectangle(img, (24, 24), (ancho - 24, alto - 24), (54, 44, 40), 2)

    y = alto // 2 - 18 * len(lineas)
    for i, linea in enumerate(lineas):
        tamano = 26 if i == 0 else 18
        color = color_titulo_bgr if i == 0 else tema.BGR_TEXTO
        img = _texto_unicode(
            img,
            linea,
            (ancho // 2, y),
            tamano=tamano,
            color_bgr=color,
            centrado=True,
        )
        y += tamano + 14
    return img


def _dibujar_una_mano(
    frame: np.ndarray,
    mano: ManoDetectada,
    ancho: int,
    alto: int,
) -> None:
    if len(mano.puntos) < 21:
        return

    pix = [(int(p.x * ancho), int(p.y * alto)) for p in mano.puntos]

    for a, b in CONEXIONES_MANO:
        cv2.line(frame, pix[a], pix[b], tema.BGR_CONEXION, 2, cv2.LINE_AA)

    for i, p in enumerate(pix):
        radio = 5 if i == 0 else 4
        cv2.circle(frame, p, radio, tema.BGR_LANDMARK, -1, cv2.LINE_AA)
        cv2.circle(frame, p, radio, tema.BGR_SOMBRA, 1, cv2.LINE_AA)

    xmin, ymin, xmax, ymax = mano.caja()
    pad_x, pad_y = int(0.03 * ancho), int(0.03 * alto)
    p1 = (max(0, int(xmin * ancho) - pad_x), max(0, int(ymin * alto) - pad_y))
    p2 = (
        min(ancho - 1, int(xmax * ancho) + pad_x),
        min(alto - 1, int(ymax * alto) + pad_y),
    )
    cv2.rectangle(frame, p1, p2, tema.BGR_CAJA, 2, cv2.LINE_AA)

    etiqueta = _etiqueta_lateralidad(mano)
    _poner_etiqueta(frame, etiqueta, (p1[0], max(0, p1[1] - 28)))


def _etiqueta_lateralidad(mano: ManoDetectada) -> str:
    nombres = {
        "izquierda": "Izquierda",
        "derecha": "Derecha",
        "desconocida": "Mano",
    }
    base = nombres.get(mano.lateralidad, "Mano")
    if mano.puntuacion > 0:
        return f"{base}  {mano.puntuacion:.0%}"
    return base


def _poner_etiqueta(frame: np.ndarray, texto: str, origen: tuple[int, int]) -> None:
    alto, ancho = frame.shape[:2]
    x, y = origen
    ancho_etiq = min(ancho - 8, max(80, 11 * len(texto) + 18))
    alto_etiq = 26
    x = max(0, min(x, ancho - ancho_etiq))
    y = max(0, min(y, alto - alto_etiq))
    cv2.rectangle(frame, (x, y), (x + ancho_etiq, y + alto_etiq), tema.BGR_SOMBRA, -1)
    pintado = _texto_unicode(
        frame,
        texto,
        (x + 8, y + 4),
        tamano=16,
        color_bgr=tema.BGR_TEXTO,
    )
    frame[:] = pintado


def _texto_unicode(
    frame_bgr: np.ndarray,
    texto: str,
    origen: tuple[int, int],
    tamano: int,
    color_bgr: tuple[int, int, int],
    centrado: bool = False,
) -> np.ndarray:
    """Dibuja texto con Pillow para respetar acentos del español."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    imagen = Image.fromarray(rgb)
    draw = ImageDraw.Draw(imagen)
    fuente = _fuente(tamano)
    color = (color_bgr[2], color_bgr[1], color_bgr[0])
    x, y = origen
    if centrado:
        bbox = draw.textbbox((0, 0), texto, font=fuente)
        x -= (bbox[2] - bbox[0]) // 2
    draw.text((x, y), texto, font=fuente, fill=color)
    return cv2.cvtColor(np.array(imagen), cv2.COLOR_RGB2BGR)


def _fuente(tamano: int) -> ImageFont.ImageFont:
    for ruta in _FUENTES_CANDIDATAS:
        if ruta.exists():
            try:
                return ImageFont.truetype(str(ruta), tamano)
            except OSError:
                continue
    return ImageFont.load_default()
