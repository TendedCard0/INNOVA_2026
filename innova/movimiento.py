"""Detector de movimiento de la mano para enrutar estático vs DTW."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from innova.config import (
    SENSIBILIDAD_MOVIMIENTO,
    UMBRAL_MOVIMIENTO,
    VENTANA_MOVIMIENTO_S,
)


@dataclass
class EstadoMovimiento:
    """Salida del detector para un fotograma."""

    puntuacion: float
    en_movimiento: bool
    umbral: float
    muestras: int
    ventana_s: float


class DetectorMovimiento:
    """Mide si la muñeca se desplazó con claridad en una ventana corta.

    Ventana por omisión: 0,6 s (rango 0,4–0,8 s). La *sensibilidad* baja el
    umbral (1.0 = más fácil pasar a dinámico; 0.0 = más exigente).
    """

    def __init__(
        self,
        *,
        ventana_s: float = VENTANA_MOVIMIENTO_S,
        umbral: float = UMBRAL_MOVIMIENTO,
        sensibilidad: float = SENSIBILIDAD_MOVIMIENTO,
    ) -> None:
        self.ventana_s = float(max(0.40, min(0.80, ventana_s)))
        self.umbral_base = float(umbral)
        self.sensibilidad = float(max(0.0, min(1.0, sensibilidad)))
        self._puntos: deque[tuple[float, float, float]] = deque()  # t, x, y

    def reiniciar(self) -> None:
        self._puntos.clear()

    def umbral_efectivo(self) -> float:
        """Más sensibilidad → umbral más bajo."""
        factor = 1.70 - 1.20 * self.sensibilidad
        return max(0.015, self.umbral_base * factor)

    def actualizar(
        self,
        muneca_xy: tuple[float, float] | None,
        t: float,
    ) -> EstadoMovimiento:
        if muneca_xy is None:
            self._puntos.clear()
            return EstadoMovimiento(
                puntuacion=0.0,
                en_movimiento=False,
                umbral=self.umbral_efectivo(),
                muestras=0,
                ventana_s=self.ventana_s,
            )

        x, y = float(muneca_xy[0]), float(muneca_xy[1])
        self._puntos.append((float(t), x, y))
        corte = float(t) - self.ventana_s
        while self._puntos and self._puntos[0][0] < corte:
            self._puntos.popleft()

        puntuacion = puntuacion_movimiento([(p[1], p[2]) for p in self._puntos])
        umbral = self.umbral_efectivo()
        return EstadoMovimiento(
            puntuacion=puntuacion,
            en_movimiento=puntuacion >= umbral,
            umbral=umbral,
            muestras=len(self._puntos),
            ventana_s=self.ventana_s,
        )


def puntuacion_movimiento(trayectoria: list[tuple[float, float]]) -> float:
    """Combina longitud de camino y dispersión de la muñeca (coords 0–1).

    Una mano quieta (temblor de unos milésimas) queda cerca de 0. Un barrido
    tipo J/Z en ~0,6 s suele superar 0,08–0,15.
    """
    n = len(trayectoria)
    if n < 3:
        return 0.0

    xs = [p[0] for p in trayectoria]
    ys = [p[1] for p in trayectoria]
    camino = 0.0
    for i in range(1, n):
        dx = xs[i] - xs[i - 1]
        dy = ys[i] - ys[i - 1]
        camino += (dx * dx + dy * dy) ** 0.5

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var = sum((x - mean_x) ** 2 + (y - mean_y) ** 2 for x, y in zip(xs, ys)) / n
    dispersion = var**0.5
    desplazamiento = ((xs[-1] - xs[0]) ** 2 + (ys[-1] - ys[0]) ** 2) ** 0.5

    # Camino captura el trazo; desplazamiento evita premiar solo el temblor.
    return 0.55 * camino + 0.25 * desplazamiento + 0.20 * (3.0 * dispersion)
