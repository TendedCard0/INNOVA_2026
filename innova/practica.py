"""Mini juego de Mamatlatolli: letra estática, 5 segundos y récord.

No hay una lista guiada ni plantillas precargadas. Las letras salen de las
plantillas estáticas ``categoria: letra`` que la persona ya capturó. Un
acierto solo cuenta cuando la predicción *estable* (filtro de estabilidad)
coincide con la letra en pantalla antes de que se acabe el tiempo. Mientras
más rápido, más puntos. Si se acaba el tiempo, o la seña estable es otra
letra, la partida termina.
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
# Rapidez del acierto estable: menos de 1 s, de 1 s a menos de 3 s, de 3 s a menos de 5 s.
PUNTOS_RAPIDO = 1000
PUNTOS_MEDIO = 700
PUNTOS_LENTO = 500
UMBRAL_RAPIDO_S = 1.0
UMBRAL_MEDIO_S = 3.0

MOTIVO_TIEMPO = "tiempo"
MOTIVO_FALLA = "falla"

MENSAJE_SIN_LETRAS = (
    "Aún no hay letras estáticas. En «Capturar plantillas» elige Letra y "
    "Estática, y guarda las señas que quieras jugar. Mamatlatolli no trae "
    "una lista de palabras: Mini juego usa solo las letras que tú captures."
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

    Ignora palabras y señas dinámicas: Mini juego solo pide una pose quieta.
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


def puntos_por_rapidez(transcurrido_s: float) -> int:
    """Puntos de un acierto según cuánto tardó la seña estable.

    Menos de 1 s → 1000. De 1 s a menos de 3 s → 700. De 3 s a menos de 5 s → 500.
    A los 5 s ya no hay acierto: la ronda se pierde y esto devuelve 0.
    """
    try:
        t = float(transcurrido_s)
    except (TypeError, ValueError):
        return 0
    if t < UMBRAL_RAPIDO_S:
        return PUNTOS_RAPIDO
    if t < UMBRAL_MEDIO_S:
        return PUNTOS_MEDIO
    if t < DURACION_RONDA_S:
        return PUNTOS_LENTO
    return 0


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
    puntos_obtenidos: int = 0
    en_curso: bool = False


def texto_fin(vista: VistaPractica) -> str:
    """Copia en español para el cierre de la partida."""
    if vista.motivo == MOTIVO_FALLA:
        que = "La seña estable no era esa letra."
    else:
        que = "Se acabó el tiempo."
    if vista.nuevo_record:
        return f"{que} ¡Nuevo récord: {vista.record}!"
    return f"{que} Puntos: {vista.puntuacion}. Récord: {vista.record}."


SONIDO_ACIERTO = "acierto"
SONIDO_ERROR = "error"
SONIDO_RECORD = "record"


def sonidos_para(
    vista: VistaPractica,
    *,
    puntuacion_antes: int,
    record_guardado: int,
    record_anunciado: bool,
) -> tuple[str, ...]:
    """Efectos de un fotograma. El récord suena solo la vez que se supera el máximo."""
    if vista.acierto:
        sonidos = [SONIDO_ACIERTO]
        if (
            not record_anunciado
            and puntuacion_antes <= record_guardado < vista.puntuacion
        ):
            sonidos.append(SONIDO_RECORD)
        return tuple(sonidos)
    if vista.terminado:
        sonidos = [SONIDO_ERROR]
        if (
            not record_anunciado
            and vista.nuevo_record
            and vista.puntuacion > record_guardado
        ):
            sonidos.append(SONIDO_RECORD)
        return tuple(sonidos)
    return ()


class PartidaPractica:
    """Una corrida: letra al azar, 5 s, puntos por rapidez, o fin de partida.

    No arranca sola: ``iniciar`` pone en marcha el cronómetro. Un acierto
    para el reloj hasta el siguiente ``iniciar`` (el botón Siguiente).
    Tras un acierto se ignora la misma letra comprometida hasta que la
    predicción estable cambie o se suelte. Así, seguir mostrando la seña
    que acaba de sumar no cuenta otra vez ni cierra la partida por «fallo».
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
            raise ValueError("Mini juego necesita al menos una letra estática.")
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
        self.en_curso = False
        self.terminada = False
        self.motivo: str | None = None
        self.nuevo_record = False

    def iniciar(self, ahora: float) -> VistaPractica:
        """Arranca el cronómetro de la letra actual. No reinicia una ronda ya en curso."""
        if self.terminada or self.en_curso:
            return self._vista(ahora, acierto=False)
        self.en_curso = True
        self._inicio = float(ahora)
        return self._vista(ahora, acierto=False)

    def observar(
        self,
        ahora: float,
        etiqueta: str | None,
        *,
        comprometida: bool,
    ) -> VistaPractica:
        """Avanza el reloj y aplica la predicción estable de este fotograma."""
        if self.terminada or not self.en_curso:
            return self._vista(ahora, acierto=False)

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

    def _transcurrido(self, ahora: float) -> float:
        assert self._inicio is not None
        return max(0.0, float(ahora) - self._inicio)

    def _a_tiempo(self, ahora: float) -> bool:
        # El tramo de 500 puntos es [3 s, 5 s): en el segundo 5 la ronda ya se pierde.
        return self._transcurrido(ahora) < self.duracion_s

    def _expirada(self, ahora: float) -> bool:
        return self._transcurrido(ahora) >= self.duracion_s - 1e-9

    def _acertar(self, ahora: float) -> VistaPractica:
        obtenidos = puntos_por_rapidez(self._transcurrido(ahora))
        anterior = self.letra
        self.puntuacion += obtenidos
        self._bloqueada = anterior
        self.letra = elegir_letra(self.letras, anterior, self._rng)
        # La siguiente letra espera a Inicio / Siguiente: el reloj no sigue solo.
        self.en_curso = False
        self._inicio = None
        return self._vista(ahora, acierto=True, puntos_obtenidos=obtenidos)

    def _terminar(self, motivo: str, ahora: float) -> VistaPractica:
        self.terminada = True
        self.en_curso = False
        self.motivo = motivo
        self._inicio = float(ahora)
        vigente, es_nuevo = record_tras_partida(self.puntuacion, self.record)
        self.record = vigente
        self.nuevo_record = es_nuevo
        return self._vista(ahora, acierto=False)

    def _vista(self, ahora: float, *, acierto: bool, puntos_obtenidos: int = 0) -> VistaPractica:
        return VistaPractica(
            letra=self.letra,
            puntuacion=self.puntuacion,
            record=self.record,
            restante_s=0.0 if self.terminada else self._restante(ahora),
            acierto=acierto,
            terminado=self.terminada,
            motivo=self.motivo,
            nuevo_record=self.nuevo_record,
            puntos_obtenidos=puntos_obtenidos,
            en_curso=self.en_curso and not self.terminada,
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
