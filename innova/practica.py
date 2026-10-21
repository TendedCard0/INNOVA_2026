"""Mini juego de Mamatlatolli: letra estática, nivel y récord.

No hay una lista guiada ni plantillas precargadas. Las letras salen de las
plantillas estáticas ``categoria: letra`` que la persona ya capturó. Un
acierto solo cuenta cuando la predicción *estable* (filtro de estabilidad)
coincide con la letra en pantalla antes de que se acabe el tiempo. Mientras
más rápido, más puntos. Si se acaba el tiempo, o la seña estable es otra
letra, la partida termina.

El nivel elige la duración (Fácil 8 s, Medio 6 s, Difícil 4 s) y si se
muestra la foto de apoyo. Los puntos siguen siendo 1000 / 700 / 500; los
cortes se estiran con la misma proporción que tenía la ronda de 5 s
(antes de 1 s, antes de 3 s, y el resto).
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
from innova.textos import DETALLE_MINIJUEGO_VACIO as MENSAJE_SIN_LETRAS

# Referencia histórica de los tramos (1 s y 3 s dentro de 5 s). Los niveles
# no usan esta duración: estiran los mismos cortes al 20 % y al 60 % de su reloj.
DURACION_RONDA_S = 5.0
PUNTOS_RAPIDO = 1000
PUNTOS_MEDIO = 700
PUNTOS_LENTO = 500
UMBRAL_RAPIDO_S = 1.0
UMBRAL_MEDIO_S = 3.0

NIVEL_FACIL = "facil"
NIVEL_MEDIO = "medio"
NIVEL_DIFICIL = "dificil"

DURACION_FACIL_S = 8.0
DURACION_MEDIO_S = 6.0
DURACION_DIFICIL_S = 4.0

APOYO_SIEMPRE = "siempre"
APOYO_INICIO = "inicio"
APOYO_NUNCA = "nunca"
# En Medio la foto se ve al empezar el turno y se oculta al cumplir este tiempo.
SEGUNDOS_IMAGEN_INICIO = 2.0


@dataclass(frozen=True)
class NivelMiniJuego:
    """Duración y política de la foto de apoyo de un nivel."""

    clave: str
    nombre: str
    duracion_s: float
    apoyo: str


NIVELES: dict[str, NivelMiniJuego] = {
    NIVEL_FACIL: NivelMiniJuego(NIVEL_FACIL, "Fácil", DURACION_FACIL_S, APOYO_SIEMPRE),
    NIVEL_MEDIO: NivelMiniJuego(NIVEL_MEDIO, "Medio", DURACION_MEDIO_S, APOYO_INICIO),
    NIVEL_DIFICIL: NivelMiniJuego(NIVEL_DIFICIL, "Difícil", DURACION_DIFICIL_S, APOYO_NUNCA),
}
NIVELES_ORDEN: tuple[str, ...] = (NIVEL_FACIL, NIVEL_MEDIO, NIVEL_DIFICIL)

MOTIVO_TIEMPO = "tiempo"
MOTIVO_FALLA = "falla"

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


def imagen_de_letra(etiqueta: str, ruta: str | Path | None = None) -> Path | None:
    """JPEG de apoyo de una letra estática, o None si no hay archivo.

    Si hay varias tomas con foto, usa la de marca de tiempo más reciente.
    Una plantilla vieja, o una ruta que no está, no es un error: devuelve None.
    """
    from innova.config import RUTA_PLANTILLAS
    from innova.imagen_apoyo import ruta_imagen_segura

    objetivo = normalizar_letra(etiqueta)
    if not objetivo:
        return None
    base = Path(ruta) if ruta is not None else Path(RUTA_PLANTILLAS)
    muestras, _errores = cargar_plantillas_con_errores(base)
    candidatas = [
        muestra
        for muestra in plantillas_estaticas(filtrar_por_categoria(muestras, CATEGORIA_LETRA))
        if normalizar_letra(muestra.etiqueta) == objetivo
        and muestra.imagen_apoyo is not None
        and muestra.imagen_apoyo.archivo
    ]
    candidatas.sort(key=lambda muestra: muestra.metadatos.marca_tiempo)
    for muestra in reversed(candidatas):
        assert muestra.imagen_apoyo is not None
        destino = ruta_imagen_segura(base, muestra.imagen_apoyo.archivo)
        if destino is not None and destino.is_file():
            return destino
    return None


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


def normalizar_nivel(valor: str | None) -> str:
    """``facil``, ``medio`` o ``dificil``. Cualquier otra cosa cae en Fácil."""
    clave = str(valor or "").strip().lower()
    alias = {
        "fácil": NIVEL_FACIL,
        "facil": NIVEL_FACIL,
        "medio": NIVEL_MEDIO,
        "difícil": NIVEL_DIFICIL,
        "dificil": NIVEL_DIFICIL,
    }
    return alias.get(clave, NIVEL_FACIL)


def nivel_de(clave: str | None) -> NivelMiniJuego:
    return NIVELES[normalizar_nivel(clave)]


def umbrales_puntos(duracion_s: float) -> tuple[float, float]:
    """Cortes de 1000 y de 700, proporcionales a la duración.

    En la ronda de referencia (5 s) eran 1 s y 3 s: el 20 % y el 60 % del
    tiempo. Fácil (8 s) queda en 1.6 s y 4.8 s; Medio (6 s) en 1.2 s y 3.6 s;
    Difícil (4 s) en 0.8 s y 2.4 s.
    """
    duracion = float(duracion_s)
    if duracion <= 0:
        return 0.0, 0.0
    return (
        duracion * UMBRAL_RAPIDO_S / DURACION_RONDA_S,
        duracion * UMBRAL_MEDIO_S / DURACION_RONDA_S,
    )


def puntos_por_rapidez(transcurrido_s: float, duracion_s: float = DURACION_RONDA_S) -> int:
    """Puntos de un acierto según cuánto tardó la seña estable.

    Con la duración de referencia (5 s): menos de 1 s → 1000, de 1 s a menos
    de 3 s → 700, de 3 s a menos de 5 s → 500. En otro nivel los cortes son
    la misma fracción del reloj. Al cumplirse la duración ya no hay acierto.
    """
    try:
        t = float(transcurrido_s)
    except (TypeError, ValueError):
        return 0
    try:
        duracion = float(duracion_s)
    except (TypeError, ValueError):
        return 0
    if duracion <= 0 or t >= duracion:
        return 0
    rapido, medio = umbrales_puntos(duracion)
    if t < rapido:
        return PUNTOS_RAPIDO
    if t < medio:
        return PUNTOS_MEDIO
    return PUNTOS_LENTO


def apoyo_visible(nivel: str | None, transcurrido_s: float, *, en_curso: bool) -> bool:
    """Si la foto (o el aviso de que no hay foto) debe verse en este instante.

    Fácil: todo el turno. Medio: los primeros 2 s de cada letra. Difícil: nunca.
    Fuera de un turno en curso, no se muestra.
    """
    if not en_curso:
        return False
    info = NIVELES.get(str(nivel or "").strip().lower())
    if info is None or info.apoyo == APOYO_NUNCA:
        return False
    if info.apoyo == APOYO_SIEMPRE:
        return True
    try:
        t = float(transcurrido_s)
    except (TypeError, ValueError):
        t = 0.0
    return t < SEGUNDOS_IMAGEN_INICIO


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
    nivel: str = ""
    apoyo_visible: bool = False
    duracion_s: float = DURACION_RONDA_S


def texto_fin(vista: VistaPractica) -> str:
    """Copia en español para el cierre de la partida."""
    if vista.motivo == MOTIVO_FALLA:
        que = "Esa no era la letra. La partida se detiene aquí."
    else:
        que = "Se acabó el tiempo."
    if vista.nuevo_record:
        return f"{que} ¡Nuevo récord: {vista.record} puntos!"
    return f"{que} Llevas {vista.puntuacion} puntos. El récord sigue en {vista.record}."


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
    """Una corrida: letra al azar, reloj del nivel, puntos por rapidez, o fin.

    No arranca sola: ``iniciar`` pone en marcha la partida. Cada acierto
    cambia de letra y reinicia el reloj sin otra pulsación. Solo una derrota
    devuelve la partida a la espera.
    Tras un acierto se ignora la misma letra comprometida hasta que la
    predicción estable cambie o se suelte. Así, seguir mostrando la seña
    que acaba de sumar no cuenta otra vez ni cierra la partida por «fallo».

    ``nivel`` vacío deja la duración que se pase (5 s si no se dice otra).
    La pantalla del juego siempre pasa un nivel de ``NIVELES``.
    """

    def __init__(
        self,
        letras: Sequence[str],
        *,
        record: int = 0,
        duracion_s: float | None = None,
        nivel: str = "",
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
        self.nivel = nivel if nivel in NIVELES else ""
        if duracion_s is None:
            duracion = NIVELES[self.nivel].duracion_s if self.nivel else DURACION_RONDA_S
        else:
            duracion = float(duracion_s)
        if duracion <= 0:
            raise ValueError("La duración de la ronda debe ser mayor que cero.")
        self.letras = banco
        self.duracion_s = duracion
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
        # El tramo lento es el último 40 % del reloj. Al cumplirse la duración, se pierde.
        return self._transcurrido(ahora) < self.duracion_s

    def _expirada(self, ahora: float) -> bool:
        return self._transcurrido(ahora) >= self.duracion_s - 1e-9

    def _acertar(self, ahora: float) -> VistaPractica:
        obtenidos = puntos_por_rapidez(self._transcurrido(ahora), self.duracion_s)
        anterior = self.letra
        self.puntuacion += obtenidos
        self._bloqueada = anterior
        self.letra = elegir_letra(self.letras, anterior, self._rng)
        self._inicio = float(ahora)
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
        en_curso = self.en_curso and not self.terminada
        transcurrido = self._transcurrido(ahora) if en_curso and self._inicio is not None else 0.0
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
            en_curso=en_curso,
            nivel=self.nivel,
            apoyo_visible=apoyo_visible(self.nivel, transcurrido, en_curso=en_curso),
            duracion_s=self.duracion_s,
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
