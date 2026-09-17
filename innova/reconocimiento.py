"""Interfaz de reconocimiento de LSM y marcador (stub) de la fase 1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from innova.config import ETIQUETA_DETECTANDO, ETIQUETA_SIN_DETECCION
from innova.detector import ManoDetectada


@dataclass
class ResultadoReconocimiento:
    """Salida estable que la UI puede mostrar sin conocer el modelo."""

    etiqueta: str
    confianza: float
    mensaje: str = ""


class ReconocedorLSM(Protocol):
    """Contrato para el clasificador de letras/palabras LSM.

    Fase 2: implementar este protocolo con un modelo entrenado (por ejemplo
    un RandomForest, una red pequeña o un modelo TFLite) y sustituir
    `crear_reconocedor()` — la UI no debería cambiar.
    """

    def predecir(
        self,
        frame_bgr: np.ndarray,
        manos: list[ManoDetectada],
    ) -> ResultadoReconocimiento: ...


class ReconocedorMarcador:
    """Marcador de posición: aún no hay modelo de LSM cargado."""

    def predecir(
        self,
        frame_bgr: np.ndarray,
        manos: list[ManoDetectada],
    ) -> ResultadoReconocimiento:
        del frame_bgr  # Se usará en la fase 2 (recortes, landmarks, etc.).
        if not manos:
            return ResultadoReconocimiento(
                etiqueta=ETIQUETA_SIN_DETECCION,
                confianza=0.0,
                mensaje="Sin manos en el encuadre",
            )

        n = len(manos)
        detalle = "1 mano detectada" if n == 1 else f"{n} manos detectadas"
        return ResultadoReconocimiento(
            etiqueta=ETIQUETA_DETECTANDO,
            confianza=0.0,
            mensaje=f"{detalle} · modelo LSM pendiente (fase 2)",
        )


def crear_reconocedor() -> ReconocedorLSM:
    """Fábrica única que la UI usa para obtener el reconocedor.

    En la fase 2, devolver aquí una instancia del modelo real, por ejemplo:
        return ReconocedorModeloLSM(ruta="modelos/lsm_letras.pkl")
    """
    return ReconocedorMarcador()
