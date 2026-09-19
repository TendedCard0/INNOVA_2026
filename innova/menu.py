"""Menú principal de Mamatlatolli: destinos y navegación (sin Tk)."""

from __future__ import annotations

from dataclasses import dataclass

from innova.esquema import CATEGORIA_LETRA, CATEGORIA_PALABRA

DESTINO_MENU = "menu"
DESTINO_ABECEDARIO = "abecedario"
DESTINO_VOCABULARIO = "vocabulario"
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
        "Letras LSM: pose estática y trayectoria con DTW.",
    ),
    (
        DESTINO_VOCABULARIO,
        "Vocabulario",
        "Palabras LSM: plantillas de palabra (pose y rostro listos).",
    ),
    (
        DESTINO_CAPTURA,
        "Capturar plantillas",
        "Guardar una seña de letra o de palabra (estática o dinámica).",
    ),
    (
        DESTINO_BIBLIOTECA,
        "Biblioteca de señas",
        "Listar, filtrar, probar o borrar las plantillas guardadas.",
    ),
    (
        DESTINO_CONFIGURACION,
        "Configuración",
        "Confianza, estabilidad y sensibilidad al movimiento.",
    ),
    (
        DESTINO_DEMO,
        "Modo demostración",
        "Vista de Abecedario sin cámara física.",
    ),
    (
        DESTINO_ACERCA,
        "Acerca de Mamatlatolli",
        "Qué es el prototipo, LSM y las fases del proyecto.",
    ),
)


TEXTO_ACERCA = (
    "Mamatlatolli es un prototipo de escritorio para reconocer Lengua de Señas "
    "Mexicana (LSM) con la cámara del equipo.\n\n"
    "Fase 1 — ventana, video en vivo y detección de manos.\n"
    "Fase 2a — plantillas estáticas (landmarks normalizados) y filtro de estabilidad.\n"
    "Fase 2b — menú principal y letras con movimiento comparadas con DTW.\n"
    "Fase 3 — Abecedario y Vocabulario como modos separados; categoría letra/palabra.\n\n"
    "El uso diario se divide en «Abecedario» (letras) y «Vocabulario» (palabras). "
    "Capturar plantillas y la biblioteca organizan el banco de señas: elige Letra o "
    "Palabra al guardar, y filtra igual al revisar.\n\n"
    "Las letras estáticas (A, B, C…) se comparan fotograma a fotograma. Las que "
    "llevan trayectoria (J, Ñ, Z…) se graban como secuencia y se reconocen con "
    "Dynamic Time Warping. Si la mano se mueve con claridad durante ~0,4–0,8 s, "
    "Mamatlatolli usa las plantillas dinámicas; si permanece estable, usa las "
    "estáticas. También puedes forzar el modo dinámico con «Seña con movimiento» "
    "o manteniendo Space. Lo mismo aplica a las palabras dinámicas.\n\n"
    "Pose y rostro ya caben en el esquema. Los ganchos están en innova/cuerpo.py "
    "y hoy devuelven null; cuando se activen MediaPipe Pose y Face Mesh, la UI "
    "no tiene que reescribirse.\n\n"
    "Proyecto estudiantil — Instituto Tecnológico de San Juan del Río.\n"
    "Esc o Q cierran la aplicación."
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
            DESTINO_CAPTURA,
            DESTINO_DEMO,
        }

    def usa_demostracion(self) -> bool:
        return self.actual == DESTINO_DEMO
