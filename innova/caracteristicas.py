"""Normalización de landmarks y comparación de vectores (plantillas estáticas)."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from innova.config import SATURACION_DISTANCIA

# MediaPipe Hands: 21 puntos. Usamos la muñeca (0) y el MCP del medio (9)
# para fijar origen y escala.
_INDICE_MUNECA = 0
_INDICE_MCP_MEDIO = 9
_PUNTAS = (4, 8, 12, 16, 20)  # pulgar, índice, medio, anular, meñique
_PALMA = (0, 5, 9, 13, 17)

N_LANDMARKS_MANO = 21


class ErrorCaracteristicas(ValueError):
    """Landmarks insuficientes o degenerados para armar el vector."""


def matriz_desde_puntos(puntos: Sequence[object]) -> np.ndarray:
    """Convierte 21 landmarks (Punto o [x, y, z]) en una matriz (21, 3)."""
    if len(puntos) < N_LANDMARKS_MANO:
        raise ErrorCaracteristicas(
            f"Se necesitan {N_LANDMARKS_MANO} landmarks de la mano, hay {len(puntos)}."
        )
    filas: list[tuple[float, float, float]] = []
    for p in list(puntos)[:N_LANDMARKS_MANO]:
        if hasattr(p, "x") and hasattr(p, "y"):
            z = float(getattr(p, "z", 0.0) or 0.0)
            filas.append((float(p.x), float(p.y), z))
        else:
            seq = list(p)  # type: ignore[arg-type]
            x = float(seq[0])
            y = float(seq[1])
            z = float(seq[2]) if len(seq) > 2 else 0.0
            filas.append((x, y, z))
    return np.asarray(filas, dtype=np.float64)


def normalizar_landmarks(puntos: Sequence[object] | np.ndarray) -> np.ndarray:
    """Trasladar a la muñeca y escalar por el tamaño de la palma.

    No se rota a propósito: varias letras LSM se distinguen por la orientación
    de la mano. El resultado es una matriz (21, 3), invariante a traslación
    y (aprox.) a la distancia a la cámara.
    """
    coords = (
        np.asarray(puntos, dtype=np.float64)
        if isinstance(puntos, np.ndarray)
        else matriz_desde_puntos(puntos)
    )
    if coords.shape != (N_LANDMARKS_MANO, 3):
        raise ErrorCaracteristicas(
            f"Se esperaba una matriz (21, 3); se recibió {coords.shape}."
        )

    origen = coords[_INDICE_MUNECA].copy()
    centrado = coords - origen
    escala = float(np.linalg.norm(centrado[_INDICE_MCP_MEDIO]))
    if escala < 1e-6:
        normas_palma = np.linalg.norm(centrado[list(_PALMA)], axis=1)
        escala = float(np.max(normas_palma))
    if escala < 1e-6:
        normas = np.linalg.norm(centrado, axis=1)
        escala = float(np.max(normas))
    if escala < 1e-6:
        raise ErrorCaracteristicas("La mano es degenerada (todos los puntos coinciden).")
    return centrado / escala


def vector_caracteristicas(normalizados: np.ndarray) -> np.ndarray:
    """Vector denso para matching: 63 coords + distancias de puntas.

    - 21×3 coordenadas ya normalizadas (muñeca en el origen, palma de tamaño 1)
    - 5 distancias muñeca→punta
    - 10 distancias entre pares de puntas

    Total: 78 números. Suficiente para plantillas; sin entrenar un modelo.
    """
    pts = np.asarray(normalizados, dtype=np.float64).reshape(N_LANDMARKS_MANO, 3)
    plano = pts.reshape(-1)
    puntas = pts[list(_PUNTAS)]
    muneca = pts[_INDICE_MUNECA]
    dist_muneca = np.linalg.norm(puntas - muneca, axis=1)
    pares: list[float] = []
    for i in range(len(_PUNTAS)):
        for j in range(i + 1, len(_PUNTAS)):
            pares.append(float(np.linalg.norm(puntas[i] - puntas[j])))
    return np.concatenate([plano, dist_muneca, np.asarray(pares, dtype=np.float64)])


def extraer_vector(puntos: Sequence[object] | np.ndarray) -> np.ndarray:
    """Atajo: landmarks crudos → vector de características."""
    return vector_caracteristicas(normalizar_landmarks(puntos))


def origen_y_escala_muneca(puntos: Sequence[object] | np.ndarray) -> tuple[np.ndarray, float]:
    """Muñeca (x, y) y tamaño de palma en coords de imagen, para alinear trayectorias."""
    coords = (
        np.asarray(puntos, dtype=np.float64)
        if isinstance(puntos, np.ndarray)
        else matriz_desde_puntos(puntos)
    )
    origen = coords[_INDICE_MUNECA, :2].copy()
    palma = coords[_INDICE_MCP_MEDIO, :2] - origen
    escala = float(np.linalg.norm(palma))
    if escala < 1e-6:
        normas = np.linalg.norm(coords[:, :2] - origen, axis=1)
        escala = float(np.max(normas))
    if escala < 1e-6:
        escala = 1.0
    return origen, escala


def vector_dinamico(
    puntos: Sequence[object] | np.ndarray,
    origen_muneca: np.ndarray,
    escala: float,
) -> np.ndarray:
    """Vector de un fotograma dinámico: forma 2a (78) + muñeca relativa (2) = 80.

    La normalización de forma quita la traslación; sin el desplazamiento de la
    muñeca, J/Ñ/Z se parecerían a una pose quieta. La trayectoria se expresa
    respecto al primer fotograma del gesto.
    """
    forma = extraer_vector(puntos)
    coords = (
        np.asarray(puntos, dtype=np.float64)
        if isinstance(puntos, np.ndarray)
        else matriz_desde_puntos(puntos)
    )
    denom = float(escala) if float(escala) > 1e-6 else 1.0
    rel = (coords[_INDICE_MUNECA, :2] - np.asarray(origen_muneca, dtype=np.float64).reshape(-1)[:2]) / denom
    return np.concatenate([forma, rel])


def distancia_euclidiana(a: np.ndarray, b: np.ndarray) -> float:
    """Distancia RMS (euclidiana / sqrt(D)) para que no crezca con la dimensión."""
    va = np.asarray(a, dtype=np.float64).reshape(-1)
    vb = np.asarray(b, dtype=np.float64).reshape(-1)
    if va.shape != vb.shape:
        raise ErrorCaracteristicas("Los vectores a comparar tienen distinta dimensión.")
    diff = va - vb
    return float(np.sqrt(np.mean(diff * diff)))


def distancia_coseno(a: np.ndarray, b: np.ndarray) -> float:
    """1 − coseno; 0 si son paralelos, 2 si son opuestos."""
    va = np.asarray(a, dtype=np.float64).reshape(-1)
    vb = np.asarray(b, dtype=np.float64).reshape(-1)
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na < 1e-9 or nb < 1e-9:
        return 1.0
    coseno = float(np.dot(va, vb) / (na * nb))
    coseno = max(-1.0, min(1.0, coseno))
    return 1.0 - coseno


def distancia(
    a: np.ndarray,
    b: np.ndarray,
    metrica: str = "euclidiana",
) -> float:
    if metrica == "coseno":
        return distancia_coseno(a, b)
    if metrica == "euclidiana":
        return distancia_euclidiana(a, b)
    raise ErrorCaracteristicas(f"Métrica desconocida: {metrica}")


def confianza_desde_distancia(
    dist: float,
    metrica: str = "euclidiana",
    saturacion: float = SATURACION_DISTANCIA,
) -> float:
    """Convierte distancia en confianza 0–1 (1 = idéntico)."""
    if metrica == "coseno":
        # distancia_coseno está en [0, 2]; 0 → confianza 1.
        return float(max(0.0, min(1.0, 1.0 - dist)))
    if saturacion <= 1e-9:
        return 0.0
    return float(max(0.0, min(1.0, 1.0 - dist / saturacion)))
