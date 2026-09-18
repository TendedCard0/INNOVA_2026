"""Menú principal de Mamatlatolli: destinos y navegación (sin Tk)."""

from __future__ import annotations

from dataclasses import dataclass

DESTINO_MENU = "menu"
DESTINO_RECONOCIMIENTO = "reconocimiento"
DESTINO_CAPTURA = "captura"
DESTINO_BIBLIOTECA = "biblioteca"
DESTINO_CONFIGURACION = "configuracion"
DESTINO_DEMO = "demo"
DESTINO_ACERCA = "acerca"

DESTINOS_VALIDOS = frozenset(
    {
        DESTINO_MENU,
        DESTINO_RECONOCIMIENTO,
        DESTINO_CAPTURA,
        DESTINO_BIBLIOTECA,
        DESTINO_CONFIGURACION,
        DESTINO_DEMO,
        DESTINO_ACERCA,
    }
)

# (id, etiqueta visible, descripción corta)
OPCIONES_MENU: tuple[tuple[str, str, str], ...] = (
    (
        DESTINO_RECONOCIMIENTO,
        "Iniciar reconocimiento",
        "Cámara en vivo: letras estáticas y con movimiento (DTW).",
    ),
    (
        DESTINO_CAPTURA,
        "Capturar plantillas",
        "Guardar una seña estática o una trayectoria dinámica.",
    ),
    (
        DESTINO_BIBLIOTECA,
        "Biblioteca de señas",
        "Listar, probar o borrar las plantillas guardadas.",
    ),
    (
        DESTINO_CONFIGURACION,
        "Configuración",
        "Confianza, estabilidad y sensibilidad al movimiento.",
    ),
    (
        DESTINO_DEMO,
        "Modo demostración",
        "Misma vista de reconocimiento, sin cámara física.",
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
    "Fase 2b — menú principal y letras con movimiento comparadas con DTW.\n\n"
    "El uso diario es «Iniciar reconocimiento». Capturar plantillas y la "
    "biblioteca sirven para organizar el banco de señas, no como una segunda app.\n\n"
    "Las letras estáticas (A, B, C…) se comparan fotograma a fotograma. Las que "
    "llevan trayectoria (J, Ñ, Z…) se graban como secuencia y se reconocen con "
    "Dynamic Time Warping. Si la mano se mueve con claridad durante ~0,4–0,8 s, "
    "Mamatlatolli usa las plantillas dinámicas; si permanece estable, usa las "
    "estáticas. También puedes forzar el modo dinámico con «Seña con movimiento» "
    "o manteniendo Space.\n\n"
    "Pose y rostro quedan en null hasta el vocabulario completo.\n\n"
    "Proyecto estudiantil — Instituto Tecnológico de San Juan del Río.\n"
    "Esc o Q cierran la aplicación."
)


def etiquetas_menu() -> list[str]:
    return [etiqueta for _destino, etiqueta, _desc in OPCIONES_MENU]


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
            DESTINO_RECONOCIMIENTO,
            DESTINO_CAPTURA,
            DESTINO_DEMO,
        }

    def usa_demostracion(self) -> bool:
        return self.actual == DESTINO_DEMO
