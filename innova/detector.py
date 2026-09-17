"""Detección de manos: MediaPipe (cámara real) o simulación (modo demo)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import cv2
import numpy as np

from innova.camara import esqueleto_mano_normalizado, pose_mano_demo
from innova.config import (
    CONFIANZA_DETECCION,
    CONFIANZA_SEGUIMIENTO,
    MAX_MANOS,
)


@dataclass
class Punto:
    """Landmark normalizado (x, y en 0–1 respecto al fotograma)."""

    x: float
    y: float
    z: float = 0.0


@dataclass
class ManoDetectada:
    """Una mano con sus 21 landmarks y lateralidad si se conoce."""

    puntos: list[Punto] = field(default_factory=list)
    lateralidad: str = "desconocida"  # "izquierda" | "derecha" | "desconocida"
    puntuacion: float = 0.0

    def caja(self) -> tuple[float, float, float, float]:
        """(xmin, ymin, xmax, ymax) normalizados."""
        xs = [p.x for p in self.puntos]
        ys = [p.y for p in self.puntos]
        return min(xs), min(ys), max(xs), max(ys)


class DetectorManos(Protocol):
    def detectar(self, frame_bgr: np.ndarray) -> list[ManoDetectada]: ...

    def cerrar(self) -> None: ...


class DetectorMediaPipe:
    """Detector real con MediaPipe Hands (API clásica solutions)."""

    def __init__(
        self,
        max_manos: int = MAX_MANOS,
        confianza_deteccion: float = CONFIANZA_DETECCION,
        confianza_seguimiento: float = CONFIANZA_SEGUIMIENTO,
        espejo: bool = True,
    ) -> None:
        import mediapipe as mp

        self._espejo = espejo
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=max_manos,
            model_complexity=1,
            min_detection_confidence=confianza_deteccion,
            min_tracking_confidence=confianza_seguimiento,
        )

    def detectar(self, frame_bgr: np.ndarray) -> list[ManoDetectada]:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        resultado = self._hands.process(rgb)
        rgb.flags.writeable = True

        if not resultado.multi_hand_landmarks:
            return []

        handedness = resultado.multi_handedness or []
        manos: list[ManoDetectada] = []
        for i, landmarks in enumerate(resultado.multi_hand_landmarks):
            lateralidad = "desconocida"
            puntuacion = 0.0
            if i < len(handedness) and handedness[i].classification:
                categoria = handedness[i].classification[0]
                # En vista espejo, MediaPipe etiqueta al revés de la persona usuaria.
                if categoria.label == "Left":
                    lateralidad = "derecha" if self._espejo else "izquierda"
                elif categoria.label == "Right":
                    lateralidad = "izquierda" if self._espejo else "derecha"
                puntuacion = float(categoria.score)

            puntos = [Punto(lm.x, lm.y, lm.z) for lm in landmarks.landmark]
            manos.append(
                ManoDetectada(
                    puntos=puntos,
                    lateralidad=lateralidad,
                    puntuacion=puntuacion,
                )
            )
        return manos

    def cerrar(self) -> None:
        self._hands.close()


class DetectorSimulado:
    """Devuelve una mano sintética alineada con FuenteDemo.

    Sirve para enseñar el overlay y el panel de reconocimiento sin cámara.
    """

    def detectar(self, frame_bgr: np.ndarray) -> list[ManoDetectada]:
        import time

        del frame_bgr
        t = time.monotonic()
        cx, cy, escala, angulo = pose_mano_demo(t)
        xy = esqueleto_mano_normalizado(cx, cy, escala, angulo, t)
        puntos = [Punto(x, y, 0.0) for x, y in xy]
        return [
            ManoDetectada(
                puntos=puntos,
                lateralidad="derecha",
                puntuacion=1.0,
            )
        ]

    def cerrar(self) -> None:
        return
