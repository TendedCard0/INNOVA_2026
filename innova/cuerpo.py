"""Pose corporal y rostro para el vocabulario de Mamatlatolli.

Misma generación que las manos: MediaPipe 0.10.x, API clásica
``mp.solutions`` (no Tasks). Vocabulario usa:

- ``mp.solutions.pose.Pose`` — 33 landmarks (``model_complexity=1``, el modelo
  full que ya viene en el paquete; el lite y el heavy se descargan aparte);
- ``mp.solutions.face_mesh.FaceMesh(refine_landmarks=True)`` — 478 puntos
  (468 de la malla + iris). Si un modelo devolviera solo 468, también se acepta.

Abecedario no llama a estos modelos: el pipeline solo anota cuerpo cuando
el modo es Vocabulario o la captura está en categoría ``palabra``.

Si el import o la carga del grafo fallan, las extractoras devuelven ``None``
y el reconocimiento de palabras sigue con la mano.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

# Los ganchos están vivos. Si el modelo no carga, la extracción igual devuelve None.
POSE_ACTIVA = True
ROSTRO_ACTIVO = True

# Conteos de referencia (MediaPipe clásico / solutions).
N_LANDMARKS_POSE = 33
N_LANDMARKS_ROSTRO = 478
N_LANDMARKS_ROSTRO_MIN = 468

# Esqueleto de MediaPipe Pose (POSE_CONNECTIONS), para el overlay.
CONEXIONES_POSE: tuple[tuple[int, int], ...] = (
    (0, 1),
    (0, 4),
    (1, 2),
    (2, 3),
    (3, 7),
    (4, 5),
    (5, 6),
    (6, 8),
    (9, 10),
    (11, 12),
    (11, 13),
    (11, 23),
    (12, 14),
    (12, 24),
    (13, 15),
    (14, 16),
    (15, 17),
    (15, 19),
    (15, 21),
    (16, 18),
    (16, 20),
    (16, 22),
    (17, 19),
    (18, 20),
    (23, 24),
    (23, 25),
    (24, 26),
    (25, 27),
    (26, 28),
    (27, 29),
    (27, 31),
    (28, 30),
    (28, 32),
    (29, 31),
    (30, 32),
)

_CONFIANZA_DETECCION = 0.5
_CONFIANZA_SEGUIMIENTO = 0.5


class _EstadoModelos:
    """Carga perezosa: un fallo deja el gancho en None sin tumbar la app."""

    def __init__(self) -> None:
        self.intentado = False
        self.pose: Any = None
        self.rostro: Any = None
        self.error_pose: str | None = None
        self.error_rostro: str | None = None


class _CacheInferencia:
    def __init__(self) -> None:
        self.clave: tuple[Any, ...] | None = None
        self.valor: tuple[dict[str, Any] | None, dict[str, Any] | None] = (None, None)


_estado = _EstadoModelos()
_cache = _CacheInferencia()


def extraer_pose(frame_bgr: np.ndarray | None) -> dict[str, Any] | None:
    """Landmarks de MediaPipe Pose o ``None`` si no hay persona o el modelo falló."""
    if not POSE_ACTIVA or frame_bgr is None:
        return None
    pose, _rostro = _inferir(frame_bgr)
    return pose


def extraer_rostro(frame_bgr: np.ndarray | None) -> dict[str, Any] | None:
    """Landmarks de MediaPipe Face Mesh o ``None`` si no hay cara o el modelo falló."""
    if not ROSTRO_ACTIVO or frame_bgr is None:
        return None
    _pose, rostro = _inferir(frame_bgr)
    return rostro


def cuerpo_disponible() -> bool:
    """True si el gancho está activo y, tras intentar cargar, quedó al menos un modelo."""
    if not (POSE_ACTIVA or ROSTRO_ACTIVO):
        return False
    if not _estado.intentado:
        return True
    return _estado.pose is not None or _estado.rostro is not None


def anotar_cuerpo(
    frame_bgr: np.ndarray | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Par ``(pose, rostro)`` listo para el esquema. ``(None, None)`` si no hay señal."""
    if frame_bgr is None or not (POSE_ACTIVA or ROSTRO_ACTIVO):
        return None, None
    return _inferir(frame_bgr)


def bloque_desde_puntos(
    puntos: Sequence[Any] | None,
    *,
    visibilidad: Sequence[float] | None = None,
    minimo: int | None = None,
    maximo: int | None = None,
) -> dict[str, Any] | None:
    """Arma ``{"landmarks": [[x, y, z], ...]}`` o ``None`` si no alcanza el mínimo.

    ``maximo`` recorta (Pose trae 33). La visibilidad, si viene, se guarda
    aparte: el esquema solo exige la lista ``landmarks``.
    """
    if puntos is None:
        return None
    filas: list[list[float]] = []
    for p in puntos:
        if hasattr(p, "x") and hasattr(p, "y"):
            z = float(getattr(p, "z", 0.0) or 0.0)
            filas.append([round(float(p.x), 6), round(float(p.y), 6), round(z, 6)])
        else:
            seq = list(p)
            if len(seq) < 2:
                return None
            z = float(seq[2]) if len(seq) > 2 else 0.0
            try:
                filas.append([round(float(seq[0]), 6), round(float(seq[1]), 6), round(z, 6)])
            except (TypeError, ValueError):
                return None
    if maximo is not None:
        filas = filas[:maximo]
    if minimo is not None and len(filas) < minimo:
        return None
    if not filas:
        return None
    bloque: dict[str, Any] = {"landmarks": filas}
    if visibilidad is not None:
        vis = list(visibilidad)[: len(filas)]
        try:
            bloque["visibilidad"] = [round(float(v), 4) for v in vis]
        except (TypeError, ValueError):
            pass
    return bloque


def cerrar_modelos() -> None:
    """Suelta los grafos. El siguiente fotograma vuelve a intentar la carga."""
    for modelo in (_estado.pose, _estado.rostro):
        cerrar = getattr(modelo, "close", None)
        if callable(cerrar):
            try:
                cerrar()
            except Exception:  # noqa: BLE001 — cerrar no debe tumbar la salida
                pass
    _estado.intentado = False
    _estado.pose = None
    _estado.rostro = None
    _estado.error_pose = None
    _estado.error_rostro = None
    _cache.clave = None
    _cache.valor = (None, None)


def _inferir(
    frame_bgr: np.ndarray,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(frame_bgr, np.ndarray) or frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
        return None, None
    if frame_bgr.size == 0:
        return None, None
    _asegurar_modelos()
    clave = _clave_frame(frame_bgr)
    if clave == _cache.clave:
        return _cache.valor
    pose: dict[str, Any] | None = None
    rostro: dict[str, Any] | None = None
    try:
        import cv2
    except Exception:  # noqa: BLE001
        _cache.clave = clave
        _cache.valor = (None, None)
        return None, None
    try:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
    except Exception:  # noqa: BLE001
        _cache.clave = clave
        _cache.valor = (None, None)
        return None, None
    if POSE_ACTIVA and _estado.pose is not None:
        pose = _leer_pose(rgb)
    if ROSTRO_ACTIVO and _estado.rostro is not None:
        rostro = _leer_rostro(rgb)
    _cache.clave = clave
    _cache.valor = (pose, rostro)
    return pose, rostro


def _clave_frame(frame: np.ndarray) -> tuple[Any, ...]:
    plano = frame.reshape(-1)
    paso = max(1, plano.size // 64)
    firma = int(plano[::paso].sum())
    return (
        id(_estado.pose),
        id(_estado.rostro),
        int(frame.ctypes.data),
        frame.shape,
        firma,
    )


def _asegurar_modelos() -> None:
    if _estado.intentado:
        return
    _estado.intentado = True
    try:
        import mediapipe as mp
    except Exception as exc:  # noqa: BLE001 — sin MediaPipe el vocabulario sigue en manos
        _estado.error_pose = str(exc)
        _estado.error_rostro = str(exc)
        return
    if POSE_ACTIVA:
        try:
            _estado.pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=True,
                enable_segmentation=False,
                min_detection_confidence=_CONFIANZA_DETECCION,
                min_tracking_confidence=_CONFIANZA_SEGUIMIENTO,
            )
        except Exception as exc:  # noqa: BLE001
            _estado.pose = None
            _estado.error_pose = str(exc)
    if ROSTRO_ACTIVO:
        try:
            _estado.rostro = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=_CONFIANZA_DETECCION,
                min_tracking_confidence=_CONFIANZA_SEGUIMIENTO,
            )
        except Exception as exc:  # noqa: BLE001
            _estado.rostro = None
            _estado.error_rostro = str(exc)


def _leer_pose(rgb: np.ndarray) -> dict[str, Any] | None:
    try:
        resultado = _estado.pose.process(rgb)
    except Exception:  # noqa: BLE001
        return None
    crudo = getattr(resultado, "pose_landmarks", None)
    if crudo is None:
        return None
    puntos = list(crudo.landmark)
    visibilidad = [float(getattr(p, "visibility", 0.0) or 0.0) for p in puntos]
    return bloque_desde_puntos(
        puntos,
        visibilidad=visibilidad,
        minimo=N_LANDMARKS_POSE,
        maximo=N_LANDMARKS_POSE,
    )


def _leer_rostro(rgb: np.ndarray) -> dict[str, Any] | None:
    try:
        resultado = _estado.rostro.process(rgb)
    except Exception:  # noqa: BLE001
        return None
    caras = getattr(resultado, "multi_face_landmarks", None) or []
    if not caras:
        return None
    puntos = list(caras[0].landmark)
    if len(puntos) < N_LANDMARKS_ROSTRO_MIN:
        return None
    return bloque_desde_puntos(puntos, minimo=N_LANDMARKS_ROSTRO_MIN)
