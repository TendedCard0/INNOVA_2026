"""Tema visual de Mamatlatolli: paleta tríadica y marca.

Esquema de color (rueda tríadica): naranja, lima y azul real / índigo.
Los fondos son claros; los acentos van en iconos, bordes y botones.
El logo definitivo aún no existe: si hay ``assets/logo.png`` se usa;
si no, un marco placeholder fácil de sustituir.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Apariencia
# ---------------------------------------------------------------------------

MODO_APARIENCIA = "light"

# Superficies (claras, tipo material / Google).
COLOR_FONDO = "#F4F6FB"
COLOR_FONDO_ALT = "#EEF1F8"
COLOR_TARJETA = "#FFFFFF"
COLOR_TARJETA_HOVER = "#FFFBF4"
COLOR_TARJETA_PRESION = "#F3F0EA"
COLOR_BORDE = "#E4E8F2"
COLOR_BORDE_HOVER = "#C9D0E3"
COLOR_PANEL = "#FFFFFF"
COLOR_CAMPO = "#F3F5FA"
COLOR_VIDEO = "#1B2030"

# Texto
COLOR_TEXTO = "#1C2233"
COLOR_TEXTO_MUDO = "#5C6578"
COLOR_TEXTO_INVERSO = "#FFFFFF"

# Tríada principal
COLOR_NARANJA = "#F08C28"
COLOR_NARANJA_SUAVE = "#FFF3E4"
COLOR_NARANJA_HOVER = "#D97816"

COLOR_LIMA = "#7CB342"
COLOR_LIMA_SUAVE = "#EEF7E4"
COLOR_LIMA_HOVER = "#689F38"

COLOR_INDIGO = "#3F51C9"
COLOR_INDIGO_SUAVE = "#E8EBFA"
COLOR_INDIGO_HOVER = "#3242B0"

# Semántica (mapeada a la tríada para no inventar una cuarta familia)
COLOR_ACENTO = COLOR_INDIGO
COLOR_ACENTO_SUAVE = COLOR_INDIGO_SUAVE
COLOR_ACENTO_HOVER = COLOR_INDIGO_HOVER
COLOR_AVISO = COLOR_NARANJA
COLOR_OK = COLOR_LIMA
COLOR_ERROR = "#E24B3B"
COLOR_ERROR_SUAVE = "#FDECEA"
COLOR_ERROR_HOVER = "#C63D30"

TRIDADA: tuple[str, str, str] = (COLOR_NARANJA, COLOR_LIMA, COLOR_INDIGO)
TRIDADA_SUAVE: tuple[str, str, str] = (
    COLOR_NARANJA_SUAVE,
    COLOR_LIMA_SUAVE,
    COLOR_INDIGO_SUAVE,
)

# Overlay de cámara (OpenCV usa BGR).
BGR_NARANJA = (40, 140, 240)
BGR_LIMA = (66, 179, 124)
BGR_INDIGO = (201, 81, 63)
BGR_CONEXION = BGR_LIMA
BGR_LANDMARK = BGR_NARANJA
BGR_CAJA = BGR_INDIGO
BGR_TEXTO = (244, 238, 232)
BGR_SOMBRA = (22, 24, 28)

RUTA_ASSETS = Path(__file__).resolve().parent.parent / "assets"
RUTA_LOGO = RUTA_ASSETS / "logo.png"

_ICONOS_MENU = (
    "reconocer",
    "capturar",
    "biblioteca",
    "configurar",
    "demo",
    "acerca",
)


def hex_a_rgb(color: str) -> tuple[int, int, int]:
    valor = color.lstrip("#")
    return int(valor[0:2], 16), int(valor[2:4], 16), int(valor[4:6], 16)


def acento_de_indice(indice: int) -> str:
    return TRIDADA[indice % 3]


def acento_suave_de_indice(indice: int) -> str:
    return TRIDADA_SUAVE[indice % 3]


def aplicar_tema() -> None:
    """Aplica el modo claro de CustomTkinter. Los colores concretos van por widget."""
    import customtkinter as ctk

    ctk.set_appearance_mode(MODO_APARIENCIA)
    ctk.set_default_color_theme("blue")


def resolver_logo(base: Path | None = None) -> Optional[Path]:
    """Devuelve ``assets/logo.png`` si existe; si no, ``None`` (usar placeholder)."""
    candidato = (base if base is not None else RUTA_ASSETS) / "logo.png"
    return candidato if candidato.is_file() else None


def imagen_logo(lado: int = 96, base: Path | None = None) -> tuple[Image.Image, bool]:
    """Imagen cuadrada del logo real o del marco placeholder.

    El segundo valor indica si se cargó un archivo (True) o el placeholder (False).
    """
    ruta = resolver_logo(base)
    if ruta is not None:
        return _ajustar_logo(Image.open(ruta).convert("RGBA"), lado), True
    return _dibujar_placeholder_logo(lado), False


def icono_menu(nombre: str, acento: str, lado: int = 56) -> Image.Image:
    """Icono geométrico para una tarjeta del menú (fondo suave + trazo del acento)."""
    suave = {
        COLOR_NARANJA: COLOR_NARANJA_SUAVE,
        COLOR_LIMA: COLOR_LIMA_SUAVE,
        COLOR_INDIGO: COLOR_INDIGO_SUAVE,
    }.get(acento, COLOR_INDIGO_SUAVE)
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    draw = ImageDraw.Draw(lienzo)
    radio = max(14, lado // 4)
    draw.rounded_rectangle((0, 0, lado - 1, lado - 1), radius=radio, fill=suave)
    margen = lado * 0.22
    caja = (margen, margen, lado - margen, lado - margen)
    _dibujar_glifo(draw, nombre, caja, acento)
    return lienzo


def nombres_iconos_menu() -> tuple[str, ...]:
    return _ICONOS_MENU


def _ajustar_logo(original: Image.Image, lado: int) -> Image.Image:
    copiada = original.copy()
    copiada.thumbnail((lado, lado), Image.Resampling.LANCZOS)
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    x = (lado - copiada.width) // 2
    y = (lado - copiada.height) // 2
    lienzo.paste(copiada, (x, y), copiada)
    return lienzo


def _dibujar_placeholder_logo(lado: int) -> Image.Image:
    """Marco redondeado con tres puntos tríadicos (fácil de sustituir por logo.png)."""
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    draw = ImageDraw.Draw(lienzo)
    draw.rounded_rectangle(
        (1, 1, lado - 2, lado - 2),
        radius=max(18, lado // 5),
        fill=hex_a_rgb(COLOR_TARJETA) + (255,),
        outline=hex_a_rgb(COLOR_BORDE) + (255,),
        width=max(2, lado // 48),
    )
    # Anillo interior suave
    inset = lado * 0.12
    draw.ellipse(
        (inset, inset, lado - inset, lado - inset),
        outline=hex_a_rgb(COLOR_INDIGO_SUAVE) + (255,),
        width=max(2, lado // 32),
    )
    cx, cy = lado / 2, lado / 2
    radio_orbita = lado * 0.22
    radio_punto = max(5, lado * 0.09)
    # Tríada en triángulo (misma geometría que la rueda de color de referencia).
    puntos = (
        (cx, cy - radio_orbita),
        (cx - radio_orbita * 0.87, cy + radio_orbita * 0.5),
        (cx + radio_orbita * 0.87, cy + radio_orbita * 0.5),
    )
    for (px, py), color in zip(puntos, TRIDADA):
        draw.ellipse(
            (px - radio_punto, py - radio_punto, px + radio_punto, py + radio_punto),
            fill=hex_a_rgb(color) + (255,),
        )
    return lienzo


def _dibujar_glifo(
    draw: ImageDraw.ImageDraw,
    nombre: str,
    caja: tuple[float, float, float, float],
    acento: str,
) -> None:
    x0, y0, x1, y1 = caja
    w, h = x1 - x0, y1 - y0
    color = hex_a_rgb(acento) + (255,)
    grosor = max(3, int(min(w, h) * 0.10))

    if nombre == "reconocer":
        # Palmita: palma + cuatro dedos.
        palma = (x0 + w * 0.18, y0 + h * 0.42, x1 - w * 0.18, y1 - h * 0.05)
        draw.rounded_rectangle(palma, radius=w * 0.18, fill=color)
        anchos = (0.12, 0.34, 0.56, 0.78)
        altos = (0.08, 0.00, 0.10, 0.18)
        dedo_w = w * 0.16
        for ax, ay in zip(anchos, altos):
            dx = x0 + w * ax
            dy = y0 + h * ay
            draw.rounded_rectangle(
                (dx, dy, dx + dedo_w, y0 + h * 0.55),
                radius=dedo_w / 2,
                fill=color,
            )
        return

    if nombre == "capturar":
        # Cámara + cruz (guardar plantilla).
        cuerpo = (x0, y0 + h * 0.28, x1, y1)
        draw.rounded_rectangle(cuerpo, radius=w * 0.14, outline=color, width=grosor)
        draw.ellipse(
            (x0 + w * 0.28, y0 + h * 0.40, x0 + w * 0.72, y0 + h * 0.88),
            outline=color,
            width=grosor,
        )
        visor = (x0 + w * 0.18, y0 + h * 0.10, x0 + w * 0.46, y0 + h * 0.32)
        draw.rounded_rectangle(visor, radius=w * 0.08, fill=color)
        return

    if nombre == "biblioteca":
        # Dos tarjetas apiladas (la del frente rellena).
        d = w * 0.16
        draw.rounded_rectangle(
            (x0 + d, y0, x1, y1 - d),
            radius=w * 0.14,
            outline=color,
            width=grosor,
        )
        draw.rounded_rectangle(
            (x0, y0 + d, x1 - d, y1),
            radius=w * 0.14,
            fill=color,
        )
        return

    if nombre == "configurar":
        # Tres sliders (más «Google» que un engrane).
        for i, rel in enumerate((0.18, 0.50, 0.82)):
            y = y0 + h * rel
            draw.line((x0, y, x1, y), fill=color, width=grosor)
            kx = x0 + w * (0.28 + 0.22 * i)
            r = grosor * 1.15
            draw.ellipse((kx - r, y - r, kx + r, y + r), fill=color)
        return

    if nombre == "demo":
        # Triángulo de reproducción.
        pad = w * 0.08
        draw.polygon(
            [
                (x0 + pad, y0 + pad),
                (x1 - pad * 0.2, y0 + h / 2),
                (x0 + pad, y1 - pad),
            ],
            fill=color,
        )
        return

    # acerca: círculo con «i»
    draw.ellipse((x0, y0, x1, y1), outline=color, width=grosor)
    cx = (x0 + x1) / 2
    r = grosor * 0.7
    draw.ellipse((cx - r, y0 + h * 0.18, cx + r, y0 + h * 0.18 + 2 * r), fill=color)
    draw.line(
        (cx, y0 + h * 0.42, cx, y1 - h * 0.18),
        fill=color,
        width=grosor,
    )
