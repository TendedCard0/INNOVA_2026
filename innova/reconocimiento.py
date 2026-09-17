"""Reconocedor LSM de la fase 2a: plantillas estáticas + filtro de estabilidad.

Contrato estable para la UI:

    crear_reconocedor() -> ReconocedorLSM
    reconocedor.predecir(frame, manos) -> ResultadoReconocimiento

La letra *comprometida* (estable) va en `etiqueta`; la estimación del
fotograma actual, en `etiqueta_cruda`. El reconocimiento dinámico (DTW)
queda como gancho `predecir_dinamico()` para la fase 2b.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np

from innova.caracteristicas import (
    ErrorCaracteristicas,
    confianza_desde_distancia,
    distancia,
    extraer_vector,
)
from innova.config import (
    ETIQUETA_DETECTANDO,
    ETIQUETA_SIN_DETECCION,
    METRICA_DISTANCIA,
    RUTA_PLANTILLAS,
)
from innova.detector import ManoDetectada
from innova.esquema import MuestraLSM, SecuenciaEsquema
from innova.estabilidad import EstadoEstable, FiltroEstabilidad
from innova.plantillas import (
    cargar_plantillas_con_errores,
    guardar_plantilla,
    plantillas_estaticas,
)


@dataclass
class ResultadoReconocimiento:
    """Salida estable que la UI puede mostrar sin conocer el modelo."""

    etiqueta: str
    confianza: float
    mensaje: str = ""
    etiqueta_cruda: str = ""
    confianza_cruda: float = 0.0
    distancia: float | None = None


class ReconocedorLSM(Protocol):
    """Contrato del clasificador de letras/palabras LSM.

    Fase 2a: plantillas estáticas (este módulo).
    Fase 2b: implementar `predecir_dinamico()` con DTW sobre `secuencia`.
    """

    def predecir(
        self,
        frame_bgr: np.ndarray,
        manos: list[ManoDetectada],
    ) -> ResultadoReconocimiento: ...

    def predecir_dinamico(
        self,
        secuencia: MuestraLSM | SecuenciaEsquema,
    ) -> ResultadoReconocimiento: ...


class ReconocedorEstatico:
    """Matching de vectores de landmarks contra plantillas JSON en disco."""

    def __init__(
        self,
        ruta_plantillas: str | Path | None = None,
        *,
        metrica: str = METRICA_DISTANCIA,
        filtro: FiltroEstabilidad | None = None,
    ) -> None:
        self.ruta_plantillas = Path(ruta_plantillas) if ruta_plantillas else RUTA_PLANTILLAS
        self.metrica = metrica
        self._filtro = filtro or FiltroEstabilidad()
        self._plantillas: list[MuestraLSM] = []
        self._vectores: list[tuple[str, np.ndarray]] = []
        self.avisos_carga: list[str] = []
        self.recargar_plantillas()

    @property
    def n_plantillas(self) -> int:
        return len(self._vectores)

    def recargar_plantillas(self) -> None:
        muestras, errores = cargar_plantillas_con_errores(self.ruta_plantillas)
        self.avisos_carga = errores
        self._plantillas = plantillas_estaticas(muestras)
        self._vectores = []
        for muestra in self._plantillas:
            assert muestra.mano is not None
            vector = np.asarray(muestra.mano.caracteristicas, dtype=np.float64)
            if vector.size < 63:
                continue
            self._vectores.append((muestra.etiqueta, vector))
        self._filtro.reiniciar()

    def registrar_plantilla(self, muestra: MuestraLSM) -> Path:
        """Serializa una muestra y recarga el banco de plantillas."""
        ruta = guardar_plantilla(muestra, self.ruta_plantillas)
        self.recargar_plantillas()
        return ruta

    def estimar_crudo(
        self, manos: Sequence[ManoDetectada]
    ) -> tuple[str | None, float, float]:
        """(etiqueta, distancia, confianza) del fotograma, sin filtro."""
        if not manos or not self._vectores:
            return None, float("inf"), 0.0
        mano = _mano_principal(manos)
        try:
            vector = extraer_vector(mano.puntos)
        except ErrorCaracteristicas:
            return None, float("inf"), 0.0

        mejor_etiq: str | None = None
        mejor_dist = float("inf")
        for etiqueta, plantilla in self._vectores:
            try:
                dist = distancia(vector, plantilla, self.metrica)
            except ErrorCaracteristicas:
                continue
            if dist < mejor_dist:
                mejor_dist = dist
                mejor_etiq = etiqueta
        if mejor_etiq is None:
            return None, float("inf"), 0.0
        conf = confianza_desde_distancia(mejor_dist, self.metrica)
        return mejor_etiq, mejor_dist, conf

    def predecir(
        self,
        frame_bgr: np.ndarray,
        manos: list[ManoDetectada],
    ) -> ResultadoReconocimiento:
        del frame_bgr  # El matching usa landmarks, no el recorte RGB.
        hay_mano = bool(manos)
        etiqueta_cruda, dist, conf_cruda = self.estimar_crudo(manos)

        if not self._vectores:
            self._filtro.reiniciar()
            if not hay_mano:
                return ResultadoReconocimiento(
                    etiqueta=ETIQUETA_SIN_DETECCION,
                    confianza=0.0,
                    mensaje="Sin manos en el encuadre · no hay plantillas",
                    etiqueta_cruda=ETIQUETA_SIN_DETECCION,
                    confianza_cruda=0.0,
                )
            return ResultadoReconocimiento(
                etiqueta=ETIQUETA_DETECTANDO,
                confianza=0.0,
                mensaje="No hay plantillas. Escribe una letra y pulsa «Guardar plantilla».",
                etiqueta_cruda=ETIQUETA_DETECTANDO,
                confianza_cruda=0.0,
            )

        estable = self._filtro.actualizar(
            etiqueta_cruda,
            conf_cruda,
            hay_mano=hay_mano,
        )
        return ResultadoReconocimiento(
            etiqueta=estable.etiqueta,
            confianza=estable.confianza,
            mensaje=self._mensaje(estable, hay_mano=hay_mano, dist=dist),
            etiqueta_cruda=_texto_crudo(etiqueta_cruda, hay_mano),
            confianza_cruda=conf_cruda,
            distancia=None if dist == float("inf") else dist,
        )

    def predecir_dinamico(
        self,
        secuencia: MuestraLSM | SecuenciaEsquema,
    ) -> ResultadoReconocimiento:
        """Gancho de la fase 2b: DTW sobre `secuencia` (aún no implementado)."""
        del secuencia
        return ResultadoReconocimiento(
            etiqueta=ETIQUETA_DETECTANDO,
            confianza=0.0,
            mensaje="Señas dinámicas (DTW) se implementan en la fase 2b.",
            etiqueta_cruda=ETIQUETA_DETECTANDO,
            confianza_cruda=0.0,
        )

    def _mensaje(self, estable: EstadoEstable, *, hay_mano: bool, dist: float) -> str:
        extra = estable.mensaje
        if not hay_mano:
            return extra or "Sin manos en el encuadre"
        n = self.n_plantillas
        sufijo = f"{n} plantilla" + ("s" if n != 1 else "")
        if dist != float("inf"):
            return f"{extra} · d={dist:.3f} · {sufijo}"
        return f"{extra} · {sufijo}"


def _texto_crudo(etiqueta_cruda: str | None, hay_mano: bool) -> str:
    if etiqueta_cruda:
        return etiqueta_cruda
    return ETIQUETA_SIN_DETECCION if not hay_mano else ETIQUETA_DETECTANDO


def _mano_principal(manos: Sequence[ManoDetectada]) -> ManoDetectada:
    """Una seña dactilológica suele ser una mano; tomamos la de mayor score."""
    return max(manos, key=lambda m: m.puntuacion)


def crear_reconocedor(
    ruta_plantillas: str | Path | None = None,
    *,
    metrica: str | None = None,
    filtro: FiltroEstabilidad | None = None,
) -> ReconocedorLSM:
    """Fábrica única que la UI usa para obtener el reconocedor."""
    if metrica is None:
        return ReconocedorEstatico(ruta_plantillas, filtro=filtro)
    return ReconocedorEstatico(ruta_plantillas, metrica=metrica, filtro=filtro)
