"""Ganchos de cuerpo y rostro para el vocabulario completo de Mamatlatolli.

Este módulo es el único sitio que deberá activar MediaPipe Pose (33 puntos)
y Face Mesh / Face Landmarker (malla facial). Hoy las banderas están en
False y las extractoras devuelven ``None``: el esquema ya acepta
``pose`` / ``rostro`` (objeto con ``landmarks`` o null) en la muestra y
en cada fotograma de ``secuencia``.

Cuando se activen:

1. Pon ``POSE_ACTIVA`` / ``ROSTRO_ACTIVO`` en True.
2. Implementa ``extraer_pose`` / ``extraer_rostro`` (sin tocar la UI).
3. El pipeline de captura y el reconocedor ya llaman estas funciones y
   rellenan el JSON. Abecedario y Vocabulario no se reescriben.

Vocabulario, en esta fase, sigue comparando solo landmarks de mano.
"""

from __future__ import annotations

from typing import Any

import numpy as np

# Cambiar a True cuando el detector de cuerpo/cara esté listo (no reescribe UI).
POSE_ACTIVA = False
ROSTRO_ACTIVO = False

# Conteos de referencia (MediaPipe clásico / Tasks).
N_LANDMARKS_POSE = 33
N_LANDMARKS_ROSTRO = 478


def extraer_pose(frame_bgr: np.ndarray | None) -> dict[str, Any] | None:
    """Landmarks de MediaPipe Pose o ``None`` si el gancho no está vivo."""
    del frame_bgr
    if not POSE_ACTIVA:
        return None
    return None


def extraer_rostro(frame_bgr: np.ndarray | None) -> dict[str, Any] | None:
    """Landmarks de MediaPipe Face Mesh o ``None`` si el gancho no está vivo."""
    del frame_bgr
    if not ROSTRO_ACTIVO:
        return None
    return None


def cuerpo_disponible() -> bool:
    """True cuando al menos un gancho de cuerpo/cara está activo."""
    return bool(POSE_ACTIVA or ROSTRO_ACTIVO)


def anotar_cuerpo(frame_bgr: np.ndarray | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Par ``(pose, rostro)`` listo para el esquema (hoy: ``(None, None)``)."""
    return extraer_pose(frame_bgr), extraer_rostro(frame_bgr)
