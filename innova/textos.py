"""Textos visibles de Mamatlatolli, en español de México.

La lógica de reconocimiento no vive aquí: solo la copia que ve quien usa
la app en una demo escolar, aunque todavía no haya señas guardadas.
"""

from __future__ import annotations

NOMBRE_PRODUCTO = "Mamatlatolli"

CATEGORIA_PALABRA = "palabra"

MENSAJE_CAMARA_AUSENTE = (
    "No encontramos la cámara. Conéctala, cierra otras aplicaciones que la estén usando "
    "y pulsa «Reintentar cámara». También puedes abrir «Modo demostración» desde el menú."
)

LINEAS_CAMARA_VIDEO = (
    "No encontramos la cámara",
    "Conéctala y pulsa «Reintentar cámara».",
    "O abre «Modo demostración» en el menú.",
)

MENSAJE_ERROR_IMAGEN = (
    "No pudimos leer la imagen de la cámara. Pulsa «Reintentar cámara»."
)

MENSAJE_SIN_CAMARA_ACCION = (
    "Necesitamos la cámara para esto. Pulsa «Reintentar cámara» "
    "o abre «Modo demostración» desde el menú."
)

DETALLE_MINIJUEGO_VACIO = (
    "Todavía no hay letras quietas para jugar. En «Capturar plantillas» "
    "elige Letra y Estática, y guarda las señas que quieras practicar. "
    "Mamatlatolli no trae señas de fábrica: Mini juego usa solo las que tú captures."
)

PIE_MENU = "Esc o Q cierran Mamatlatolli"
PIE_VOLVER = "Esc o ← Menú vuelven    ·    Q cierra Mamatlatolli"
PIE_RECONOCIMIENTO = PIE_VOLVER + "    ·    Espacio: seña con movimiento"
PIE_JUEGO = PIE_VOLVER + "    ·    La seña tiene que quedarse quieta un momento"

AVISO_DEMO_CLI = (
    "Abriste Mamatlatolli sin cámara: Abecedario, Vocabulario y Mini juego "
    "usarán un video de ejemplo."
)

SUBTITULO_ABECEDARIO = "Letras de la LSM, quietas o con movimiento."
SUBTITULO_ABECEDARIO_DEMO = "Video de ejemplo · letras de la LSM."
SUBTITULO_VOCABULARIO = "Palabras de la LSM: mano, cuerpo y rostro."
SUBTITULO_VOCABULARIO_DEMO = "Video de ejemplo · palabras de la LSM."
SUBTITULO_DEMO = "Abecedario con un video de ejemplo, sin cámara real."
SUBTITULO_MINIJUEGO = "Seña la letra antes de que se acabe el tiempo."
SUBTITULO_CAPTURA = "Guarda una letra o una palabra, quieta o con movimiento."
SUBTITULO_BIBLIOTECA = "Las señas que ya guardaste en este equipo."
SUBTITULO_CONFIG = "Apariencia y qué tan estricta es la lectura de la seña."
SUBTITULO_ACERCA = "Lengua de Señas Mexicana, en la computadora del salón."

TITULO_POR_DESTINO = {
    "menu": NOMBRE_PRODUCTO,
    "abecedario": "Abecedario",
    "vocabulario": "Vocabulario",
    "practica": "Mini juego",
    "captura": "Capturar plantillas",
    "biblioteca": "Biblioteca de señas",
    "configuracion": "Configuración",
    "demo": "Modo demostración",
    "acerca": "Acerca de Mamatlatolli",
}

AYUDA_CONFIANZA = "Más alto: espera una seña más clara antes de aceptarla."
AYUDA_MANTENER = "Más alto: suelta antes la seña si la lectura duda."
AYUDA_CONFIRMAR = "Cuántas lecturas seguidas hacen falta para aceptar la seña."
AYUDA_SENSIBILIDAD = "Más alto: nota antes que la mano se está moviendo."
AYUDA_VENTANA = "Cuánto tiempo mira la mano para decidir si se mueve."
AYUDA_METRICA = (
    "Por forma compara el dibujo de la mano. Por dirección compara hacia dónde apunta. "
    "Si no estás seguro, deja Por forma."
)

ETIQUETA_CONFIANZA = "Confianza mínima"
ETIQUETA_MANTENER = "Mantener la seña"
ETIQUETA_CONFIRMAR = "Lecturas para confirmar"
ETIQUETA_SENSIBILIDAD = "Sensibilidad al movimiento"
ETIQUETA_VENTANA = "Tiempo para notar el movimiento"
ETIQUETA_METRICA = "Cómo comparar la seña"

MENSAJE_AJUSTES_GUARDADOS = (
    "Listo. Guardé los ajustes. Se aplican al volver a Abecedario, Vocabulario o Mini juego."
)
MENSAJE_AJUSTES_RESTAURADOS = (
    "Volví a los valores recomendados. Pulsa «Guardar ajustes» si quieres dejarlos así."
)


def titulo_pantalla(destino: str) -> str:
    """Título grande de la pantalla: el mismo nombre que la tarjeta del menú."""
    return TITULO_POR_DESTINO.get(destino, NOMBRE_PRODUCTO)


def titulo_ventana(destino: str) -> str:
    """Título de la ventana del sistema, alineado con la pantalla actual."""
    if destino in {"", "menu"}:
        return NOMBRE_PRODUCTO
    nombre = titulo_pantalla(destino)
    if destino == "acerca":
        return f"{NOMBRE_PRODUCTO} — Acerca de"
    return f"{NOMBRE_PRODUCTO} — {nombre}"


def etiqueta_visible(etiqueta: str | None) -> str:
    """Cómo se muestra el marcador interno, sin la jerga del reconocedor."""
    texto = (etiqueta or "").strip()
    if texto.lower() in {"detectando…", "detectando...", "detectando"}:
        return "Buscando…"
    if texto in {"", "—", "-"}:
        return "—"
    return texto


def mensaje_sin_manos() -> str:
    return "No veo las manos. Colócalas frente a la cámara, con buena luz."


def mensaje_mano_visible() -> str:
    return "Ya veo la mano. Puedes guardar la seña."


def mensaje_esperando_estable() -> str:
    return "Mantén la seña un momento para confirmarla."


def mensaje_sena_lista(etiqueta: str | None = None) -> str:
    nombre = (etiqueta or "").strip()
    if nombre and nombre not in {"—", "-"}:
        return f"Seña lista: {nombre}."
    return "Seña lista."


def mensaje_mantener_sena() -> str:
    return "Sigo con la misma seña."


def mensaje_cambio_inestable() -> str:
    return "Vi otra seña, pero aún no está clara."


def mensaje_banco_vacio(categoria: str) -> str:
    if categoria == CATEGORIA_PALABRA:
        return (
            "Todavía no hay palabras en Vocabulario. "
            "Ve a «Capturar plantillas», elige Palabra y guarda unas señas."
        )
    return (
        "Todavía no hay letras guardadas. "
        "Ve a «Capturar plantillas», elige Letra y guarda las señas del abecedario."
    )


def mensaje_sin_dinamicas(categoria: str) -> str:
    if categoria == CATEGORIA_PALABRA:
        return (
            "Todavía no hay palabras con movimiento. "
            "En «Capturar plantillas» elige Palabra y Dinámica."
        )
    return (
        "Todavía no hay letras con movimiento. "
        "En «Capturar plantillas» elige Letra y Dinámica."
    )


def mensaje_solo_dinamicas() -> str:
    return "Solo hay señas con movimiento. Muévela o pulsa «Seña con movimiento»."


def mensaje_sena_corta() -> str:
    return "Esa seña quedó muy corta. Haz el movimiento completo y suelta al terminar."


def mensaje_sena_no_leida() -> str:
    return "No pude leer esa seña con movimiento. Inténtala otra vez, un poco más despacio."


def mensaje_sin_comparar() -> str:
    return "No pude comparar esa seña. Inténtala de nuevo, con la mano bien visible."


def mensaje_sena_movimiento(etiqueta: str) -> str:
    return f"Seña con movimiento: {etiqueta}."


def mensaje_grabando() -> str:
    return "Grabando la seña… suelta cuando termines."


def mensaje_movimiento_detectado() -> str:
    return "Vi que la mano se mueve. Sigue la seña y quédate quieto al terminar."


def mensaje_siguiendo_movimiento() -> str:
    return "Siguiendo el movimiento…"


def mensaje_trayectoria_poco_clara() -> str:
    return "No quedó clara. Intenta el movimiento otra vez."


def mensaje_dinamica_lista(etiqueta: str) -> str:
    return f"Listo: {etiqueta}."


def texto_vacio_biblioteca(filtro: str) -> tuple[str, str]:
    """Título y detalle cuando el filtro de la biblioteca no tiene señas."""
    clave = (filtro or "").strip().lower()
    if clave == "palabra":
        return (
            "Todavía no hay palabras",
            "Ve a «Capturar plantillas», elige Palabra y guarda la seña. "
            "Aquí podrás probarla o borrarla.",
        )
    if clave == "letra":
        return (
            "Todavía no hay letras",
            "Ve a «Capturar plantillas», elige Letra y guarda la seña. "
            "Abecedario y Mini juego la van a usar.",
        )
    return (
        "La biblioteca está vacía",
        "Todavía no hay señas en este equipo. Ve a «Capturar plantillas» "
        "y guarda una letra o una palabra.",
    )


def texto_vacio_reconocimiento(categoria: str) -> tuple[str, str]:
    if categoria == CATEGORIA_PALABRA:
        return (
            "Todavía no hay palabras",
            "Ve a «Capturar plantillas», elige Palabra y guarda unas señas. "
            "Vocabulario las leerá en esta pantalla.",
        )
    return (
        "Todavía no hay letras",
        "Ve a «Capturar plantillas», elige Letra y guarda las señas. "
        "Abecedario las leerá en esta pantalla.",
    )


def texto_vacio_captura() -> tuple[str, str]:
    return (
        "Aún no hay señas guardadas",
        "Elige Letra o Palabra, coloca la seña frente a la cámara y pulsa Guardar. "
        "Así Abecedario, Vocabulario y Mini juego tendrán qué reconocer.",
    )


def titulo_vacio_minijuego() -> str:
    return "Todavía no hay letras para jugar"


def resumen_biblioteca(
    *,
    visibles: int,
    quietas: int,
    con_movimiento: int,
    letras: int,
    palabras: int,
    errores: int,
    banco_vacio: bool,
) -> str:
    if banco_vacio and errores == 0:
        return "Cuando captures la primera seña, aparecerá en esta lista."
    texto = (
        f"{visibles} en pantalla: {quietas} quietas · {con_movimiento} con movimiento"
        f"  ·  en el equipo: {letras} letras · {palabras} palabras"
    )
    if errores:
        texto += f"  ·  {errores} no se pudieron leer"
    return texto


def texto_conteo_senas(quietas: int, con_movimiento: int) -> str:
    return f"Señas guardadas: {quietas} quietas · {con_movimiento} con movimiento"


def texto_modo(modo: str, en_movimiento: bool) -> str:
    if modo == "grabando":
        return "Modo: grabando el movimiento"
    if modo == "dinamico":
        return "Modo: seña con movimiento"
    if en_movimiento:
        return "Modo: seña quieta · la mano se está moviendo"
    return "Modo: seña quieta · la mano está quieta"


def texto_lectura(etiqueta: str | None, confianza: float) -> str:
    visible = etiqueta_visible(etiqueta)
    if visible in {"—", "Buscando…"}:
        return f"Lectura de este momento: {visible}"
    return f"Lectura de este momento: {visible} ({confianza:.0%})"


def texto_transcripcion_vacia(*, palabras: bool) -> str:
    if palabras:
        return "Cuando una palabra se confirme, aparecerá aquí."
    return "Cuando una letra se quede quieta, aparecerá aquí."


def texto_fuente(fuente: str) -> str:
    limpio = (fuente or "").strip()
    if limpio.lower().startswith("cámara"):
        return "Cámara lista"
    if "demostración" in limpio.lower():
        return "Video de ejemplo"
    return limpio or "Cámara: —"


def texto_estado_manos(n_manos: int, fuente: str, *, camara_ausente: bool = False) -> str:
    if camara_ausente:
        return "Manos: 0   ·   Cámara: no disponible"
    return f"Manos: {n_manos}   ·   {texto_fuente(fuente)}"


def ayuda_captura(*, palabra: bool, dinamica: bool) -> str:
    sujeto = "la palabra" if palabra else "la letra"
    extra = (
        " Si se ve a la persona, también se guardan el cuerpo y el rostro."
        if palabra
        else " En las letras solo se guarda la mano."
    )
    if dinamica:
        return (
            f"Escribe {sujeto}. Pulsa el botón o mantén Espacio mientras haces el movimiento "
            f"y suelta para guardar.{extra}"
        )
    return (
        f"Coloca la seña quieta, escribe {sujeto} y pulsa Guardar. "
        f"Varias tomas de la misma seña ayudan.{extra}"
    )


def mensaje_falta_etiqueta(*, palabra: bool, grabando: bool) -> str:
    sujeto = "la palabra" if palabra else "la letra"
    if grabando:
        return f"Escribe {sujeto} antes de grabar el movimiento."
    return f"Escribe {sujeto} antes de guardar."


def mensaje_grabacion_descartada() -> str:
    return "No guardé nada: faltaba escribir la letra o la palabra."


def mensaje_plantilla_guardada(etiqueta: str, *, palabra: bool, dinamica: bool) -> str:
    que = "la palabra" if palabra else "la letra"
    como = " con movimiento" if dinamica else ""
    return f"Listo. Guardé {que} {etiqueta.strip().upper()}{como}."


def mensaje_no_se_pudo_guardar() -> str:
    return "No pude guardar la seña. Revisa que la mano se vea y vuelve a intentarlo."


def aviso_probar(etiqueta: str, tipo: str, categoria: str) -> str:
    modo = "Vocabulario" if categoria == CATEGORIA_PALABRA else "Abecedario"
    if tipo == "dinamico":
        return (
            f"Vamos a probar «{etiqueta}» en {modo}. "
            "Haz el movimiento o pulsa «Seña con movimiento»."
        )
    return f"Vamos a probar «{etiqueta}» en {modo}. Mantén la seña quieta un momento."


def confirmar_eliminar(etiqueta: str) -> str:
    return f"¿Quieres borrar la seña «{etiqueta}»? Esta acción no se puede deshacer."


def mensaje_acierto(puntos: int) -> str:
    return f"¡Muy bien! +{puntos} puntos"


def mensaje_espera_inicio() -> str:
    return "Pulsa Inicio cuando estés listo. La letra y los 5 segundos empiezan en ese momento."


def mensaje_durante_ronda() -> str:
    return "Menos de 1 segundo: 1000 puntos. Hasta 3 segundos: 700. Antes de que se acaben: 500."


def banner_demo() -> str:
    return "Modo demostración · video de ejemplo, sin cámara"


def banner_grabando() -> str:
    return "Grabando la seña…"
