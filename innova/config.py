"""Constantes y textos visibles de Mamatlatolli (español de México)."""

from __future__ import annotations

from pathlib import Path

from innova.tema import (  # noqa: F401 — reexportados para overlay y código existente
    BGR_CAJA,
    BGR_CONEXION,
    BGR_LANDMARK,
    BGR_SOMBRA,
    BGR_TEXTO,
    COLOR_ACENTO,
    COLOR_ACENTO_HOVER,
    COLOR_ACENTO_SUAVE,
    COLOR_AVISO,
    COLOR_ERROR,
    COLOR_FONDO,
    COLOR_PANEL,
    COLOR_TEXTO,
    COLOR_TEXTO_MUDO,
)

# El paquete Python se llama `innova` (carpeta del repositorio), pero el
# nombre del software es Mamatlatolli.
NOMBRE_PRODUCTO = "Mamatlatolli"
TITULO_VENTANA = "Mamatlatolli — Reconocimiento de LSM"
SUBTITULO = "Lengua de Señas Mexicana · fase 2b (menú y señas dinámicas)"

ANCHO_VIDEO = 640
ALTO_VIDEO = 480
FPS_OBJETIVO = 30
MAX_MANOS = 2
MAX_LINEAS_TRANSCRIPCION = 10
INTERVALO_TRANSCRIPCION_S = 2.0

# Confianza mínima de MediaPipe para reportar una mano.
CONFIANZA_DETECCION = 0.6
CONFIANZA_SEGUIMIENTO = 0.5

ETIQUETA_SIN_DETECCION = "—"
ETIQUETA_DETECTANDO = "detectando…"

# Reconocimiento (fase 2a estática + 2b DTW).
VERSION_ESQUEMA = "1.0"
RUTA_PLANTILLAS = Path(__file__).resolve().parent.parent / "datos" / "plantillas"
RUTA_AJUSTES = Path(__file__).resolve().parent.parent / "datos" / "config.json"
METRICA_DISTANCIA = "euclidiana"  # "euclidiana" | "coseno"
# Distancia RMS a partir de la cual la confianza cae a 0.
SATURACION_DISTANCIA = 0.55
SATURACION_DTW = 0.50
UMBRAL_CONFIANZA_LETRA = 0.60
# Histéresis: umbral más bajo para *mantener* la letra ya comprometida.
UMBRAL_HISTERSIS = 0.40
FOTOGRAMAS_CONSECUTIVOS = 6
VOTOS_M = 5
VENTANA_K = 8
FOTOGRAMAS_PACIENCIA = 12

# Enrutado automático estático vs dinámico (ventana ~0.4–0.8 s).
VENTANA_MOVIMIENTO_S = 0.60
UMBRAL_MOVIMIENTO = 0.08
SENSIBILIDAD_MOVIMIENTO = 0.50
MAX_DURACION_DINAMICA_S = 1.80
MIN_FOTOGRAMAS_DINAMICO = 6
FOTOGRAMAS_REPOSO_DINAMICO = 5
COOLDOWN_DINAMICO_S = 0.45

MENSAJE_CAMARA_AUSENTE = (
    "No se encontró una cámara. Conecta una, revisa los permisos del sistema "
    "y pulsa «Reintentar cámara», o ejecuta: python app.py --demo"
)

# Los colores (hex y BGR) se definen en innova.tema y se reexportan arriba.
# aplicar_tema() actualiza estos nombres para quien lea innova.config en vivo.

# Pares de landmarks al estilo MediaPipe Hands (21 puntos).
CONEXIONES_MANO: tuple[tuple[int, int], ...] = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),  # pulgar
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),  # índice
    (0, 9),
    (9, 10),
    (10, 11),
    (11, 12),  # medio
    (0, 13),
    (13, 14),
    (14, 15),
    (15, 16),  # anular
    (0, 17),
    (17, 18),
    (18, 19),
    (19, 20),  # meñique
    (5, 9),
    (9, 13),
    (13, 17),  # palma
)
