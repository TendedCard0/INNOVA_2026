"""Tema visual de Mamatlatolli: paletas clara y oscura, y marca.

Esquema de color (rueda tríadica): naranja, lima y azul real / índigo.
Los acentos se ajustan para leerse sobre el fondo de cada modo.
El logo oficial vive en ``assets/logo.png``. Si el archivo no está,
se usa un marco placeholder fácil de sustituir.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw

from innova.rutas import ruta_assets

# Claves que comparten las dos paletas (superficies, texto, tríada y BGR).
TOKENS_REQUERIDOS: tuple[str, ...] = (
    "COLOR_FONDO",
    "COLOR_FONDO_ALT",
    "COLOR_TARJETA",
    "COLOR_TARJETA_HOVER",
    "COLOR_TARJETA_PRESION",
    "COLOR_BORDE",
    "COLOR_BORDE_HOVER",
    "COLOR_PANEL",
    "COLOR_CAMPO",
    "COLOR_VIDEO",
    "COLOR_TEXTO",
    "COLOR_TEXTO_MUDO",
    "COLOR_TEXTO_INVERSO",
    "COLOR_NARANJA",
    "COLOR_NARANJA_SUAVE",
    "COLOR_NARANJA_HOVER",
    "COLOR_LIMA",
    "COLOR_LIMA_SUAVE",
    "COLOR_LIMA_HOVER",
    "COLOR_INDIGO",
    "COLOR_INDIGO_SUAVE",
    "COLOR_INDIGO_HOVER",
    "COLOR_ACENTO",
    "COLOR_ACENTO_SUAVE",
    "COLOR_ACENTO_HOVER",
    "COLOR_AVISO",
    "COLOR_OK",
    "COLOR_ERROR",
    "COLOR_ERROR_SUAVE",
    "COLOR_ERROR_HOVER",
    "BGR_NARANJA",
    "BGR_LIMA",
    "BGR_INDIGO",
    "BGR_CONEXION",
    "BGR_LANDMARK",
    "BGR_CAJA",
    "BGR_TEXTO",
    "BGR_SOMBRA",
)

TEMA_CLARO = "claro"
TEMA_OSCURO = "oscuro"
ETIQUETA_TEMA_CLARO = "Modo claro"
ETIQUETA_TEMA_OSCURO = "Modo oscuro"

_ALIAS_TEMA = {
    "claro": TEMA_CLARO,
    "light": TEMA_CLARO,
    "oscuro": TEMA_OSCURO,
    "dark": TEMA_OSCURO,
}

# Reexportados por innova.config; se actualizan al aplicar el tema.
_REEXPORTADOS_CONFIG = (
    "BGR_CAJA",
    "BGR_CONEXION",
    "BGR_LANDMARK",
    "BGR_SOMBRA",
    "BGR_TEXTO",
    "COLOR_ACENTO",
    "COLOR_ACENTO_HOVER",
    "COLOR_ACENTO_SUAVE",
    "COLOR_AVISO",
    "COLOR_ERROR",
    "COLOR_FONDO",
    "COLOR_PANEL",
    "COLOR_TEXTO",
    "COLOR_TEXTO_MUDO",
)


def hex_a_rgb(color: str) -> tuple[int, int, int]:
    valor = color.lstrip("#")
    return int(valor[0:2], 16), int(valor[2:4], 16), int(valor[4:6], 16)


def hex_a_bgr(color: str) -> tuple[int, int, int]:
    rojo, verde, azul = hex_a_rgb(color)
    return (azul, verde, rojo)


def _completar(base: dict[str, Any]) -> dict[str, Any]:
    """Deriva acento semántico y BGR de la tríada. El resto viene en ``base``."""
    paleta = dict(base)
    paleta["COLOR_ACENTO"] = paleta["COLOR_INDIGO"]
    paleta["COLOR_ACENTO_SUAVE"] = paleta["COLOR_INDIGO_SUAVE"]
    paleta["COLOR_ACENTO_HOVER"] = paleta["COLOR_INDIGO_HOVER"]
    paleta["COLOR_AVISO"] = paleta["COLOR_NARANJA"]
    paleta["COLOR_OK"] = paleta["COLOR_LIMA"]
    paleta["BGR_NARANJA"] = hex_a_bgr(paleta["COLOR_NARANJA"])
    paleta["BGR_LIMA"] = hex_a_bgr(paleta["COLOR_LIMA"])
    paleta["BGR_INDIGO"] = hex_a_bgr(paleta["COLOR_INDIGO"])
    paleta["BGR_CONEXION"] = paleta["BGR_LIMA"]
    paleta["BGR_LANDMARK"] = paleta["BGR_NARANJA"]
    paleta["BGR_CAJA"] = paleta["BGR_INDIGO"]
    faltan = [token for token in TOKENS_REQUERIDOS if token not in paleta]
    if faltan:
        raise KeyError("Paleta incompleta: " + ", ".join(faltan))
    return paleta


# Superficies claras (tipo material). Acentos históricos de la fase 2b.
PALETA_CLARA: dict[str, Any] = _completar(
    {
        "COLOR_FONDO": "#F4F6FB",
        "COLOR_FONDO_ALT": "#EEF1F8",
        "COLOR_TARJETA": "#FFFFFF",
        "COLOR_TARJETA_HOVER": "#FFFBF4",
        "COLOR_TARJETA_PRESION": "#F3F0EA",
        "COLOR_BORDE": "#E4E8F2",
        "COLOR_BORDE_HOVER": "#C9D0E3",
        "COLOR_PANEL": "#FFFFFF",
        "COLOR_CAMPO": "#F3F5FA",
        "COLOR_VIDEO": "#1B2030",
        "COLOR_TEXTO": "#1C2233",
        "COLOR_TEXTO_MUDO": "#5C6578",
        "COLOR_TEXTO_INVERSO": "#FFFFFF",
        "COLOR_NARANJA": "#F08C28",
        "COLOR_NARANJA_SUAVE": "#FFF3E4",
        "COLOR_NARANJA_HOVER": "#D97816",
        "COLOR_LIMA": "#7CB342",
        "COLOR_LIMA_SUAVE": "#EEF7E4",
        "COLOR_LIMA_HOVER": "#689F38",
        "COLOR_INDIGO": "#3F51C9",
        "COLOR_INDIGO_SUAVE": "#E8EBFA",
        "COLOR_INDIGO_HOVER": "#3242B0",
        "COLOR_ERROR": "#E24B3B",
        "COLOR_ERROR_SUAVE": "#FDECEA",
        "COLOR_ERROR_HOVER": "#C63D30",
        # Overlay sobre el video (no sobre el cromo de la ventana).
        "BGR_TEXTO": (244, 238, 232),
        "BGR_SOMBRA": (22, 24, 28),
    }
)

# Fondos profundos; tríada más luminosa y texto oscuro sobre los botones de acento.
PALETA_OSCURA: dict[str, Any] = _completar(
    {
        "COLOR_FONDO": "#12151E",
        "COLOR_FONDO_ALT": "#181C28",
        "COLOR_TARJETA": "#1C2230",
        "COLOR_TARJETA_HOVER": "#262C3E",
        "COLOR_TARJETA_PRESION": "#141824",
        "COLOR_BORDE": "#343C52",
        "COLOR_BORDE_HOVER": "#4E5874",
        "COLOR_PANEL": "#1C2230",
        "COLOR_CAMPO": "#10141E",
        "COLOR_VIDEO": "#0C0F16",
        "COLOR_TEXTO": "#F4F6FB",
        "COLOR_TEXTO_MUDO": "#B4BDD2",
        "COLOR_TEXTO_INVERSO": "#141820",
        "COLOR_NARANJA": "#FF9F3C",
        "COLOR_NARANJA_SUAVE": "#6E4A24",
        "COLOR_NARANJA_HOVER": "#FFB45C",
        "COLOR_LIMA": "#A6D45A",
        "COLOR_LIMA_SUAVE": "#415A28",
        "COLOR_LIMA_HOVER": "#B8E070",
        "COLOR_INDIGO": "#8B97FF",
        "COLOR_INDIGO_SUAVE": "#3E4880",
        "COLOR_INDIGO_HOVER": "#B0B8FF",
        "COLOR_ERROR": "#FF6B5E",
        "COLOR_ERROR_SUAVE": "#5A2A26",
        "COLOR_ERROR_HOVER": "#FF8A80",
        "BGR_TEXTO": (244, 238, 232),
        "BGR_SOMBRA": (22, 24, 28),
    }
)


def _publicar(paleta: dict[str, Any]) -> None:
    """Copia la paleta a los nombres de módulo que leen las pantallas."""
    globales = globals()
    globales.update(paleta)
    globales["TRIDADA"] = (
        paleta["COLOR_NARANJA"],
        paleta["COLOR_LIMA"],
        paleta["COLOR_INDIGO"],
    )
    globales["TRIDADA_SUAVE"] = (
        paleta["COLOR_NARANJA_SUAVE"],
        paleta["COLOR_LIMA_SUAVE"],
        paleta["COLOR_INDIGO_SUAVE"],
    )


def _sincronizar_config() -> None:
    import sys

    config = sys.modules.get("innova.config")
    if config is None:
        return
    for nombre in _REEXPORTADOS_CONFIG:
        setattr(config, nombre, globals()[nombre])


def _aplicar_customtkinter(modo_apariencia: str) -> None:
    try:
        import customtkinter as ctk
    except Exception:  # noqa: BLE001 — las pruebas de paleta no exigen Tk
        return
    try:
        ctk.set_appearance_mode(modo_apariencia)
        ctk.set_default_color_theme("blue")
    except Exception:  # noqa: BLE001 — sin display el modo igual queda en los tokens
        return


_publicar(PALETA_CLARA)
MODO_ACTUAL = TEMA_CLARO
MODO_APARIENCIA = "light"


def normalizar_tema(valor: object) -> str:
    """Devuelve ``claro`` u ``oscuro``. Cualquier valor desconocido cae en claro."""
    if isinstance(valor, str):
        clave = valor.strip().lower()
        if clave in _ALIAS_TEMA:
            return _ALIAS_TEMA[clave]
    return TEMA_CLARO


def paleta_de(modo: str) -> dict[str, Any]:
    return PALETA_OSCURA if normalizar_tema(modo) == TEMA_OSCURO else PALETA_CLARA


def etiqueta_tema(modo: str) -> str:
    if normalizar_tema(modo) == TEMA_OSCURO:
        return ETIQUETA_TEMA_OSCURO
    return ETIQUETA_TEMA_CLARO


def modo_desde_etiqueta(etiqueta: str) -> str:
    texto = etiqueta.strip().lower()
    if "oscuro" in texto or texto == "dark":
        return TEMA_OSCURO
    if "claro" in texto or texto == "light":
        return TEMA_CLARO
    return normalizar_tema(etiqueta)


def aplicar_tema(modo: str | None = None) -> str:
    """Publica la paleta activa y el modo de CustomTkinter.

    Sin argumento reaplica el modo ya elegido. Devuelve ``claro`` u ``oscuro``.
    """
    global MODO_ACTUAL, MODO_APARIENCIA
    elegido = normalizar_tema(MODO_ACTUAL if modo is None else modo)
    _publicar(paleta_de(elegido))
    MODO_ACTUAL = elegido
    MODO_APARIENCIA = "dark" if elegido == TEMA_OSCURO else "light"
    _sincronizar_config()
    _aplicar_customtkinter(MODO_APARIENCIA)
    return MODO_ACTUAL


def acento_de_indice(indice: int) -> str:
    return TRIDADA[indice % 3]


def acento_suave_de_indice(indice: int) -> str:
    return TRIDADA_SUAVE[indice % 3]


RUTA_ASSETS = ruta_assets()
RUTA_LOGO = RUTA_ASSETS / "logo.png"
RUTA_ICONO_PNG = RUTA_ASSETS / "icono.png"
RUTA_ICONO_ICO = RUTA_ASSETS / "icono.ico"
# Tamaños que Windows usa en la barra de título, la barra de tareas y el explorador.
TAMANOS_ICONO: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)
_LADO_ICONO_PNG = 512

_ICONOS_MENU = (
    "abecedario",
    "vocabulario",
    "minijuego",
    "capturar",
    "biblioteca",
    "configurar",
    "demo",
    "acerca",
)


def resolver_logo(base: Path | None = None) -> Optional[Path]:
    """Devuelve ``assets/logo.png`` si existe; si no, ``None`` (usar placeholder)."""
    candidato = (base if base is not None else RUTA_ASSETS) / "logo.png"
    return candidato if candidato.is_file() else None


def imagen_logo(lado: int = 96, base: Path | None = None) -> tuple[Image.Image, bool]:
    """Imagen cuadrada del logo real o del marco placeholder.

    El segundo valor indica si se cargó un archivo (True) o el placeholder (False).
    El archivo se centra en el cuadrado sin deformarlo.
    """
    ruta = resolver_logo(base)
    if ruta is not None:
        return _ajustar_logo(Image.open(ruta).convert("RGBA"), lado), True
    return _dibujar_placeholder_logo(lado), False


def imagen_logo_encajada(
    ancho_max: int,
    alto_max: int,
    base: Path | None = None,
) -> tuple[Image.Image, bool]:
    """Logo a tamaño real de su proporción, dentro de la caja máxima.

    Si no hay archivo, devuelve el placeholder cuadrado de ``alto_max``.
    """
    ruta = resolver_logo(base)
    if ruta is None:
        return _dibujar_placeholder_logo(alto_max), False
    copia = Image.open(ruta).convert("RGBA")
    copia.thumbnail((max(1, ancho_max), max(1, alto_max)), Image.Resampling.LANCZOS)
    return copia, True


def resolver_icono_png(base: Path | None = None) -> Optional[Path]:
    """``assets/icono.png`` (marca M + mano) si el archivo existe."""
    candidato = (base if base is not None else RUTA_ASSETS) / "icono.png"
    return candidato if candidato.is_file() else None


def resolver_icono_ico(base: Path | None = None) -> Optional[Path]:
    """``assets/icono.ico`` multi-tamaño si el archivo existe."""
    candidato = (base if base is not None else RUTA_ASSETS) / "icono.ico"
    return candidato if candidato.is_file() else None


def recorte_marca(imagen: Image.Image, margen: float = 0.08) -> Image.Image:
    """Recorta la marca (la M con la mano) y la deja en un cuadrado transparente.

    El logo oficial apila la marca, el nombre y el eslogan. A 16–32 px el
    texto no se lee, así que el icono de la ventana usa solo el bloque de
    arriba cuando es más alto que el resto y casi cuadrado. Si la imagen
    ya es una sola pieza, se encuadra entera.
    """
    rgba = imagen.convert("RGBA")
    bandas = _bandas_contenido(rgba)
    if not bandas:
        return _enmarcar_cuadrado(rgba, margen=0.0)
    if len(bandas) >= 2 and _banda_superior_es_marca(bandas):
        pieza = rgba.crop(bandas[0])
    else:
        x0 = min(b[0] for b in bandas)
        y0 = min(b[1] for b in bandas)
        x1 = max(b[2] for b in bandas)
        y1 = max(b[3] for b in bandas)
        pieza = rgba.crop((x0, y0, x1, y1))
    return _enmarcar_cuadrado(pieza, margen=margen)


def imagen_icono_app(base: Path | None = None) -> Optional[Image.Image]:
    """Icono cuadrado de la app: ``icono.png`` o, si falta, el recorte del logo."""
    ruta = resolver_icono_png(base)
    if ruta is not None:
        return Image.open(ruta).convert("RGBA")
    logo = resolver_logo(base)
    if logo is None:
        return None
    return recorte_marca(Image.open(logo))


def guardar_iconos(marca: Image.Image, directorio: Path) -> tuple[Path, Path]:
    """Escribe ``icono.png`` (512 px) e ``icono.ico`` con los tamaños de Windows.

    El ``.ico`` va en mapa de bits de 32 bits para que Tk en Windows lo cargue
    con ``iconbitmap`` (barra de título y barra de tareas).
    """
    directorio.mkdir(parents=True, exist_ok=True)
    rgba = marca.convert("RGBA")
    if rgba.size[0] != rgba.size[1]:
        rgba = _enmarcar_cuadrado(rgba, margen=0.08)
    if min(rgba.size) < TAMANOS_ICONO[-1]:
        rgba = rgba.resize((TAMANOS_ICONO[-1], TAMANOS_ICONO[-1]), Image.Resampling.LANCZOS)
    png = directorio / "icono.png"
    ico = directorio / "icono.ico"
    exportable = rgba if rgba.size == (_LADO_ICONO_PNG, _LADO_ICONO_PNG) else rgba.resize(
        (_LADO_ICONO_PNG, _LADO_ICONO_PNG), Image.Resampling.LANCZOS
    )
    exportable.save(png, format="PNG")
    fuente = rgba if min(rgba.size) >= TAMANOS_ICONO[-1] else exportable
    fuente.save(
        ico,
        format="ICO",
        sizes=[(lado_icono, lado_icono) for lado_icono in TAMANOS_ICONO],
        bitmap_format="bmp",
    )
    return png, ico


def _bandas_contenido(imagen: Image.Image, umbral: int = 16) -> list[tuple[int, int, int, int]]:
    """Cajas ``(x0, y0, x1, y1)`` de cada bloque opaco, de arriba a abajo.

    Las coordenadas derechas e inferiores son exclusivas, como ``Image.crop``.
    Huecos verticales pequeños (antialiasing) no parten un mismo dibujo.
    """
    alpha = imagen.getchannel("A")
    ancho, alto = alpha.size
    if ancho == 0 or alto == 0:
        return []
    datos = alpha.tobytes()
    filas = [max(datos[y * ancho : (y + 1) * ancho]) > umbral for y in range(alto)]
    hueco_minimo = max(4, alto // 50)
    bandas_y: list[tuple[int, int]] = []
    inicio: int | None = None
    hueco = 0
    for y, activa in enumerate(filas):
        if activa:
            if inicio is None:
                inicio = y
            hueco = 0
            continue
        if inicio is None:
            continue
        hueco += 1
        if hueco >= hueco_minimo:
            bandas_y.append((inicio, y - hueco))
            inicio = None
            hueco = 0
    if inicio is not None:
        fin = alto - 1
        while fin > inicio and not filas[fin]:
            fin -= 1
        bandas_y.append((inicio, fin))

    cajas: list[tuple[int, int, int, int]] = []
    for y0, y1 in bandas_y:
        franja = alpha.crop((0, y0, ancho, y1 + 1))
        bbox = franja.point(lambda valor: 255 if valor > umbral else 0).getbbox()
        if bbox is None:
            continue
        cajas.append((bbox[0], y0, bbox[2], y1 + 1))
    return cajas


def _banda_superior_es_marca(bandas: list[tuple[int, int, int, int]]) -> bool:
    x0, y0, x1, y1 = bandas[0]
    alto = max(1, y1 - y0)
    ancho = max(1, x1 - x0)
    if ancho / alto > 1.75:
        return False
    alto_resto = sum(max(1, b[3] - b[1]) for b in bandas[1:])
    return alto >= alto_resto


def _enmarcar_cuadrado(imagen: Image.Image, margen: float) -> Image.Image:
    bbox = imagen.getchannel("A").getbbox()
    if bbox is None:
        lado = max(1, imagen.size[0], imagen.size[1])
        return Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    recorte = imagen.crop(bbox)
    ancho, alto = recorte.size
    lado_util = max(ancho, alto)
    margen_px = int(round(lado_util * max(0.0, margen)))
    lado = max(1, lado_util + 2 * margen_px)
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    lienzo.paste(recorte, ((lado - ancho) // 2, (lado - alto) // 2), recorte)
    return lienzo


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

    if nombre in {"abecedario", "reconocer"}:
        # Tres fichas de letra (A, B, C).
        fichas = (
            (0.00, 0.22, 0.42, 0.78),
            (0.30, 0.08, 0.72, 0.64),
            (0.58, 0.28, 1.00, 0.84),
        )
        for i, (ax0, ay0, ax1, ay1) in enumerate(fichas):
            caja_f = (x0 + w * ax0, y0 + h * ay0, x0 + w * ax1, y0 + h * ay1)
            if i == 2:
                draw.rounded_rectangle(caja_f, radius=w * 0.08, fill=color)
            else:
                draw.rounded_rectangle(caja_f, radius=w * 0.08, outline=color, width=grosor)
        return

    if nombre in {"practica", "minijuego"}:
        # Mando: cuerpo, cruceta y dos botones.
        cuerpo = (x0, y0 + h * 0.28, x1, y1 - h * 0.02)
        draw.rounded_rectangle(cuerpo, radius=w * 0.22, outline=color, width=grosor)
        hombrera = (x0 + w * 0.08, y0 + h * 0.12, x0 + w * 0.42, y0 + h * 0.36)
        draw.rounded_rectangle(hombrera, radius=w * 0.08, outline=color, width=max(2, grosor - 1))
        cx, cy = x0 + w * 0.34, y0 + h * 0.58
        brazo = w * 0.16
        draw.line((cx - brazo, cy, cx + brazo, cy), fill=color, width=grosor)
        draw.line((cx, cy - brazo, cx, cy + brazo * 0.85), fill=color, width=grosor)
        radio = w * 0.07
        for ox, oy in ((0.72, 0.46), (0.86, 0.62)):
            bx, by = x0 + w * ox, y0 + h * oy
            draw.ellipse((bx - radio, by - radio, bx + radio, by + radio), fill=color)
        return

    if nombre == "vocabulario":
        # Tarjeta de glosa con tres renglones.
        draw.rounded_rectangle((x0, y0, x1, y1), radius=w * 0.16, outline=color, width=grosor)
        for rel in (0.32, 0.50, 0.68):
            y = y0 + h * rel
            x_fin = x1 - w * (0.18 if rel != 0.68 else 0.34)
            draw.line((x0 + w * 0.18, y, x_fin, y), fill=color, width=grosor)
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
