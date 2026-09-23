"""Menú principal de Mamatlatolli: destinos y navegación (sin Tk)."""

from __future__ import annotations

from dataclasses import dataclass

from innova.esquema import CATEGORIA_LETRA, CATEGORIA_PALABRA

DESTINO_MENU = "menu"
DESTINO_ABECEDARIO = "abecedario"
DESTINO_VOCABULARIO = "vocabulario"
DESTINO_PRACTICA = "practica"
DESTINO_CAPTURA = "captura"
DESTINO_BIBLIOTECA = "biblioteca"
DESTINO_CONFIGURACION = "configuracion"
DESTINO_DEMO = "demo"
DESTINO_ACERCA = "acerca"

DESTINOS_VALIDOS = frozenset(
    {
        DESTINO_MENU,
        DESTINO_ABECEDARIO,
        DESTINO_VOCABULARIO,
        DESTINO_PRACTICA,
        DESTINO_CAPTURA,
        DESTINO_BIBLIOTECA,
        DESTINO_CONFIGURACION,
        DESTINO_DEMO,
        DESTINO_ACERCA,
    }
)

DESTINOS_RECONOCIMIENTO = frozenset({DESTINO_ABECEDARIO, DESTINO_VOCABULARIO, DESTINO_DEMO})

# (id, etiqueta visible, descripción corta)
OPCIONES_MENU: tuple[tuple[str, str, str], ...] = (
    (
        DESTINO_ABECEDARIO,
        "Abecedario",
        "Letras de la LSM, quietas o con movimiento.",
    ),
    (
        DESTINO_VOCABULARIO,
        "Vocabulario",
        "Palabras de la LSM: mano, cuerpo y rostro.",
    ),
    (
        DESTINO_PRACTICA,
        "Mini juego",
        "Contrarreloj de letras · récord personal.",
    ),
    (
        DESTINO_CAPTURA,
        "Capturar plantillas",
        "Guarda una letra o una palabra, quieta o con movimiento.",
    ),
    (
        DESTINO_BIBLIOTECA,
        "Biblioteca de señas",
        "Revisa, prueba, borra o llévalas a otra computadora.",
    ),
    (
        DESTINO_CONFIGURACION,
        "Configuración",
        "Apariencia, y qué tan estricta es la lectura.",
    ),
    (
        DESTINO_DEMO,
        "Modo demostración",
        "Abecedario con un video de ejemplo, sin cámara.",
    ),
    (
        DESTINO_ACERCA,
        "Acerca de Mamatlatolli",
        "Qué es Mamatlatolli y cómo reconoce la LSM.",
    ),
)


TEXTO_ACERCA = (
    "Mamatlatolli es un prototipo de escritorio para reconocer Lengua de Señas "
    "Mexicana (LSM) con la cámara del equipo.\n\n"
    "Fase 1 — ventana, video en vivo y detección de manos.\n"
    "Fase 2a — plantillas estáticas (landmarks normalizados) y filtro de estabilidad.\n"
    "Fase 2b — menú principal y letras con movimiento comparadas con DTW.\n"
    "Fase 3 — Abecedario y Vocabulario como modos separados; categoría letra/palabra.\n"
    "Fase 4 — Vocabulario con pose corporal y rostro en vivo.\n\n"
    "El uso diario se divide en «Abecedario» (letras) y «Vocabulario» (palabras). "
    "Capturar plantillas y la biblioteca organizan el banco de señas: elige Letra o "
    "Palabra al guardar, y filtra igual al revisar.\n\n"
    "Mini juego toma una letra estática que ya capturaste y da 5 segundos para "
    "señarla. Si la seña estable llega en menos de 1 segundo suma 1000 puntos; "
    "entre 1 y 3 segundos, 700; de 3 a menos de 5, 500. Luego sale otra letra. "
    "Si se acaba el tiempo, o la seña estable es otra letra, la partida termina "
    "y solo se guarda el récord (la puntuación más alta) en datos/config.json. "
    "No hay una lista de palabras ni plantillas precargadas.\n\n"
    "En Biblioteca puedes exportar las señas a un archivo e importarlas en "
    "otra computadora, sin volver a capturarlas. Si una seña ya existe, "
    "Mamatlatolli pregunta si la reemplazas o si solo agregas las nuevas.\n\n"
    "Las letras estáticas (A, B, C…) se comparan fotograma a fotograma. Las que "
    "llevan trayectoria (J, Ñ, Z…) se graban como secuencia y se reconocen con "
    "Dynamic Time Warping. Si la mano se mueve con claridad durante ~0,4–0,8 s, "
    "Mamatlatolli usa las plantillas dinámicas; si permanece estable, usa las "
    "estáticas. También puedes forzar el modo dinámico con «Seña con movimiento» "
    "o manteniendo Space. Lo mismo aplica a las palabras dinámicas.\n\n"
    "En Vocabulario, cada fotograma puede guardar la pose (MediaPipe Pose, 33 puntos) "
    "y el rostro (Face Mesh, 478 puntos), además de la mano. Esas señales entran al "
    "matching estático y al DTW. Abecedario sigue con solo las manos. Si el modelo "
    "no carga o la cámara no ve el cuerpo, la palabra se reconoce con la mano.\n\n"
    "Proyecto estudiantil — Instituto Tecnológico de San Juan del Río.\n"
    "Esc, o el botón ← Menú, vuelven al menú. En el menú, Esc o Q cierran "
    "Mamatlatolli. Q no cierra si estás escribiendo."
)


def etiquetas_menu() -> list[str]:
    return [etiqueta for _destino, etiqueta, _desc in OPCIONES_MENU]


def categoria_de_destino(destino: str) -> str:
    """Categoría de plantillas que usa una pantalla de reconocimiento."""
    if destino == DESTINO_VOCABULARIO:
        return CATEGORIA_PALABRA
    return CATEGORIA_LETRA


@dataclass
class Navegador:
    """Estado de pantalla: el menú es el centro; cada opción va y vuelve."""

    actual: str = DESTINO_MENU

    def ir(self, destino: str) -> str:
        if destino not in DESTINOS_VALIDOS:
            raise ValueError(f"Pantalla desconocida: {destino}")
        self.actual = destino
        return self.actual

    def volver(self) -> str:
        self.actual = DESTINO_MENU
        return self.actual

    def en_menu(self) -> bool:
        return self.actual == DESTINO_MENU

    def usa_video(self) -> bool:
        return self.actual in {
            DESTINO_ABECEDARIO,
            DESTINO_VOCABULARIO,
            DESTINO_PRACTICA,
            DESTINO_CAPTURA,
            DESTINO_DEMO,
        }

    def usa_demostracion(self) -> bool:
        return self.actual == DESTINO_DEMO

    def accion_escape(self) -> str:
        """Esc hace lo mismo que ← Menú: volver, o salir si ya estás en el menú."""
        return "salir" if self.en_menu() else "volver"
