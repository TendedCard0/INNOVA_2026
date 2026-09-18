"""Une cámara, detector, reconocedor y overlay en un solo paso por fotograma."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from innova.camara import Camara, FuenteDemo, FuenteVideo
from innova.config import (
    ETIQUETA_DETECTANDO,
    ETIQUETA_SIN_DETECCION,
    FPS_OBJETIVO,
    INTERVALO_TRANSCRIPCION_S,
    MAX_LINEAS_TRANSCRIPCION,
)
from innova.detector import DetectorManos, DetectorMediaPipe, DetectorSimulado, ManoDetectada
from innova.esquema import muestra_estatica_desde_mano
from innova.overlay import dibujar_manos, poner_banner
from innova.reconocimiento import (
    ReconocedorEstatico,
    ReconocedorLSM,
    ResultadoReconocimiento,
    crear_reconocedor,
)


@dataclass
class FotogramaProcesado:
    imagen: np.ndarray
    manos: list[ManoDetectada]
    resultado: ResultadoReconocimiento
    transcripcion: list[str] = field(default_factory=list)
    fuente: str = ""
    n_plantillas: int = 0


class BitacoraTranscripcion:
    """Historial corto de letras *comprometidas* (no marcadores de espera)."""

    def __init__(
        self,
        max_lineas: int = MAX_LINEAS_TRANSCRIPCION,
        intervalo_s: float = INTERVALO_TRANSCRIPCION_S,
    ) -> None:
        self._max = max_lineas
        self._intervalo = intervalo_s
        self._lineas: list[str] = []
        self._ultima = ""
        self._t_ultima = 0.0

    def registrar(self, etiqueta: str) -> None:
        if not etiqueta or etiqueta in {ETIQUETA_SIN_DETECCION, ETIQUETA_DETECTANDO}:
            return
        ahora = time.monotonic()
        if etiqueta == self._ultima and (ahora - self._t_ultima) < self._intervalo:
            return
        marca = time.strftime("%H:%M:%S")
        self._lineas.append(f"{marca}   {etiqueta}")
        self._lineas = self._lineas[-self._max :]
        self._ultima = etiqueta
        self._t_ultima = ahora

    def lineas(self) -> list[str]:
        return list(self._lineas)


class PipelineVision:
    """Procesa un fotograma: detectar → reconocer → dibujar."""

    def __init__(self, fuente: FuenteVideo, detector: DetectorManos, reconocedor: ReconocedorLSM) -> None:
        self.fuente = fuente
        self.detector = detector
        self.reconocedor = reconocedor
        self.bitacora = BitacoraTranscripcion()
        self._espejo = not isinstance(fuente, FuenteDemo)
        self._ultimo: FotogramaProcesado | None = None

    @property
    def n_plantillas(self) -> int:
        return int(getattr(self.reconocedor, "n_plantillas", 0))

    def procesar(self) -> FotogramaProcesado | None:
        frame = self.fuente.leer()
        if frame is None:
            return None

        if self._espejo:
            frame = cv2.flip(frame, 1)

        manos = self.detector.detectar(frame)
        resultado = self.reconocedor.predecir(frame, manos)
        self.bitacora.registrar(resultado.etiqueta)
        imagen = dibujar_manos(frame, manos)
        descripcion = self.fuente.descripcion()
        if isinstance(self.fuente, FuenteDemo):
            imagen = poner_banner(
                imagen,
                "Modo demostración — landmarks de ejemplo (sin cámara)",
                (180, 196, 46),
            )
        procesado = FotogramaProcesado(
            imagen=imagen,
            manos=manos,
            resultado=resultado,
            transcripcion=self.bitacora.lineas(),
            fuente=descripcion,
            n_plantillas=self.n_plantillas,
        )
        self._ultimo = procesado
        return procesado

    def guardar_plantilla(self, etiqueta: str, *, notas: str = "", consentimiento: bool = True) -> Path:
        """Guarda la mano del último fotograma como plantilla estática."""
        if self._ultimo is None or not self._ultimo.manos:
            raise ValueError("No hay una mano detectada para guardar. Coloca la seña frente a la cámara.")
        origen = "demo" if isinstance(self.fuente, FuenteDemo) else "camara"
        muestra = muestra_estatica_desde_mano(
            self._ultimo.manos[0],
            etiqueta,
            consentimiento=consentimiento,
            notas=notas,
            origen=origen,
            fps=float(FPS_OBJETIVO),
        )
        reconocedor = self.reconocedor
        if isinstance(reconocedor, ReconocedorEstatico):
            return reconocedor.registrar_plantilla(muestra)
        raise ValueError("Este reconocedor no admite guardar plantillas.")

    def cerrar(self) -> None:
        self.detector.cerrar()
        self.fuente.liberar()


def crear_pipeline(
    *,
    modo_demo: bool,
    indice_camara: int = 0,
    ruta_plantillas: str | Path | None = None,
) -> PipelineVision:
    """Construye el pipeline (cámara real o demostración) con el reconocedor 2a."""
    reconocedor = crear_reconocedor(ruta_plantillas)
    if modo_demo:
        return PipelineVision(FuenteDemo(), DetectorSimulado(), reconocedor)
    fuente: FuenteVideo = Camara(indice_camara)
    return PipelineVision(fuente, DetectorMediaPipe(espejo=True), reconocedor)
