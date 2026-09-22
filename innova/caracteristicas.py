"""Normalización de landmarks y comparación de vectores (plantillas estáticas).

La mano sigue el vector de 78 (estático) o 80 (dinámico). En Vocabulario se
suman pose (33 puntos, torso como referencia) y un subconjunto del rostro
(ojos, cejas y boca). Si falta pose o rostro, esa parte se omite y el peso
se reparte entre las que sí están: la comparación no falla.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from innova.config import SATURACION_DISTANCIA
from innova.cuerpo import N_LANDMARKS_POSE, N_LANDMARKS_ROSTRO_MIN

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


# Pose: hombros y caderas (índices de MediaPipe Pose).
_POSE_HOMBRO_I = 11
_POSE_HOMBRO_D = 12
_POSE_CADERA_I = 23
_POSE_CADERA_D = 24

# Subconjunto de Face Mesh para expresión y orientación de la cabeza.
# Los índices existen tanto en la malla de 468 como en la de 478 (con iris).
INDICES_ROSTRO: tuple[int, ...] = (
    1,  # punta de la nariz (origen)
    10,  # frente
    152,  # mentón
    33,  # comisura externa del ojo izquierdo
    133,  # comisura interna del ojo izquierdo
    263,  # comisura externa del ojo derecho
    362,  # comisura interna del ojo derecho
    70,  # ceja izquierda
    300,  # ceja derecha
    61,  # comisura izquierda de la boca
    291,  # comisura derecha de la boca
    0,  # labio superior
    17,  # labio inferior
    13,  # labio superior interno
    14,  # labio inferior interno
)
_ROSTRO_NARIZ = 1
_ROSTRO_OJO_I = 33
_ROSTRO_OJO_D = 263

# Pesos del matching de palabras. La mano manda; pose y rostro afinan.
# Si una parte falta en la consulta o en la plantilla, se omite y se renormaliza.
PESO_MANO = 0.55
PESO_POSE = 0.30
PESO_ROSTRO = 0.15

DIM_MANO_DINAMICA = 80
DIM_POSE = N_LANDMARKS_POSE * 3
DIM_ROSTRO = len(INDICES_ROSTRO) * 3
DIM_FUSION_DINAMICA = DIM_MANO_DINAMICA + DIM_POSE + DIM_ROSTRO
_CORTE_POSE = DIM_MANO_DINAMICA
_CORTE_ROSTRO = DIM_MANO_DINAMICA + DIM_POSE


def matriz_puntos(puntos: Sequence[object], n: int | None = None) -> np.ndarray:
    """Lista de landmarks → matriz (N, 3). ``n`` exige al menos esa cantidad."""
    fuente = list(puntos)
    if n is not None and len(fuente) < n:
        raise ErrorCaracteristicas(f"Se necesitan {n} landmarks, hay {len(fuente)}.")
    if n is not None:
        fuente = fuente[:n]
    filas: list[tuple[float, float, float]] = []
    for p in fuente:
        if hasattr(p, "x") and hasattr(p, "y"):
            z = float(getattr(p, "z", 0.0) or 0.0)
            filas.append((float(p.x), float(p.y), z))
        else:
            seq = list(p)  # type: ignore[arg-type]
            if len(seq) < 2:
                raise ErrorCaracteristicas("Un landmark necesita al menos x e y.")
            z = float(seq[2]) if len(seq) > 2 else 0.0
            filas.append((float(seq[0]), float(seq[1]), z))
    if not filas:
        raise ErrorCaracteristicas("No hay landmarks para normalizar.")
    return np.asarray(filas, dtype=np.float64)


def _landmarks_de_bloque(valor: Any) -> Sequence[object]:
    if isinstance(valor, dict):
        lm = valor.get("landmarks")
        if not isinstance(lm, list) or not lm:
            raise ErrorCaracteristicas("El bloque no trae landmarks.")
        return lm
    return valor


def normalizar_pose(puntos: Sequence[object] | np.ndarray | dict[str, Any]) -> np.ndarray:
    """Torso al origen y ancho de hombros ≈ 1. Matriz (33, 3).

    El origen es el punto medio de las caderas; si degenera, el de los hombros.
    La escala es la distancia entre hombros. No se rota: la inclinación del
    torso distingue señas.
    """
    coords = matriz_puntos(_landmarks_de_bloque(puntos), N_LANDMARKS_POSE)
    hombros = coords[[_POSE_HOMBRO_I, _POSE_HOMBRO_D]]
    caderas = coords[[_POSE_CADERA_I, _POSE_CADERA_D]]
    origen = (caderas[0] + caderas[1]) / 2.0
    if not np.isfinite(origen).all():
        origen = (hombros[0] + hombros[1]) / 2.0
    centrado = coords - origen
    escala = float(np.linalg.norm(hombros[0] - hombros[1]))
    if escala < 1e-6:
        medio_hombros = (hombros[0] + hombros[1]) / 2.0
        escala = float(np.linalg.norm(medio_hombros - origen))
    if escala < 1e-6:
        escala = float(np.max(np.linalg.norm(centrado, axis=1)))
    if escala < 1e-6:
        raise ErrorCaracteristicas("La pose es degenerada (todos los puntos coinciden).")
    return centrado / escala


def vector_pose(puntos: Sequence[object] | np.ndarray | dict[str, Any]) -> np.ndarray:
    """99 números: 33 landmarks de pose ya normalizados."""
    return normalizar_pose(puntos).reshape(-1)


def normalizar_rostro(puntos: Sequence[object] | np.ndarray | dict[str, Any]) -> np.ndarray:
    """Cara relativa a la nariz, escala = distancia entre ojos. Matriz (15, 3)."""
    coords = matriz_puntos(_landmarks_de_bloque(puntos))
    necesario = max(INDICES_ROSTRO) + 1
    if coords.shape[0] < max(necesario, N_LANDMARKS_ROSTRO_MIN):
        raise ErrorCaracteristicas(
            f"El rostro necesita al menos {N_LANDMARKS_ROSTRO_MIN} puntos "
            f"(hay {coords.shape[0]})."
        )
    origen = coords[_ROSTRO_NARIZ]
    escala = float(np.linalg.norm(coords[_ROSTRO_OJO_I] - coords[_ROSTRO_OJO_D]))
    if escala < 1e-6:
        escala = float(np.max(np.linalg.norm(coords - origen, axis=1)))
    if escala < 1e-6:
        raise ErrorCaracteristicas("El rostro es degenerado.")
    sel = coords[list(INDICES_ROSTRO)] - origen
    return sel / escala


def vector_rostro(puntos: Sequence[object] | np.ndarray | dict[str, Any]) -> np.ndarray:
    """Vector compacto del rostro (ojos, cejas, boca), no los 478 puntos crudos."""
    return normalizar_rostro(puntos).reshape(-1)


def vector_pose_opcional(bloque: Any) -> np.ndarray | None:
    """``None`` si no hay pose usable. No lanza."""
    if bloque is None:
        return None
    try:
        return vector_pose(bloque)
    except (ErrorCaracteristicas, TypeError, ValueError, IndexError):
        return None


def vector_rostro_opcional(bloque: Any) -> np.ndarray | None:
    """``None`` si no hay rostro usable. No lanza."""
    if bloque is None:
        return None
    try:
        return vector_rostro(bloque)
    except (ErrorCaracteristicas, TypeError, ValueError, IndexError):
        return None


def vector_dinamico_fusion(
    puntos: Sequence[object] | np.ndarray,
    origen_muneca: np.ndarray,
    escala: float,
    pose: Any = None,
    rostro: Any = None,
) -> np.ndarray:
    """Fotograma de palabra: mano (80) + pose (99) + rostro compacto.

    Los bloques ausentes quedan en NaN para que la distancia los ignore.
    """
    salida = np.full(DIM_FUSION_DINAMICA, np.nan, dtype=np.float64)
    salida[:DIM_MANO_DINAMICA] = vector_dinamico(puntos, origen_muneca, escala)
    pose_v = vector_pose_opcional(pose)
    if pose_v is not None and pose_v.size == DIM_POSE:
        salida[_CORTE_POSE:_CORTE_ROSTRO] = pose_v
    rostro_v = vector_rostro_opcional(rostro)
    if rostro_v is not None and rostro_v.size == DIM_ROSTRO:
        salida[_CORTE_ROSTRO:] = rostro_v
    return salida


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


def distancia_partes(
    mano_a: np.ndarray | None,
    mano_b: np.ndarray | None,
    pose_a: np.ndarray | None,
    pose_b: np.ndarray | None,
    rostro_a: np.ndarray | None,
    rostro_b: np.ndarray | None,
    metrica: str = "euclidiana",
) -> float:
    """Distancia de una palabra estática: mano, y pose/rostro si ambos lados los traen.

    Los pesos se renormalizan sobre las partes presentes. Con solo manos, el
    resultado coincide con ``distancia`` de la mano.
    """
    partes: list[tuple[float, float]] = []
    if mano_a is not None and mano_b is not None:
        partes.append((distancia(mano_a, mano_b, metrica), PESO_MANO))
    if pose_a is not None and pose_b is not None and np.asarray(pose_a).shape == np.asarray(pose_b).shape:
        partes.append((distancia(pose_a, pose_b, metrica), PESO_POSE))
    if (
        rostro_a is not None
        and rostro_b is not None
        and np.asarray(rostro_a).shape == np.asarray(rostro_b).shape
    ):
        partes.append((distancia(rostro_a, rostro_b, metrica), PESO_ROSTRO))
    if not partes:
        raise ErrorCaracteristicas("No hay partes comparables (mano, pose o rostro).")
    peso = sum(w for _d, w in partes)
    return float(sum(d * w for d, w in partes) / peso)


def distancia_fusion_dinamica(
    a: np.ndarray,
    b: np.ndarray,
    metrica: str = "euclidiana",
) -> float:
    """Distancia entre fotogramas de palabra (vector fusionado con NaN = ausente).

    Un vector de solo mano (80) se compara como antes, sin pose ni rostro.
    """
    va = np.asarray(a, dtype=np.float64).reshape(-1)
    vb = np.asarray(b, dtype=np.float64).reshape(-1)
    if va.shape != vb.shape:
        raise ErrorCaracteristicas("Los vectores a comparar tienen distinta dimensión.")
    if va.size == DIM_MANO_DINAMICA and np.all(np.isfinite(va)) and np.all(np.isfinite(vb)):
        return distancia(va, vb, metrica)
    if va.size != DIM_FUSION_DINAMICA:
        raise ErrorCaracteristicas(
            f"Se esperaba un vector dinámico de {DIM_MANO_DINAMICA} o {DIM_FUSION_DINAMICA}."
        )
    cortes = (
        (0, DIM_MANO_DINAMICA, PESO_MANO),
        (_CORTE_POSE, _CORTE_ROSTRO, PESO_POSE),
        (_CORTE_ROSTRO, DIM_FUSION_DINAMICA, PESO_ROSTRO),
    )
    partes: list[tuple[float, float]] = []
    for ini, fin, peso in cortes:
        bloque_a = va[ini:fin]
        bloque_b = vb[ini:fin]
        if not (np.all(np.isfinite(bloque_a)) and np.all(np.isfinite(bloque_b))):
            continue
        partes.append((distancia(bloque_a, bloque_b, metrica), peso))
    if not partes:
        raise ErrorCaracteristicas("El fotograma fusionado no tiene bloques comparables.")
    total = sum(w for _d, w in partes)
    return float(sum(d * w for d, w in partes) / total)


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
