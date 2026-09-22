"""Dynamic Time Warping sobre secuencias de vectores de la mano.

En palabras, cada fotograma puede sumar pose y rostro (vector fusionado).
Las letras siguen en 80 dimensiones (forma + muñeca relativa).
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from innova.caracteristicas import (
    DIM_FUSION_DINAMICA,
    ErrorCaracteristicas,
    distancia_fusion_dinamica,
    origen_y_escala_muneca,
    vector_dinamico,
    vector_dinamico_fusion,
)
from innova.caracteristicas import distancia as distancia_vector
from innova.config import SATURACION_DTW
from innova.esquema import MuestraLSM, SecuenciaEsquema


def dtw_distancia(
    secuencia_a: np.ndarray,
    secuencia_b: np.ndarray,
    metrica: str = "euclidiana",
) -> float:
    """DTW clásico; devuelve la distancia media a lo largo del camino.

    `secuencia_a` y `secuencia_b` son matrices (T, D). La suma del camino se
    divide entre n+m para comparar gestos de distinta duración.
    """
    a = np.asarray(secuencia_a, dtype=np.float64)
    b = np.asarray(secuencia_b, dtype=np.float64)
    if a.ndim != 2 or b.ndim != 2:
        raise ErrorCaracteristicas("Las secuencias DTW deben ser matrices (T, D).")
    if a.shape[0] == 0 or b.shape[0] == 0:
        raise ErrorCaracteristicas("Las secuencias DTW no pueden estar vacías.")
    if a.shape[1] != b.shape[1]:
        raise ErrorCaracteristicas("Las secuencias DTW tienen distinta dimensión.")

    costos = _matriz_costos(a, b, metrica)
    return dtw_desde_costos(costos)


def dtw_desde_costos(costos: np.ndarray) -> float:
    """DP sobre una matriz de costos (n, m) ya calculada."""
    c = np.asarray(costos, dtype=np.float64)
    n, m = c.shape
    inf = np.inf
    tabla = np.full((n + 1, m + 1), inf, dtype=np.float64)
    tabla[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            tabla[i, j] = c[i - 1, j - 1] + min(
                tabla[i - 1, j],
                tabla[i, j - 1],
                tabla[i - 1, j - 1],
            )
    camino = float(tabla[n, m])
    if not np.isfinite(camino):
        return inf
    return camino / float(n + m)


def mejor_plantilla_dtw(
    consulta: np.ndarray,
    plantillas: Sequence[tuple[str, np.ndarray]],
    metrica: str = "euclidiana",
) -> tuple[str | None, float]:
    """(etiqueta, distancia) de la plantilla dinámica más cercana."""
    mejor_etiq: str | None = None
    mejor_dist = float("inf")
    for etiqueta, matriz in plantillas:
        try:
            dist = dtw_distancia(consulta, matriz, metrica)
        except ErrorCaracteristicas:
            continue
        if dist < mejor_dist:
            mejor_dist = dist
            mejor_etiq = etiqueta
    return mejor_etiq, mejor_dist


def confianza_dtw(
    dist: float,
    metrica: str = "euclidiana",
    saturacion: float = SATURACION_DTW,
) -> float:
    from innova.caracteristicas import confianza_desde_distancia

    return confianza_desde_distancia(dist, metrica, saturacion=saturacion)


def vectores_desde_secuencia(
    secuencia: MuestraLSM | SecuenciaEsquema,
) -> np.ndarray:
    """Fotogramas con mano → matriz (T, 80) alineada al primer fotograma."""
    esquema = _secuencia_de(secuencia)
    manos = [f.mano for f in esquema.fotogramas if f.mano is not None]
    if not manos:
        raise ErrorCaracteristicas("La secuencia no tiene fotogramas con mano.")

    origen, escala = origen_y_escala_muneca(manos[0].landmarks)
    filas: list[np.ndarray] = []
    for mano in manos:
        try:
            filas.append(vector_dinamico(mano.landmarks, origen, escala))
        except ErrorCaracteristicas:
            continue
    if not filas:
        raise ErrorCaracteristicas("No se pudieron vectorizar los fotogramas.")
    return np.vstack(filas)


def vectores_desde_landmarks(
    lista_landmarks: Sequence[Sequence[object]],
) -> np.ndarray:
    """Atajo de pruebas: lista de 21 puntos crudos → matriz dinámica."""
    if not lista_landmarks:
        raise ErrorCaracteristicas("La secuencia de landmarks está vacía.")
    origen, escala = origen_y_escala_muneca(lista_landmarks[0])
    filas = [vector_dinamico(pts, origen, escala) for pts in lista_landmarks]
    return np.vstack(filas)


def vectores_fusionados_desde_secuencia(
    secuencia: MuestraLSM | SecuenciaEsquema,
) -> np.ndarray:
    """Fotogramas de palabra → matriz (T, mano+pose+rostro).

    Pose o rostro ausentes quedan en NaN y el DTW los ignora en ese par.
    """
    esquema = _secuencia_de(secuencia)
    utiles = [f for f in esquema.fotogramas if f.mano is not None]
    if not utiles:
        raise ErrorCaracteristicas("La secuencia no tiene fotogramas con mano.")

    origen, escala = origen_y_escala_muneca(utiles[0].mano.landmarks)  # type: ignore[union-attr]
    filas: list[np.ndarray] = []
    for foto in utiles:
        assert foto.mano is not None
        try:
            filas.append(
                vector_dinamico_fusion(
                    foto.mano.landmarks,
                    origen,
                    escala,
                    foto.pose,
                    foto.rostro,
                )
            )
        except ErrorCaracteristicas:
            continue
    if not filas:
        raise ErrorCaracteristicas("No se pudieron vectorizar los fotogramas.")
    return np.vstack(filas)


def _secuencia_de(secuencia: MuestraLSM | SecuenciaEsquema) -> SecuenciaEsquema:
    if isinstance(secuencia, MuestraLSM):
        if secuencia.secuencia is None:
            raise ErrorCaracteristicas("La muestra no tiene bloque secuencia.")
        return secuencia.secuencia
    return secuencia


def _matriz_costos(a: np.ndarray, b: np.ndarray, metrica: str) -> np.ndarray:
    n, m = a.shape[0], b.shape[0]
    fusion = a.shape[1] == DIM_FUSION_DINAMICA
    costos = np.empty((n, m), dtype=np.float64)
    for i in range(n):
        for j in range(m):
            if fusion:
                costos[i, j] = distancia_fusion_dinamica(a[i], b[j], metrica)
            else:
                costos[i, j] = distancia_vector(a[i], b[j], metrica)
    return costos


__all__ = [
    "confianza_dtw",
    "dtw_distancia",
    "dtw_desde_costos",
    "mejor_plantilla_dtw",
    "vectores_desde_landmarks",
    "vectores_desde_secuencia",
    "vectores_fusionados_desde_secuencia",
]
