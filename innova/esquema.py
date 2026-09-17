"""Esquema versionado de muestras LSM (JSON) y helpers de validación.

Una *muestra* es o bien un fotograma estático (una seña de una sola pose) o
una secuencia dinámica (letras con movimiento, fase 2b). El esquema ya reserva
campos `pose` y `rostro` para el vocabulario completo; en la fase 2a van en
null porque solo corre MediaPipe Hands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from innova.caracteristicas import extraer_vector, normalizar_landmarks
from innova.config import FPS_OBJETIVO, VERSION_ESQUEMA
from innova.detector import ManoDetectada

VERSIONES_COMPATIBLES = frozenset({"1.0"})
TIPOS_MUESTRA = frozenset({"estatico", "dinamico"})
LATERALIDADES = frozenset({"izquierda", "derecha", "desconocida"})


class ErrorEsquema(ValueError):
    """JSON de muestra inválido o incompleto."""


@dataclass
class ManoEsquema:
    """21 landmarks de una mano, crudos y normalizados, más el vector derivado."""

    lateralidad: str
    landmarks: list[list[float]]
    landmarks_normalizados: list[list[float]]
    caracteristicas: list[float]

    def a_dict(self) -> dict[str, Any]:
        return {
            "lateralidad": self.lateralidad,
            "landmarks": _redondear_matriz(self.landmarks),
            "landmarks_normalizados": _redondear_matriz(self.landmarks_normalizados),
            "caracteristicas": [round(float(x), 6) for x in self.caracteristicas],
        }


@dataclass
class FotogramaSecuencia:
    """Un paso de una seña dinámica (fase 2b / DTW)."""

    t: float
    mano: ManoEsquema | None = None
    pose: dict[str, Any] | None = None
    rostro: dict[str, Any] | None = None

    def a_dict(self) -> dict[str, Any]:
        return {
            "t": round(float(self.t), 4),
            "mano": None if self.mano is None else self.mano.a_dict(),
            "pose": self.pose,
            "rostro": self.rostro,
        }


@dataclass
class SecuenciaEsquema:
    fps: float
    fotogramas: list[FotogramaSecuencia] = field(default_factory=list)

    def a_dict(self) -> dict[str, Any]:
        return {
            "fps": float(self.fps),
            "fotogramas": [f.a_dict() for f in self.fotogramas],
        }


@dataclass
class MetadatosMuestra:
    marca_tiempo: str
    fps: float | None = None
    notas: str = ""
    consentimiento: bool = False
    origen: str = ""

    def a_dict(self) -> dict[str, Any]:
        return {
            "marca_tiempo": self.marca_tiempo,
            "fps": self.fps,
            "notas": self.notas,
            "consentimiento": bool(self.consentimiento),
            "origen": self.origen,
        }


@dataclass
class MuestraLSM:
    """Unidad que se guarda en `datos/plantillas/` (estática o dinámica)."""

    etiqueta: str
    tipo: str
    mano: ManoEsquema | None
    pose: dict[str, Any] | None
    rostro: dict[str, Any] | None
    secuencia: SecuenciaEsquema | None
    metadatos: MetadatosMuestra
    version: str = VERSION_ESQUEMA

    def a_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "etiqueta": self.etiqueta,
            "tipo": self.tipo,
            "mano": None if self.mano is None else self.mano.a_dict(),
            "pose": self.pose,
            "rostro": self.rostro,
            "secuencia": None if self.secuencia is None else self.secuencia.a_dict(),
            "metadatos": self.metadatos.a_dict(),
        }


def mano_desde_deteccion(mano: ManoDetectada) -> ManoEsquema:
    """Arma el bloque `mano` del esquema a partir de una detección en vivo."""
    crudos = [[float(p.x), float(p.y), float(p.z)] for p in mano.puntos[:21]]
    if len(crudos) < 21:
        raise ErrorEsquema("La mano detectada no tiene 21 landmarks.")
    normalizados = normalizar_landmarks(crudos).tolist()
    vector = extraer_vector(crudos).tolist()
    lateralidad = mano.lateralidad if mano.lateralidad in LATERALIDADES else "desconocida"
    return ManoEsquema(
        lateralidad=lateralidad,
        landmarks=crudos,
        landmarks_normalizados=normalizados,
        caracteristicas=[float(x) for x in vector],
    )


def muestra_estatica_desde_mano(
    mano: ManoDetectada,
    etiqueta: str,
    *,
    consentimiento: bool = True,
    notas: str = "",
    origen: str = "camara",
    fps: float = FPS_OBJETIVO,
) -> MuestraLSM:
    """Crea una muestra `tipo=estatico` lista para serializar (pose/rostro = null)."""
    etiqueta_n = normalizar_etiqueta(etiqueta)
    return MuestraLSM(
        version=VERSION_ESQUEMA,
        etiqueta=etiqueta_n,
        tipo="estatico",
        mano=mano_desde_deteccion(mano),
        pose=None,
        rostro=None,
        secuencia=None,
        metadatos=MetadatosMuestra(
            marca_tiempo=_ahora_iso(),
            fps=float(fps),
            notas=notas,
            consentimiento=bool(consentimiento),
            origen=origen,
        ),
    )


def muestra_dinamica_desde_fotogramas(
    etiqueta: str,
    fotogramas: Iterable[FotogramaSecuencia],
    *,
    fps: float = FPS_OBJETIVO,
    consentimiento: bool = True,
    notas: str = "",
    origen: str = "camara",
) -> MuestraLSM:
    """Crea una muestra `tipo=dinamico` (la secuencia se usará en la fase 2b)."""
    frames = list(fotogramas)
    if not frames:
        raise ErrorEsquema("Una muestra dinámica necesita al menos un fotograma.")
    primera_mano = next((f.mano for f in frames if f.mano is not None), None)
    return MuestraLSM(
        version=VERSION_ESQUEMA,
        etiqueta=normalizar_etiqueta(etiqueta),
        tipo="dinamico",
        mano=primera_mano,
        pose=None,
        rostro=None,
        secuencia=SecuenciaEsquema(fps=float(fps), fotogramas=frames),
        metadatos=MetadatosMuestra(
            marca_tiempo=_ahora_iso(),
            fps=float(fps),
            notas=notas,
            consentimiento=bool(consentimiento),
            origen=origen,
        ),
    )


def muestra_desde_dict(datos: dict[str, Any]) -> MuestraLSM:
    """Deserializa y valida. Completa normalización/características si faltan."""
    errores = validar_muestra(datos)
    if errores:
        raise ErrorEsquema("Muestra inválida: " + " ".join(errores))
    tipo = str(datos["tipo"])
    mano = _mano_desde_dict(datos.get("mano"))
    secuencia = _secuencia_desde_dict(datos.get("secuencia"))
    if tipo == "estatico" and mano is not None:
        mano = _completar_mano(mano)
    if secuencia is not None:
        secuencia = SecuenciaEsquema(
            fps=secuencia.fps,
            fotogramas=[
                FotogramaSecuencia(
                    t=f.t,
                    mano=_completar_mano(f.mano) if f.mano is not None else None,
                    pose=f.pose,
                    rostro=f.rostro,
                )
                for f in secuencia.fotogramas
            ],
        )
    meta_bruta = datos.get("metadatos") or {}
    return MuestraLSM(
        version=str(datos.get("version", VERSION_ESQUEMA)),
        etiqueta=str(datos["etiqueta"]),
        tipo=tipo,
        mano=mano,
        pose=_opcional_cuerpo(datos.get("pose")),
        rostro=_opcional_cuerpo(datos.get("rostro")),
        secuencia=secuencia,
        metadatos=MetadatosMuestra(
            marca_tiempo=str(meta_bruta.get("marca_tiempo") or _ahora_iso()),
            fps=_float_o_none(meta_bruta.get("fps")),
            notas=str(meta_bruta.get("notas") or ""),
            consentimiento=bool(meta_bruta.get("consentimiento", False)),
            origen=str(meta_bruta.get("origen") or ""),
        ),
    )


def validar_muestra(datos: Any) -> list[str]:
    """Devuelve una lista de errores en español; vacía si el dict es válido."""
    errores: list[str] = []
    if not isinstance(datos, dict):
        return ["La muestra debe ser un objeto JSON."]

    version = datos.get("version")
    if version not in VERSIONES_COMPATIBLES:
        errores.append(
            f"version debe ser una de {sorted(VERSIONES_COMPATIBLES)} (se recibió {version!r})."
        )

    etiqueta = datos.get("etiqueta")
    if not isinstance(etiqueta, str) or not etiqueta.strip():
        errores.append("etiqueta es obligatoria y no puede estar vacía.")

    tipo = datos.get("tipo")
    if tipo not in TIPOS_MUESTRA:
        errores.append("tipo debe ser 'estatico' o 'dinamico'.")

    errores.extend(_errores_mano(datos.get("mano"), obligatorio=(tipo == "estatico")))
    errores.extend(_errores_cuerpo_opcional(datos.get("pose"), "pose"))
    errores.extend(_errores_cuerpo_opcional(datos.get("rostro"), "rostro"))
    errores.extend(_errores_secuencia(datos.get("secuencia"), obligatorio=(tipo == "dinamico")))
    errores.extend(_errores_metadatos(datos.get("metadatos")))
    return errores


def normalizar_etiqueta(texto: str) -> str:
    limpio = " ".join((texto or "").strip().split())
    if not limpio:
        raise ErrorEsquema("La etiqueta no puede estar vacía.")
    return limpio.upper()


def _completar_mano(mano: ManoEsquema) -> ManoEsquema:
    if len(mano.landmarks_normalizados) != 21:
        mano.landmarks_normalizados = normalizar_landmarks(mano.landmarks).tolist()
    if len(mano.caracteristicas) < 63:
        mano.caracteristicas = extraer_vector(mano.landmarks).tolist()
    return mano


def _mano_desde_dict(datos: Any) -> ManoEsquema | None:
    if datos is None:
        return None
    return ManoEsquema(
        lateralidad=str(datos.get("lateralidad") or "desconocida"),
        landmarks=_lista_puntos(datos.get("landmarks") or []),
        landmarks_normalizados=_lista_puntos(datos.get("landmarks_normalizados") or []),
        caracteristicas=[float(x) for x in (datos.get("caracteristicas") or [])],
    )


def _secuencia_desde_dict(datos: Any) -> SecuenciaEsquema | None:
    if datos is None:
        return None
    frames = []
    for item in datos.get("fotogramas") or []:
        frames.append(
            FotogramaSecuencia(
                t=float(item.get("t", 0.0)),
                mano=_mano_desde_dict(item.get("mano")),
                pose=_opcional_cuerpo(item.get("pose")),
                rostro=_opcional_cuerpo(item.get("rostro")),
            )
        )
    return SecuenciaEsquema(fps=float(datos.get("fps") or FPS_OBJETIVO), fotogramas=frames)


def _errores_mano(valor: Any, *, obligatorio: bool) -> list[str]:
    if valor is None:
        return ["mano es obligatorio en una muestra estática."] if obligatorio else []
    if not isinstance(valor, dict):
        return ["mano debe ser un objeto o null."]
    errores: list[str] = []
    lat = valor.get("lateralidad", "desconocida")
    if lat not in LATERALIDADES:
        errores.append("mano.lateralidad debe ser izquierda, derecha o desconocida.")
    errores.extend(_errores_lista_21(valor.get("landmarks"), "mano.landmarks"))
    if valor.get("landmarks_normalizados") is not None:
        if valor.get("landmarks_normalizados") != []:
            errores.extend(
                _errores_lista_21(
                    valor.get("landmarks_normalizados"),
                    "mano.landmarks_normalizados",
                    permitir_vacio=True,
                )
            )
    if valor.get("caracteristicas") is not None and not isinstance(
        valor.get("caracteristicas"), list
    ):
        errores.append("mano.caracteristicas debe ser una lista de números.")
    return errores


def _errores_lista_21(
    valor: Any, campo: str, *, permitir_vacio: bool = False
) -> list[str]:
    if valor is None or (permitir_vacio and valor == []):
        return [] if permitir_vacio else [f"{campo} debe tener 21 puntos [x, y, z]."]
    if not isinstance(valor, list):
        return [f"{campo} debe ser una lista."]
    if len(valor) != 21:
        return [f"{campo} debe tener 21 puntos (tiene {len(valor)})."]
    errores: list[str] = []
    for i, p in enumerate(valor):
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            errores.append(f"{campo}[{i}] debe ser [x, y, z].")
            continue
        try:
            float(p[0])
            float(p[1])
            if len(p) > 2:
                float(p[2])
        except (TypeError, ValueError):
            errores.append(f"{campo}[{i}] contiene valores no numéricos.")
    return errores


def _errores_secuencia(valor: Any, *, obligatorio: bool) -> list[str]:
    if valor is None:
        return ["secuencia es obligatoria en una muestra dinámica."] if obligatorio else []
    if not isinstance(valor, dict):
        return ["secuencia debe ser un objeto o null."]
    errores: list[str] = []
    fps = valor.get("fps")
    if fps is None or not _es_numero(fps) or float(fps) <= 0:
        errores.append("secuencia.fps debe ser un número positivo.")
    frames = valor.get("fotogramas")
    if not isinstance(frames, list) or not frames:
        errores.append("secuencia.fotogramas debe ser una lista con al menos un fotograma.")
        return errores
    for i, item in enumerate(frames):
        if not isinstance(item, dict):
            errores.append(f"secuencia.fotogramas[{i}] debe ser un objeto.")
            continue
        if not _es_numero(item.get("t", 0)):
            errores.append(f"secuencia.fotogramas[{i}].t debe ser numérico.")
        errores.extend(_errores_mano(item.get("mano"), obligatorio=False))
        errores.extend(_errores_cuerpo_opcional(item.get("pose"), f"secuencia.fotogramas[{i}].pose"))
        errores.extend(
            _errores_cuerpo_opcional(item.get("rostro"), f"secuencia.fotogramas[{i}].rostro")
        )
    return errores


def _errores_cuerpo_opcional(valor: Any, campo: str) -> list[str]:
    """pose / rostro: null (fase 2a) o un objeto con lista `landmarks` (futuro)."""
    if valor is None:
        return []
    if not isinstance(valor, dict):
        return [f"{campo} debe ser null o un objeto con 'landmarks'."]
    if "landmarks" in valor and not isinstance(valor["landmarks"], list):
        return [f"{campo}.landmarks debe ser una lista."]
    return []


def _errores_metadatos(valor: Any) -> list[str]:
    if valor is None:
        return ["metadatos es obligatorio."]
    if not isinstance(valor, dict):
        return ["metadatos debe ser un objeto."]
    errores: list[str] = []
    if not valor.get("marca_tiempo"):
        errores.append("metadatos.marca_tiempo es obligatorio.")
    if "consentimiento" in valor and not isinstance(valor["consentimiento"], bool):
        errores.append("metadatos.consentimiento debe ser booleano.")
    fps = valor.get("fps")
    if fps is not None and not _es_numero(fps):
        errores.append("metadatos.fps debe ser numérico o null.")
    return errores


def _opcional_cuerpo(valor: Any) -> dict[str, Any] | None:
    if valor is None:
        return None
    if not isinstance(valor, dict):
        raise ErrorEsquema("pose/rostro debe ser un objeto o null.")
    return valor


def _lista_puntos(valor: Any) -> list[list[float]]:
    salida: list[list[float]] = []
    for p in valor:
        x = float(p[0])
        y = float(p[1])
        z = float(p[2]) if len(p) > 2 else 0.0
        salida.append([x, y, z])
    return salida


def _float_o_none(valor: Any) -> float | None:
    if valor is None or valor == "":
        return None
    return float(valor)


def _es_numero(valor: Any) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _redondear_matriz(puntos: list[list[float]]) -> list[list[float]]:
    return [[round(float(c), 6) for c in p] for p in puntos]
