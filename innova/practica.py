"""Modo Práctica de Mamatlatolli: letra estática, 5 segundos y récord.

No hay una lista guiada ni plantillas precargadas. Las letras salen de las
plantillas estáticas ``categoria: letra`` que la persona ya capturó. Un
acierto solo cuenta cuando la predicción *estable* (filtro de estabilidad)
coincide con la letra en pantalla antes de que se acabe el tiempo. Si se
acaba el tiempo, o la seña estable es otra letra, la partida termina.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from innova.config import ETIQUETA_DETECTANDO, ETIQUETA_SIN_DETECCION
from innova.esquema import CATEGORIA_LETRA
from innova.plantillas import (
    cargar_plantillas_con_errores,
    filtrar_por_categoria,
    plantillas_estaticas,
)

DURACION_RONDA_S = 5.0
PUNTOS_ACIERTO = 1

MOTIVO_TIEMPO = "tiempo"
MOTIVO_FALLA = "falla"

MENSAJE_SIN_LETRAS = (
    "Aún no hay letras estáticas. En «Capturar plantillas» elige Letra y "
    "Estática, y guarda las señas que quieras practicar. Mamatlatolli no trae "
    "una lista de palabras: Práctica usa solo las letras que tú captures."
)

_MARCADORES = frozenset(
    {
        "",
        ETIQUETA_SIN_DETECCION,
        ETIQUETA_DETECTANDO,
        ETIQUETA_DETECTANDO.upper(),
        "—",
        "-",
    }
)


def normalizar_letra(texto: str | None) -> str:
    """Mayúsculas y espacios colapsados. Vacío si no hay etiqueta útil."""
    limpio = " ".join((texto or "").strip().split()).upper()
    if limpio in _MARCADORES:
        return ""
    return limpio


def letras_estaticas_disponibles(ruta: str | Path | None = None) -> list[str]:
    """Etiquetas únicas de plantillas estáticas de letra, en orden alfabético.

    Ignora palabras y señas dinámicas: Práctica solo pide una pose quieta.
    """
    muestras, _errores = cargar_plantillas_con_errores(None if ruta is None else Path(ruta))
    estaticas = plantillas_estaticas(filtrar_por_categoria(muestras, CATEGORIA_LETRA))
    vistas: list[str] = []
    ya: set[str] = set()
    for muestra in estaticas:
        etiqueta = normalizar_letra(muestra.etiqueta)
        if not etiqueta or etiqueta in ya:
            continue
        ya.add(etiqueta)
        vistas.append(etiqueta)
    vistas.sort()
    return vistas


def elegir_letra(
    opciones: Sequence[str],
    anterior: str | None,
    rng: random.Random,
) -> str:
    """Elige una letra del banco. No repite ``anterior`` si hay otra."""
    if not opciones:
        raise ValueError("No hay letras para elegir.")
    if len(opciones) == 1 or not anterior:
        return rng.choice(list(opciones))
    otras = [opcion for opcion in opciones if opcion != anterior]
    if not otras:
        return rng.choice(list(opciones))
    return rng.choice(otras)


def compromiso_desde_resultado(resultado: Any) -> tuple[str | None, bool]:
    """Traduce la salida del reconocedor a (etiqueta, comprometida).

    Solo cuenta el modo estático. ``detectando…`` y ``—`` no están
    comprometidos: un parpadeo de la estimación cruda no es un acierto ni
    un fallo.
    """
    if getattr(resultado, "modo", "estatico") != "estatico":
        return None, False
    etiqueta = normalizar_letra(getattr(resultado, "etiqueta", None))
    if not etiqueta:
        return None, False
    return etiqueta, True


def record_tras_partida(puntuacion: int, record: int) -> tuple[int, bool]:
    """Devuelve ``(récord vigente, es_nuevo)``. Solo sube si la partida gana."""
    puntos = _no_negativo(puntuacion)
    mejor = _no_negativo(record)
    if puntos > mejor:
        return puntos, True
    return mejor, False


@dataclass(frozen=True)
class VistaPractica:
    """Instantánea que la pantalla puede pintar sin conocer el reloj."""

    letra: str
    puntuacion: int
    record: int
    restante_s: float
    acierto: bool
    terminado: bool
    motivo: str | None
    nuevo_record: bool


def texto_fin(vista: VistaPractica) -> str:
    """Copia en español para el cierre de la partida."""
    if vista.motivo == MOTIVO_FALLA:
        que = "La seña estable no era esa letra."
    else:
        que = "Se acabó el tiempo."
    if vista.nuevo_record:
        return f"{que} ¡Nuevo récord: {vista.record}!"
    return f"{que} Puntos: {vista.puntuacion}. Récord: {vista.record}."


class PartidaPractica:
    """Una corrida: letra al azar, 5 s, +1 y letra nueva, o fin de partida.

    Tras un acierto se ignora la misma letra comprometida hasta que la
    predicción estable cambie o se suelte. Así, seguir mostrando la seña
    que acaba de sumar no cuenta otra vez ni cierra la partida por «fallo».
    La pantalla debe reiniciar el filtro de estabilidad al cambiar de letra;
    este bloqueo cubre el fotograma en el que el filtro aún no se limpió.
    """

    def __init__(
        self,
        letras: Sequence[str],
        *,
        record: int = 0,
        duracion_s: float = DURACION_RONDA_S,
        rng: random.Random | None = None,
    ) -> None:
        banco: list[str] = []
        ya: set[str] = set()
        for letra in letras:
            norma = normalizar_letra(str(letra))
            if not norma or norma in ya:
                continue
            ya.add(norma)
            banco.append(norma)
        if not banco:
            raise ValueError("Práctica necesita al menos una letra estática.")
        if duracion_s <= 0:
            raise ValueError("La duración de la ronda debe ser mayor que cero.")
        self.letras = banco
        self.duracion_s = float(duracion_s)
        self.record = _no_negativo(record)
        self.puntuacion = 0
        self._rng = rng or random.Random()
        self.letra = elegir_letra(self.letras, None, self._rng)
        self._inicio: float | None = None
        self._bloqueada: str | None = None
        self.terminada = False
        self.motivo: str | None = None
        self.nuevo_record = False

    def observar(
        self,
        ahora: float,
        etiqueta: str | None,
        *,
        comprometida: bool,
    ) -> VistaPractica:
        """Avanza el reloj y aplica la predicción estable de este fotograma."""
        if self.terminada:
            return self._vista(ahora, acierto=False)

        if self._inicio is None:
            self._inicio = float(ahora)

        letra_vista = normalizar_letra(etiqueta) if comprometida else ""

        if self._bloqueada is not None and letra_vista == self._bloqueada:
            if self._expirada(ahora):
                return self._terminar(MOTIVO_TIEMPO, ahora)
            return self._vista(ahora, acierto=False)

        if self._bloqueada is not None:
            self._bloqueada = None

        if self._a_tiempo(ahora) and letra_vista == self.letra:
            return self._acertar(ahora)

        if self._expirada(ahora):
            return self._terminar(MOTIVO_TIEMPO, ahora)

        if letra_vista and letra_vista != self.letra:
            return self._terminar(MOTIVO_FALLA, ahora)

        return self._vista(ahora, acierto=False)

    def observar_resultado(self, ahora: float, resultado: Any) -> VistaPractica:
        """Igual que ``observar``, leyendo un ``ResultadoReconocimiento``."""
        etiqueta, comprometida = compromiso_desde_resultado(resultado)
        return self.observar(ahora, etiqueta, comprometida=comprometida)

    def _a_tiempo(self, ahora: float) -> bool:
        assert self._inicio is not None
        return (float(ahora) - self._inicio) <= self.duracion_s + 1e-9

    def _expirada(self, ahora: float) -> bool:
        assert self._inicio is not None
        return (float(ahora) - self._inicio) >= self.duracion_s - 1e-9

    def _acertar(self, ahora: float) -> VistaPractica:
        anterior = self.letra
        self.puntuacion += PUNTOS_ACIERTO
        self._bloqueada = anterior
        self.letra = elegir_letra(self.letras, anterior, self._rng)
        self._inicio = float(ahora)
        return self._vista(ahora, acierto=True)

    def _terminar(self, motivo: str, ahora: float) -> VistaPractica:
        self.terminada = True
        self.motivo = motivo
        self._inicio = float(ahora)
        vigente, es_nuevo = record_tras_partida(self.puntuacion, self.record)
        self.record = vigente
        self.nuevo_record = es_nuevo
        return self._vista(ahora, acierto=False)

    def _vista(self, ahora: float, *, acierto: bool) -> VistaPractica:
        return VistaPractica(
            letra=self.letra,
            puntuacion=self.puntuacion,
            record=self.record,
            restante_s=0.0 if self.terminada else self._restante(ahora),
            acierto=acierto,
            terminado=self.terminada,
            motivo=self.motivo,
            nuevo_record=self.nuevo_record,
        )

    def _restante(self, ahora: float) -> float:
        if self._inicio is None:
            return self.duracion_s
        transcurrido = max(0.0, float(ahora) - self._inicio)
        return max(0.0, self.duracion_s - transcurrido)


def _no_negativo(valor: object) -> int:
    try:
        numero = int(valor)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        try:
            numero = int(float(valor))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0
    return max(0, numero)
