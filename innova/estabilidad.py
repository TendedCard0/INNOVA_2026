"""Filtro de estabilidad: umbral + voto temporal + histéresis.

La estimación cruda de cada fotograma es ruidosa. Este módulo solo *compromete*
una letra cuando:

1. La confianza supera el umbral.
2. Hay acuerdo temporal: N fotogramas consecutivos **o** M de los últimos K.
3. La histéresis evita que una letra ya mostrada parpadee: se mantiene con un
   umbral más bajo y no cambia hasta que otra letra también se estabilice.

Las letras en movimiento (J, Ñ, Z, etc.) se resolverán en la fase 2b con DTW;
aquí el filtro opera sobre etiquetas estáticas fotograma a fotograma.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from innova.config import (
    ETIQUETA_DETECTANDO,
    ETIQUETA_SIN_DETECCION,
    FOTOGRAMAS_CONSECUTIVOS,
    FOTOGRAMAS_PACIENCIA,
    UMBRAL_CONFIANZA_LETRA,
    UMBRAL_HISTERSIS,
    VENTANA_K,
    VOTOS_M,
)


@dataclass
class EstadoEstable:
    """Salida del filtro para un fotograma."""

    etiqueta: str
    confianza: float
    mensaje: str
    comprometida: bool


class FiltroEstabilidad:
    """Acumula predicciones crudas y emite una letra estable (o un marcador)."""

    def __init__(
        self,
        *,
        umbral_confianza: float = UMBRAL_CONFIANZA_LETRA,
        umbral_histeresis: float = UMBRAL_HISTERSIS,
        consecutivos: int = FOTOGRAMAS_CONSECUTIVOS,
        votos_m: int = VOTOS_M,
        ventana_k: int = VENTANA_K,
        paciencia: int = FOTOGRAMAS_PACIENCIA,
    ) -> None:
        if consecutivos < 1:
            raise ValueError("consecutivos debe ser >= 1.")
        if votos_m < 1 or ventana_k < 1:
            raise ValueError("votos_m y ventana_k deben ser >= 1.")
        self.umbral_confianza = umbral_confianza
        self.umbral_histeresis = umbral_histeresis
        self.consecutivos = consecutivos
        self.votos_m = votos_m
        self.ventana_k = ventana_k
        self.paciencia = paciencia

        self._historial: deque[tuple[str | None, float]] = deque(maxlen=ventana_k)
        self._comprometida: str | None = None
        self._confianza_comprometida: float = 0.0
        self._candidato: str | None = None
        self._racha: int = 0
        self._perdidos: int = 0

    def reiniciar(self) -> None:
        self._historial.clear()
        self._comprometida = None
        self._confianza_comprometida = 0.0
        self._candidato = None
        self._racha = 0
        self._perdidos = 0

    def actualizar(
        self,
        etiqueta_cruda: str | None,
        confianza: float,
        *,
        hay_mano: bool,
    ) -> EstadoEstable:
        """Incorpora un fotograma y devuelve la seña que la UI debe mostrar."""
        candidato = self._clasificar_fotograma(etiqueta_cruda, confianza)

        if candidato is None:
            self._perdidos += 1
            self._candidato = None
            self._racha = 0
            self._historial.append((None, confianza))
        else:
            self._perdidos = 0
            if candidato == self._candidato:
                self._racha += 1
            else:
                self._candidato = candidato
                self._racha = 1
            self._historial.append((candidato, confianza))

        return self._decidir(candidato, confianza, hay_mano=hay_mano)

    def _clasificar_fotograma(
        self,
        etiqueta_cruda: str | None,
        confianza: float,
    ) -> str | None:
        if not etiqueta_cruda:
            return None
        # Histéresis: la letra ya comprometida se acepta con umbral más bajo.
        if (
            self._comprometida is not None
            and etiqueta_cruda == self._comprometida
            and confianza >= self.umbral_histeresis
        ):
            return etiqueta_cruda
        if confianza >= self.umbral_confianza:
            return etiqueta_cruda
        return None

    def _decidir(
        self,
        candidato: str | None,
        confianza: float,
        *,
        hay_mano: bool,
    ) -> EstadoEstable:
        if self._comprometida is None:
            if candidato is not None and self._hay_acuerdo(candidato):
                return self._comprometer(candidato, confianza)
            return self._sin_compromiso(hay_mano)

        if candidato == self._comprometida:
            self._confianza_comprometida = confianza
            return EstadoEstable(
                etiqueta=self._comprometida,
                confianza=confianza,
                mensaje=f"Seña estable · {confianza:.0%}",
                comprometida=True,
            )

        if candidato is not None and self._hay_acuerdo(candidato):
            return self._comprometer(candidato, confianza)

        if candidato is None and self._perdidos >= self.paciencia:
            self._comprometida = None
            self._confianza_comprometida = 0.0
            return self._sin_compromiso(hay_mano)

        # Sigue vigente por histéresis (cambio inestable o hueco breve).
        if candidato is None:
            mensaje = "Manteniendo seña (histéresis)"
        else:
            mensaje = f"Cambio inestable hacia {candidato}"
        return EstadoEstable(
            etiqueta=self._comprometida,
            confianza=self._confianza_comprometida,
            mensaje=mensaje,
            comprometida=True,
        )

    def _hay_acuerdo(self, etiqueta: str) -> bool:
        if self._candidato == etiqueta and self._racha >= self.consecutivos:
            return True
        votos_altos = sum(
            1 for e, c in self._historial if e == etiqueta and c >= self.umbral_confianza
        )
        return votos_altos >= self.votos_m

    def _comprometer(self, etiqueta: str, confianza: float) -> EstadoEstable:
        self._comprometida = etiqueta
        self._confianza_comprometida = confianza
        return EstadoEstable(
            etiqueta=etiqueta,
            confianza=confianza,
            mensaje=f"Letra comprometida: {etiqueta} · {confianza:.0%}",
            comprometida=True,
        )

    def _sin_compromiso(self, hay_mano: bool) -> EstadoEstable:
        if not hay_mano:
            return EstadoEstable(
                etiqueta=ETIQUETA_SIN_DETECCION,
                confianza=0.0,
                mensaje="Sin manos en el encuadre",
                comprometida=False,
            )
        return EstadoEstable(
            etiqueta=ETIQUETA_DETECTANDO,
            confianza=0.0,
            mensaje="Esperando seña estable…",
            comprometida=False,
        )
