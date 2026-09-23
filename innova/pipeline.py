"""Une cámara, detector, reconocedor y overlay en un solo paso por fotograma."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from innova import tema
from innova.ajustes import Ajustes, cargar_ajustes
from innova.camara import Camara, FuenteDemo, FuenteVideo
from innova.config import (
    ETIQUETA_DETECTANDO,
    ETIQUETA_SIN_DETECCION,
    FPS_OBJETIVO,
    INTERVALO_TRANSCRIPCION_S,
    MAX_LINEAS_TRANSCRIPCION,
    MIN_FOTOGRAMAS_DINAMICO,
)
from innova.cuerpo import anotar_cuerpo
from innova.detector import DetectorManos, DetectorMediaPipe, DetectorSimulado, ManoDetectada
from innova.esquema import (
    CATEGORIA_LETRA,
    CATEGORIA_PALABRA,
    CATEGORIA_TODAS,
    FotogramaSecuencia,
    mano_desde_deteccion,
    muestra_dinamica_desde_fotogramas,
    muestra_estatica_desde_mano,
    normalizar_categoria,
)
from innova.overlay import dibujar_cuerpo, dibujar_manos, poner_banner
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
    n_estaticas: int = 0
    n_dinamicas: int = 0
    grabando: bool = False


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

    def vaciar(self) -> None:
        self._lineas.clear()
        self._ultima = ""
        self._t_ultima = 0.0


class PipelineVision:
    """Procesa un fotograma: detectar → reconocer → dibujar."""

    def __init__(self, fuente: FuenteVideo, detector: DetectorManos, reconocedor: ReconocedorLSM) -> None:
        self.fuente = fuente
        self.detector = detector
        self.reconocedor = reconocedor
        self.bitacora = BitacoraTranscripcion()
        self._espejo = not isinstance(fuente, FuenteDemo)
        self._ultimo: FotogramaProcesado | None = None
        self._grabacion: list[FotogramaSecuencia] | None = None
        self._t0_grabacion = 0.0
        self._frame_crudo: np.ndarray | None = None
        self._pose_vivo: dict | None = None
        self._rostro_vivo: dict | None = None
        self._cuerpo_anotado = False
        # Abecedario se queda en manos. Vocabulario (y la captura en Palabra) anota cuerpo.
        self.usar_cuerpo = bool(getattr(reconocedor, "categoria", "") == CATEGORIA_PALABRA)

    @property
    def n_plantillas(self) -> int:
        return int(getattr(self.reconocedor, "n_plantillas", 0))

    @property
    def n_estaticas(self) -> int:
        return int(getattr(self.reconocedor, "n_estaticas", 0))

    @property
    def n_dinamicas(self) -> int:
        return int(getattr(self.reconocedor, "n_dinamicas", 0))

    @property
    def grabando(self) -> bool:
        if self._grabacion is not None:
            return True
        return bool(getattr(self.reconocedor, "forzar_dinamico", False))

    @property
    def n_fotogramas_grabacion(self) -> int:
        return len(self._grabacion or [])

    def set_usar_cuerpo(self, activo: bool) -> None:
        """Activa pose y rostro (captura de palabras) o los deja apagados (letras)."""
        self.usar_cuerpo = bool(activo)

    def set_solo_estatico(self, activo: bool) -> None:
        """Mini juego: matching estático de letras, sin enrutado a DTW."""
        rec = self.reconocedor
        setter = getattr(rec, "set_solo_estatico", None)
        if callable(setter):
            setter(bool(activo))

    def reiniciar_estabilidad(self) -> None:
        """Reinicia el filtro para que la siguiente letra exija una pose nueva."""
        rec = self.reconocedor
        fn = getattr(rec, "reiniciar_filtro", None)
        if callable(fn):
            fn()

    def set_forzar_dinamico(self, activo: bool) -> None:
        rec = self.reconocedor
        setter = getattr(rec, "set_forzar_dinamico", None)
        if callable(setter):
            setter(activo)

    def iniciar_grabacion(self) -> None:
        self._grabacion = []
        self._t0_grabacion = time.monotonic()

    def detener_grabacion(self) -> list[FotogramaSecuencia]:
        frames = list(self._grabacion or [])
        self._grabacion = None
        return frames

    def procesar(self, *, reconocer: bool = True) -> FotogramaProcesado | None:
        frame = self.fuente.leer()
        if frame is None:
            return None

        if self._espejo:
            frame = cv2.flip(frame, 1)

        manos = self.detector.detectar(frame)
        pose: dict | None = None
        rostro: dict | None = None
        self._cuerpo_anotado = False
        if self.usar_cuerpo:
            pose, rostro = anotar_cuerpo(frame)
            self._cuerpo_anotado = True
        self._frame_crudo = frame
        self._pose_vivo = pose
        self._rostro_vivo = rostro
        if self._grabacion is not None:
            self._anotar_grabacion(manos, pose, rostro)

        if reconocer:
            resultado = self.reconocedor.predecir(frame, manos)
            self.bitacora.registrar(resultado.etiqueta)
        else:
            resultado = ResultadoReconocimiento(
                etiqueta="—" if not manos else "mano",
                confianza=1.0 if manos else 0.0,
                mensaje="Mano visible" if manos else "Sin manos en el encuadre",
                etiqueta_cruda="mano" if manos else "—",
                modo="grabando" if self._grabacion is not None else "estatico",
            )

        imagen = dibujar_manos(frame, manos)
        if self.usar_cuerpo:
            imagen = dibujar_cuerpo(imagen, pose, rostro)
        descripcion = self.fuente.descripcion()
        if isinstance(self.fuente, FuenteDemo):
            imagen = poner_banner(
                imagen,
                "Modo demostración — landmarks de ejemplo (sin cámara)",
                tema.BGR_LIMA,
            )
        if self.grabando:
            n = len(self._grabacion) if self._grabacion is not None else 0
            extra = f" · {n} fotogramas" if n else ""
            imagen = poner_banner(
                imagen,
                f"Grabando seña con movimiento…{extra}",
                tema.BGR_NARANJA,
            )
        procesado = FotogramaProcesado(
            imagen=imagen,
            manos=manos,
            resultado=resultado,
            transcripcion=self.bitacora.lineas(),
            fuente=descripcion,
            n_plantillas=self.n_plantillas,
            n_estaticas=self.n_estaticas,
            n_dinamicas=self.n_dinamicas,
            grabando=self.grabando,
        )
        self._ultimo = procesado
        return procesado

    def guardar_plantilla(
        self,
        etiqueta: str,
        *,
        notas: str = "",
        consentimiento: bool = True,
        tipo: str = "estatico",
        fotogramas: list[FotogramaSecuencia] | None = None,
        categoria: str = CATEGORIA_LETRA,
    ) -> Path:
        """Guarda la mano actual (estático) o una secuencia (dinámico)."""
        origen = "demo" if isinstance(self.fuente, FuenteDemo) else "camara"
        cat = normalizar_categoria(categoria)
        if tipo == "dinamico":
            frames = fotogramas if fotogramas is not None else list(self._grabacion or [])
            return self._guardar_dinamica(
                etiqueta,
                frames,
                notas=notas,
                consentimiento=consentimiento,
                origen=origen,
                categoria=cat,
            )
        if self._ultimo is None or not self._ultimo.manos:
            raise ValueError("No hay una mano detectada para guardar. Coloca la seña frente a la cámara.")
        pose, rostro = self._cuerpo_para_guardar(cat)
        muestra = muestra_estatica_desde_mano(
            self._ultimo.manos[0],
            etiqueta,
            consentimiento=consentimiento,
            notas=notas,
            origen=origen,
            fps=float(FPS_OBJETIVO),
            categoria=cat,
            pose=pose,
            rostro=rostro,
        )
        return self._registrar(muestra)

    def _guardar_dinamica(
        self,
        etiqueta: str,
        fotogramas: list[FotogramaSecuencia],
        *,
        notas: str,
        consentimiento: bool,
        origen: str,
        categoria: str = CATEGORIA_LETRA,
    ) -> Path:
        if categoria != CATEGORIA_PALABRA:
            fotogramas = [
                FotogramaSecuencia(t=f.t, mano=f.mano, pose=None, rostro=None) for f in fotogramas
            ]
        con_mano = [f for f in fotogramas if f.mano is not None]
        if len(con_mano) < MIN_FOTOGRAMAS_DINAMICO:
            raise ValueError(
                "La seña dinámica es demasiado corta "
                f"({len(con_mano)} fotogramas; mínimo {MIN_FOTOGRAMAS_DINAMICO}). "
                "Mantén pulsado mientras haces el movimiento."
            )
        pose, rostro = _ultimo_cuerpo(con_mano) if categoria == CATEGORIA_PALABRA else (None, None)
        muestra = muestra_dinamica_desde_fotogramas(
            etiqueta,
            con_mano,
            fps=float(FPS_OBJETIVO),
            consentimiento=consentimiento,
            notas=notas or "Captura dinámica (DTW)",
            origen=origen,
            categoria=categoria,
            pose=pose,
            rostro=rostro,
        )
        return self._registrar(muestra)

    def _cuerpo_para_guardar(self, categoria: str) -> tuple[dict | None, dict | None]:
        """Pose y rostro del último fotograma crudo, solo si la plantilla es una palabra."""
        if categoria != CATEGORIA_PALABRA:
            return None, None
        if self._pose_vivo is not None or self._rostro_vivo is not None:
            return self._pose_vivo, self._rostro_vivo
        if self._frame_crudo is not None and not self._cuerpo_anotado:
            return anotar_cuerpo(self._frame_crudo)
        return None, None

    def _registrar(self, muestra) -> Path:
        reconocedor = self.reconocedor
        if isinstance(reconocedor, ReconocedorEstatico):
            return reconocedor.registrar_plantilla(muestra)
        raise ValueError("Este reconocedor no admite guardar plantillas.")

    def _anotar_grabacion(
        self,
        manos: list[ManoDetectada],
        pose: dict | None,
        rostro: dict | None,
    ) -> None:
        assert self._grabacion is not None
        if not manos:
            return
        try:
            esquema = mano_desde_deteccion(manos[0])
        except Exception:  # noqa: BLE001
            return
        self._grabacion.append(
            FotogramaSecuencia(
                t=time.monotonic() - self._t0_grabacion,
                mano=esquema,
                pose=pose,
                rostro=rostro,
            )
        )

    def cerrar(self) -> None:
        self.detector.cerrar()
        self.fuente.liberar()


def _ultimo_cuerpo(
    fotogramas: list[FotogramaSecuencia],
) -> tuple[dict | None, dict | None]:
    for foto in reversed(fotogramas):
        if foto.pose is not None or foto.rostro is not None:
            return foto.pose, foto.rostro
    return None, None


def crear_pipeline(
    *,
    modo_demo: bool,
    indice_camara: int = 0,
    ruta_plantillas: str | Path | None = None,
    ajustes: Ajustes | None = None,
    categoria: str = CATEGORIA_TODAS,
) -> PipelineVision:
    """Construye el pipeline (cámara real o demostración) con el reconocedor."""
    aj = ajustes if ajustes is not None else cargar_ajustes()
    reconocedor = crear_reconocedor(ruta_plantillas, ajustes=aj, categoria=categoria)
    if modo_demo:
        return PipelineVision(FuenteDemo(), DetectorSimulado(), reconocedor)
    fuente: FuenteVideo = Camara(indice_camara)
    return PipelineVision(fuente, DetectorMediaPipe(espejo=True), reconocedor)
