"""Captura de video: cámara real o fuente de demostración."""

from __future__ import annotations

import math
import time
from typing import Protocol

import cv2
import numpy as np

from innova.config import ALTO_VIDEO, ANCHO_VIDEO


class CamaraNoDisponibleError(RuntimeError):
    """No se pudo abrir ningún dispositivo de captura."""


class FuenteVideo(Protocol):
    """Cualquier origen de fotogramas BGR para el pipeline."""

    def leer(self) -> np.ndarray | None: ...

    def esta_abierta(self) -> bool: ...

    def liberar(self) -> None: ...

    def descripcion(self) -> str: ...


class Camara:
    """Envuelve cv2.VideoCapture y prueba varios índices si hace falta."""

    def __init__(self, indice_preferido: int = 0) -> None:
        self._captura, self._indice = _abrir_dispositivo(indice_preferido)

    def leer(self) -> np.ndarray | None:
        ok, frame = self._captura.read()
        if not ok or frame is None or frame.size == 0:
            return None
        return frame

    def esta_abierta(self) -> bool:
        return bool(self._captura.isOpened())

    def liberar(self) -> None:
        if self._captura is not None:
            self._captura.release()

    def descripcion(self) -> str:
        return f"Cámara {self._indice}"


class FuenteDemo:
    """Video sintético para probar la interfaz sin hardware de cámara.

    Dibuja una mano esquemática en movimiento. El detector simulado coloca
    landmarks sobre esa misma pose para que el overlay se vea completo.
    """

    def __init__(self, ancho: int = ANCHO_VIDEO, alto: int = ALTO_VIDEO) -> None:
        self._ancho = ancho
        self._alto = alto
        self._abierta = True

    def leer(self) -> np.ndarray | None:
        if not self._abierta:
            return None
        return dibujar_escena_demo(self._ancho, self._alto, time.monotonic())

    def esta_abierta(self) -> bool:
        return self._abierta

    def liberar(self) -> None:
        self._abierta = False

    def descripcion(self) -> str:
        return "Modo demostración (sin cámara)"


def pose_mano_demo(t: float) -> tuple[float, float, float, float]:
    """Devuelve (cx, cy, escala, angulo_rad) de la mano sintética.

    Compartido con el detector simulado para que landmarks y dibujo coincidan.
    """
    cx = 0.52 + 0.10 * math.sin(t * 0.9)
    cy = 0.62 + 0.04 * math.cos(t * 0.7)
    escala = 0.26
    angulo = 0.18 * math.sin(t * 0.6)
    return cx, cy, escala, angulo


def dibujar_escena_demo(ancho: int, alto: int, t: float) -> np.ndarray:
    """Genera un fotograma BGR con fondo y una mano dibujada a mano alzada."""
    degradado = np.linspace(18, 42, alto, dtype=np.float32)
    fondo = np.stack((degradado + 8, degradado + 4, degradado), axis=1)
    frame = np.repeat(fondo[:, None, :], ancho, axis=1).astype(np.uint8)

    cx, cy, escala, angulo = pose_mano_demo(t)
    puntos = esqueleto_mano_normalizado(cx, cy, escala, angulo, t)
    _dibujar_mano_esquematica(frame, puntos)
    return frame


def esqueleto_mano_normalizado(
    cx: float,
    cy: float,
    escala: float,
    angulo: float,
    t: float = 0.0,
) -> list[tuple[float, float]]:
    """21 puntos (x, y) normalizados 0–1, palma de frente y dedos hacia arriba."""
    # Coordenadas locales: origen en la muñeca, Y negativo = hacia arriba.
    curl = 0.10 * math.sin(t * 2.1)
    plantilla: tuple[tuple[float, float], ...] = (
        (0.00, 0.00),
        (-0.14, -0.10),
        (-0.26, -0.24),
        (-0.34, -0.38),
        (-0.40, -0.52),
        (-0.18, -0.40),
        (-0.20, -0.58),
        (-0.21, -0.72),
        (-0.22, -0.90),
        (0.00, -0.42),
        (0.00, -0.62),
        (0.00, -0.78),
        (0.00, -0.98),
        (0.16, -0.40),
        (0.18, -0.58),
        (0.19, -0.72),
        (0.20, -0.88),
        (0.30, -0.34),
        (0.34, -0.48),
        (0.36, -0.60),
        (0.38, -0.74),
    )

    cos_a, sin_a = math.cos(angulo), math.sin(angulo)
    puntos: list[tuple[float, float]] = []
    for i, (x, y) in enumerate(plantilla):
        # Los dedos (no la palma) se recogen un poco con el tiempo.
        if i in {4, 8, 12, 16, 20}:
            y += curl
        xr = x * cos_a - y * sin_a
        yr = x * sin_a + y * cos_a
        puntos.append((cx + xr * escala, cy + yr * escala))
    return puntos


def _dibujar_mano_esquematica(
    frame: np.ndarray,
    puntos_norm: list[tuple[float, float]],
) -> None:
    alto, ancho = frame.shape[:2]
    pts = [(int(x * ancho), int(y * alto)) for x, y in puntos_norm]
    palma = np.array([pts[0], pts[1], pts[5], pts[9], pts[13], pts[17]], dtype=np.int32)
    overlay = frame.copy()
    cv2.fillConvexPoly(overlay, palma, (90, 130, 190))
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    def segmento(a: int, b: int, grosor: int) -> None:
        cv2.line(frame, pts[a], pts[b], (70, 115, 175), grosor, cv2.LINE_AA)

    for a, b, g in (
        (0, 1, 14),
        (1, 2, 12),
        (2, 3, 11),
        (3, 4, 10),
        (0, 5, 16),
        (5, 6, 12),
        (6, 7, 11),
        (7, 8, 10),
        (0, 9, 16),
        (9, 10, 12),
        (10, 11, 11),
        (11, 12, 10),
        (0, 13, 16),
        (13, 14, 12),
        (14, 15, 11),
        (15, 16, 10),
        (0, 17, 14),
        (17, 18, 11),
        (18, 19, 10),
        (19, 20, 9),
        (5, 9, 14),
        (9, 13, 14),
        (13, 17, 14),
    ):
        segmento(a, b, g)

    for p in pts:
        cv2.circle(frame, p, 7, (120, 165, 210), -1, cv2.LINE_AA)


def _abrir_dispositivo(indice_preferido: int) -> tuple[cv2.VideoCapture, int]:
    vistos: list[int] = []
    for indice in [indice_preferido, *[i for i in range(3) if i != indice_preferido]]:
        vistos.append(indice)
        captura = cv2.VideoCapture(indice)
        if not captura.isOpened():
            captura.release()
            continue
        captura.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO_VIDEO)
        captura.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO_VIDEO)
        ok, frame = captura.read()
        if ok and frame is not None and frame.size > 0:
            return captura, indice
        captura.release()

    raise CamaraNoDisponibleError(
        "No se encontró una cámara disponible "
        f"(se probaron los índices {vistos})."
    )
