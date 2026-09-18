"""Reconocedor LSM de Mamatlatolli: plantillas estáticas + DTW dinámico.

Contrato estable para la UI:

    crear_reconocedor() -> ReconocedorLSM
    reconocedor.predecir(frame, manos) -> ResultadoReconocimiento
    reconocedor.predecir_dinamico(secuencia) -> ResultadoReconocimiento

La letra *comprometida* (estable) va en `etiqueta`; la estimación del
fotograma actual, en `etiqueta_cruda`.

Enrutado por omisión: si la mano se mueve con claridad en ~0,4–0,8 s se
compara la trayectoria con plantillas `tipo: dinamico` (DTW). Si está
quieta, se usa el matching estático de la fase 2a. `set_forzar_dinamico`
(botón / Space) graba y reconoce al soltar.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np

from innova.ajustes import Ajustes
from innova.caracteristicas import (
    ErrorCaracteristicas,
    confianza_desde_distancia,
    distancia,
    extraer_vector,
)
from innova.config import (
    COOLDOWN_DINAMICO_S,
    ETIQUETA_DETECTANDO,
    ETIQUETA_SIN_DETECCION,
    FOTOGRAMAS_REPOSO_DINAMICO,
    FPS_OBJETIVO,
    MAX_DURACION_DINAMICA_S,
    METRICA_DISTANCIA,
    MIN_FOTOGRAMAS_DINAMICO,
    RUTA_PLANTILLAS,
    SATURACION_DTW,
)
from innova.detector import ManoDetectada
from innova.dtw import confianza_dtw, mejor_plantilla_dtw, vectores_desde_secuencia
from innova.esquema import (
    FotogramaSecuencia,
    ManoEsquema,
    MuestraLSM,
    SecuenciaEsquema,
    mano_desde_deteccion,
)
from innova.estabilidad import EstadoEstable, FiltroEstabilidad
from innova.movimiento import DetectorMovimiento, EstadoMovimiento
from innova.plantillas import (
    cargar_plantillas_con_errores,
    guardar_plantilla,
    plantillas_dinamicas,
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
    modo: str = "estatico"  # estatico | dinamico | grabando
    en_movimiento: bool = False


class ReconocedorLSM(Protocol):
    """Contrato del clasificador de letras/palabras LSM."""

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
    """Matching estático (fase 2a) + DTW sobre secuencias (fase 2b)."""

    def __init__(
        self,
        ruta_plantillas: str | Path | None = None,
        *,
        metrica: str = METRICA_DISTANCIA,
        filtro: FiltroEstabilidad | None = None,
        ajustes: Ajustes | None = None,
        detector_movimiento: DetectorMovimiento | None = None,
    ) -> None:
        self.ruta_plantillas = Path(ruta_plantillas) if ruta_plantillas else RUTA_PLANTILLAS
        self.ajustes = (ajustes or Ajustes()).normalizado()
        self.metrica = metrica or self.ajustes.metrica
        self._filtro = filtro or FiltroEstabilidad(
            umbral_confianza=self.ajustes.umbral_confianza,
            umbral_histeresis=self.ajustes.umbral_histeresis,
            consecutivos=self.ajustes.fotogramas_consecutivos,
            votos_m=self.ajustes.votos_m,
            ventana_k=self.ajustes.ventana_k,
        )
        self._movimiento = detector_movimiento or DetectorMovimiento(
            ventana_s=self.ajustes.ventana_movimiento_s,
            umbral=self.ajustes.umbral_movimiento,
            sensibilidad=self.ajustes.sensibilidad_movimiento,
        )
        self._plantillas: list[MuestraLSM] = []
        self._vectores: list[tuple[str, np.ndarray]] = []
        self._secuencias: list[tuple[str, np.ndarray]] = []
        self.avisos_carga: list[str] = []

        self.forzar_dinamico = False
        self._buffer_forzado: list[FotogramaSecuencia] = []
        self._t0_forzado = 0.0
        self._pendiente_forzado = False

        self._historial_vivo: deque[tuple[float, ManoEsquema | None]] = deque(maxlen=36)
        self._gesto_auto: list[FotogramaSecuencia] | None = None
        self._t0_gesto = 0.0
        self._quietos = 0
        self._cooldown_hasta = 0.0
        self._ultimo_dinamico: ResultadoReconocimiento | None = None

        self.recargar_plantillas()

    @property
    def n_plantillas(self) -> int:
        return self.n_estaticas + self.n_dinamicas

    @property
    def n_estaticas(self) -> int:
        return len(self._vectores)

    @property
    def n_dinamicas(self) -> int:
        return len(self._secuencias)

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

        self._secuencias = []
        for muestra in plantillas_dinamicas(muestras):
            try:
                matriz = vectores_desde_secuencia(muestra)
            except ErrorCaracteristicas:
                continue
            if matriz.shape[0] < MIN_FOTOGRAMAS_DINAMICO:
                continue
            self._secuencias.append((muestra.etiqueta, matriz))
        self._filtro.reiniciar()
        self._movimiento.reiniciar()
        self._historial_vivo.clear()
        self._gesto_auto = None

    def registrar_plantilla(self, muestra: MuestraLSM) -> Path:
        """Serializa una muestra y recarga el banco de plantillas."""
        ruta = guardar_plantilla(muestra, self.ruta_plantillas)
        self.recargar_plantillas()
        return ruta

    def set_forzar_dinamico(self, activo: bool) -> None:
        """Mantener True mientras el usuario pulsa el botón o Space."""
        activo = bool(activo)
        if activo and not self.forzar_dinamico:
            self.forzar_dinamico = True
            self._buffer_forzado = []
            self._t0_forzado = time.monotonic()
            self._pendiente_forzado = False
            self._gesto_auto = None
            self._filtro.reiniciar()
        elif not activo and self.forzar_dinamico:
            self.forzar_dinamico = False
            self._pendiente_forzado = True

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
        del frame_bgr
        ahora = time.monotonic()
        hay_mano = bool(manos)
        mano = _mano_principal(manos) if hay_mano else None
        muneca = None
        if mano is not None and mano.puntos:
            muneca = (float(mano.puntos[0].x), float(mano.puntos[0].y))
        mov = self._movimiento.actualizar(muneca, ahora)
        self._anotar_historial(ahora, mano)

        if self.forzar_dinamico:
            return self._durante_forzado(mano, hay_mano, mov)

        if self._pendiente_forzado:
            return self._cerrar_forzado(hay_mano, mov)

        if self._gesto_auto is not None:
            return self._durante_auto(mano, hay_mano, mov, ahora)

        if (
            mov.en_movimiento
            and self._secuencias
            and ahora >= self._cooldown_hasta
        ):
            return self._iniciar_auto(mano, hay_mano, mov, ahora)

        return self._predecir_estatico(manos, hay_mano, mov)

    def predecir_dinamico(
        self,
        secuencia: MuestraLSM | SecuenciaEsquema,
    ) -> ResultadoReconocimiento:
        """Compara una trayectoria con las plantillas `tipo: dinamico` vía DTW."""
        if not self._secuencias:
            return ResultadoReconocimiento(
                etiqueta=ETIQUETA_DETECTANDO,
                confianza=0.0,
                mensaje="No hay plantillas dinámicas. Captúralas en «Capturar plantillas».",
                etiqueta_cruda=ETIQUETA_DETECTANDO,
                confianza_cruda=0.0,
                modo="dinamico",
            )
        try:
            consulta = vectores_desde_secuencia(secuencia)
        except ErrorCaracteristicas as exc:
            return ResultadoReconocimiento(
                etiqueta=ETIQUETA_DETECTANDO,
                confianza=0.0,
                mensaje=f"Secuencia no usable ({exc}).",
                etiqueta_cruda=ETIQUETA_DETECTANDO,
                confianza_cruda=0.0,
                modo="dinamico",
            )
        if consulta.shape[0] < MIN_FOTOGRAMAS_DINAMICO:
            return ResultadoReconocimiento(
                etiqueta=ETIQUETA_DETECTANDO,
                confianza=0.0,
                mensaje=(
                    f"Seña demasiado corta ({consulta.shape[0]} fotogramas; "
                    f"mínimo {MIN_FOTOGRAMAS_DINAMICO})."
                ),
                etiqueta_cruda=ETIQUETA_DETECTANDO,
                confianza_cruda=0.0,
                modo="dinamico",
            )

        etiqueta, dist = mejor_plantilla_dtw(consulta, self._secuencias, self.metrica)
        if etiqueta is None:
            return ResultadoReconocimiento(
                etiqueta=ETIQUETA_DETECTANDO,
                confianza=0.0,
                mensaje="No se pudo comparar con las plantillas dinámicas.",
                etiqueta_cruda=ETIQUETA_DETECTANDO,
                confianza_cruda=0.0,
                modo="dinamico",
            )
        conf = confianza_dtw(dist, self.metrica, saturacion=SATURACION_DTW)
        n = self.n_dinamicas
        sufijo = f"{n} plantilla" + ("s" if n != 1 else "") + " dinámica" + ("s" if n != 1 else "")
        return ResultadoReconocimiento(
            etiqueta=etiqueta,
            confianza=conf,
            mensaje=f"DTW · d={dist:.3f} · {conf:.0%} · {sufijo}",
            etiqueta_cruda=etiqueta,
            confianza_cruda=conf,
            distancia=dist,
            modo="dinamico",
        )

    def _predecir_estatico(
        self,
        manos: Sequence[ManoDetectada],
        hay_mano: bool,
        mov: EstadoMovimiento,
    ) -> ResultadoReconocimiento:
        etiqueta_cruda, dist, conf_cruda = self.estimar_crudo(manos)

        if not self._vectores and not self._secuencias:
            self._filtro.reiniciar()
            if not hay_mano:
                return ResultadoReconocimiento(
                    etiqueta=ETIQUETA_SIN_DETECCION,
                    confianza=0.0,
                    mensaje="Sin manos en el encuadre · no hay plantillas",
                    etiqueta_cruda=ETIQUETA_SIN_DETECCION,
                    confianza_cruda=0.0,
                    modo="estatico",
                    en_movimiento=mov.en_movimiento,
                )
            return ResultadoReconocimiento(
                etiqueta=ETIQUETA_DETECTANDO,
                confianza=0.0,
                mensaje="No hay plantillas. Ábrelo en «Capturar plantillas».",
                etiqueta_cruda=ETIQUETA_DETECTANDO,
                confianza_cruda=0.0,
                modo="estatico",
                en_movimiento=mov.en_movimiento,
            )

        if not self._vectores:
            self._filtro.reiniciar()
            if not hay_mano:
                return ResultadoReconocimiento(
                    etiqueta=ETIQUETA_SIN_DETECCION,
                    confianza=0.0,
                    mensaje="Sin manos en el encuadre",
                    etiqueta_cruda=ETIQUETA_SIN_DETECCION,
                    modo="estatico",
                    en_movimiento=False,
                )
            extra = (
                "Solo hay plantillas dinámicas: mueve la mano o pulsa «Seña con movimiento»."
                if self._secuencias
                else "Esperando seña estable…"
            )
            return ResultadoReconocimiento(
                etiqueta=ETIQUETA_DETECTANDO,
                confianza=0.0,
                mensaje=extra,
                etiqueta_cruda=ETIQUETA_DETECTANDO,
                modo="estatico",
                en_movimiento=mov.en_movimiento,
            )

        estable = self._filtro.actualizar(
            etiqueta_cruda,
            conf_cruda,
            hay_mano=hay_mano,
        )
        return ResultadoReconocimiento(
            etiqueta=estable.etiqueta,
            confianza=estable.confianza,
            mensaje=self._mensaje_estatico(estable, hay_mano=hay_mano, dist=dist, mov=mov),
            etiqueta_cruda=_texto_crudo(etiqueta_cruda, hay_mano),
            confianza_cruda=conf_cruda,
            distancia=None if dist == float("inf") else dist,
            modo="estatico",
            en_movimiento=mov.en_movimiento,
        )

    def _durante_forzado(
        self,
        mano: ManoDetectada | None,
        hay_mano: bool,
        mov: EstadoMovimiento,
    ) -> ResultadoReconocimiento:
        foto = _fotograma_de(mano, time.monotonic() - self._t0_forzado)
        if foto is not None:
            self._buffer_forzado.append(foto)
        n = len(self._buffer_forzado)
        return ResultadoReconocimiento(
            etiqueta=ETIQUETA_DETECTANDO,
            confianza=0.0,
            mensaje=f"Grabando seña con movimiento… {n} fotogramas (suelta para reconocer)",
            etiqueta_cruda=ETIQUETA_DETECTANDO,
            confianza_cruda=0.0,
            modo="grabando",
            en_movimiento=True if hay_mano else mov.en_movimiento,
        )

    def _cerrar_forzado(
        self,
        hay_mano: bool,
        mov: EstadoMovimiento,
    ) -> ResultadoReconocimiento:
        self._pendiente_forzado = False
        frames = list(self._buffer_forzado)
        self._buffer_forzado = []
        resultado = self._reconocer_secuencia(frames)
        if resultado.confianza >= self._filtro.umbral_confianza and resultado.etiqueta not in {
            ETIQUETA_DETECTANDO,
            ETIQUETA_SIN_DETECCION,
        }:
            self._comprometer_dinamico(resultado)
        resultado.en_movimiento = mov.en_movimiento
        if not hay_mano and resultado.etiqueta == ETIQUETA_DETECTANDO:
            resultado.etiqueta = ETIQUETA_SIN_DETECCION
            resultado.etiqueta_cruda = ETIQUETA_SIN_DETECCION
        return resultado

    def _iniciar_auto(
        self,
        mano: ManoDetectada | None,
        hay_mano: bool,
        mov: EstadoMovimiento,
        ahora: float,
    ) -> ResultadoReconocimiento:
        self._filtro.reiniciar()
        self._t0_gesto = self._historial_vivo[0][0] if self._historial_vivo else ahora
        self._gesto_auto = []
        for t, esquema in self._historial_vivo:
            self._gesto_auto.append(
                FotogramaSecuencia(t=t - self._t0_gesto, mano=esquema, pose=None, rostro=None)
            )
        if mano is not None and (not self._gesto_auto or self._gesto_auto[-1].mano is None):
            foto = _fotograma_de(mano, ahora - self._t0_gesto)
            if foto is not None:
                self._gesto_auto.append(foto)
        self._quietos = 0
        return ResultadoReconocimiento(
            etiqueta=ETIQUETA_DETECTANDO,
            confianza=0.0,
            mensaje="Movimiento detectado · grabando trayectoria (DTW)…",
            etiqueta_cruda=ETIQUETA_DETECTANDO,
            modo="grabando",
            en_movimiento=True,
        )

    def _durante_auto(
        self,
        mano: ManoDetectada | None,
        hay_mano: bool,
        mov: EstadoMovimiento,
        ahora: float,
    ) -> ResultadoReconocimiento:
        assert self._gesto_auto is not None
        foto = _fotograma_de(mano, ahora - self._t0_gesto)
        if foto is not None:
            self._gesto_auto.append(foto)

        duracion = ahora - self._t0_gesto
        if mov.en_movimiento and hay_mano:
            self._quietos = 0
        else:
            self._quietos += 1

        cerrar = self._quietos >= FOTOGRAMAS_REPOSO_DINAMICO or duracion >= MAX_DURACION_DINAMICA_S
        if not cerrar:
            n = len(self._gesto_auto)
            return ResultadoReconocimiento(
                etiqueta=ETIQUETA_DETECTANDO,
                confianza=0.0,
                mensaje=f"Seña en movimiento… {n} fotogramas",
                etiqueta_cruda=ETIQUETA_DETECTANDO,
                modo="grabando",
                en_movimiento=mov.en_movimiento,
            )

        frames = list(self._gesto_auto)
        self._gesto_auto = None
        self._quietos = 0
        resultado = self._reconocer_secuencia(frames)
        if resultado.confianza >= self._filtro.umbral_confianza and resultado.etiqueta not in {
            ETIQUETA_DETECTANDO,
            ETIQUETA_SIN_DETECCION,
        }:
            self._comprometer_dinamico(resultado)
            return resultado

        self._cooldown_hasta = ahora + COOLDOWN_DINAMICO_S
        if self._ultimo_dinamico is not None and hay_mano:
            hold = self._ultimo_dinamico
            hold.mensaje = "Trayectoria poco clara · " + (resultado.mensaje or "")
            hold.en_movimiento = mov.en_movimiento
            return hold
        resultado.en_movimiento = mov.en_movimiento
        return resultado

    def _reconocer_secuencia(self, frames: list[FotogramaSecuencia]) -> ResultadoReconocimiento:
        con_mano = [f for f in frames if f.mano is not None]
        seq = SecuenciaEsquema(fps=float(FPS_OBJETIVO), fotogramas=con_mano)
        return self.predecir_dinamico(seq)

    def _comprometer_dinamico(self, resultado: ResultadoReconocimiento) -> None:
        self._ultimo_dinamico = resultado
        self._cooldown_hasta = time.monotonic() + COOLDOWN_DINAMICO_S
        resultado.mensaje = f"Seña dinámica comprometida: {resultado.etiqueta} · {resultado.confianza:.0%}"
        # El filtro estático no debe pelear con este compromiso en el siguiente fotograma.
        self._filtro.reiniciar()

    def _anotar_historial(self, t: float, mano: ManoDetectada | None) -> None:
        esquema: ManoEsquema | None = None
        if mano is not None:
            try:
                esquema = mano_desde_deteccion(mano)
            except Exception:  # noqa: BLE001 — un fotograma degenerado no debe tumbar el pipeline
                esquema = None
        self._historial_vivo.append((t, esquema))

    def _mensaje_estatico(
        self,
        estable: EstadoEstable,
        *,
        hay_mano: bool,
        dist: float,
        mov: EstadoMovimiento,
    ) -> str:
        extra = estable.mensaje
        if not hay_mano:
            return extra or "Sin manos en el encuadre"
        n_e = self.n_estaticas
        n_d = self.n_dinamicas
        sufijo = f"{n_e} estática{'s' if n_e != 1 else ''}"
        if n_d:
            sufijo += f" · {n_d} dinámica{'s' if n_d != 1 else ''}"
        mov_txt = f" · movimiento {mov.puntuacion:.2f}"
        if dist != float("inf"):
            return f"{extra} · d={dist:.3f} · {sufijo}{mov_txt}"
        return f"{extra} · {sufijo}{mov_txt}"


def _fotograma_de(mano: ManoDetectada | None, t: float) -> FotogramaSecuencia | None:
    if mano is None:
        return None
    try:
        esquema = mano_desde_deteccion(mano)
    except Exception:  # noqa: BLE001
        return None
    return FotogramaSecuencia(t=float(max(0.0, t)), mano=esquema, pose=None, rostro=None)


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
    ajustes: Ajustes | None = None,
) -> ReconocedorLSM:
    """Fábrica única que la UI usa para obtener el reconocedor."""
    aj = ajustes.normalizado() if ajustes is not None else None
    metrica_final = metrica or (aj.metrica if aj is not None else METRICA_DISTANCIA)
    return ReconocedorEstatico(
        ruta_plantillas,
        metrica=metrica_final,
        filtro=filtro,
        ajustes=aj,
    )
