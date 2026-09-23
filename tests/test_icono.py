"""Recorte de la marca M + mano e iconos de la ventana de Mamatlatolli."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from innova.tema import (
    RUTA_ICONO_ICO,
    RUTA_ICONO_PNG,
    RUTA_LOGO,
    TAMANOS_ICONO,
    guardar_iconos,
    imagen_icono_app,
    recorte_marca,
    resolver_icono_ico,
    resolver_icono_png,
)


def _logo_sintetico() -> Image.Image:
    """Marca casi cuadrada arriba y una franja de texto debajo, separadas."""
    lienzo = Image.new("RGBA", (240, 180), (0, 0, 0, 0))
    draw = ImageDraw.Draw(lienzo)
    draw.rounded_rectangle((70, 8, 150, 88), radius=12, fill=(20, 60, 160, 255))
    draw.rectangle((10, 120, 230, 145), fill=(230, 120, 30, 255))
    return lienzo


class TestRecorteMarca(unittest.TestCase):
    def test_separa_la_marca_del_texto(self) -> None:
        marca = recorte_marca(_logo_sintetico())
        self.assertEqual(marca.size[0], marca.size[1])
        self.assertEqual(marca.getpixel((0, 0))[3], 0)
        centro = marca.getpixel((marca.size[0] // 2, marca.size[1] // 2))
        self.assertGreater(centro[2], centro[0])
        self.assertEqual(centro[3], 255)
        naranjas = sum(1 for pixel in marca.getdata() if pixel[0] > 180 and pixel[1] > 80 and pixel[2] < 80)
        self.assertEqual(naranjas, 0)

    def test_una_sola_pieza_se_encuadra(self) -> None:
        lienzo = Image.new("RGBA", (120, 40), (0, 0, 0, 0))
        ImageDraw.Draw(lienzo).rectangle((4, 8, 100, 32), fill=(12, 40, 90, 255))
        marca = recorte_marca(lienzo, margen=0.0)
        self.assertEqual(marca.size[0], marca.size[1])
        self.assertGreater(marca.getpixel((marca.size[0] // 2, marca.size[1] // 2))[3], 0)

    def test_imagen_vacia_sigue_siendo_cuadrada(self) -> None:
        vacia = Image.new("RGBA", (32, 48), (0, 0, 0, 0))
        marca = recorte_marca(vacia)
        self.assertEqual(marca.size[0], marca.size[1])
        self.assertEqual(marca.getchannel("A").getbbox(), None)

    def test_logo_oficial_no_arrastra_el_wordmark(self) -> None:
        with Image.open(RUTA_LOGO) as logo:
            marca = recorte_marca(logo)
            self.assertEqual(marca.size[0], marca.size[1])
            self.assertLess(marca.size[0], logo.size[0])
            self.assertGreater(marca.size[0], 400)
            bbox = marca.getchannel("A").getbbox()
            self.assertIsNotNone(bbox)
            assert bbox is not None
            ancho = bbox[2] - bbox[0]
            alto = bbox[3] - bbox[1]
            self.assertLess(ancho / alto, 1.6)
            self.assertGreater(ancho / alto, 0.8)


class TestGuardarIconos(unittest.TestCase):
    def test_png_e_ico_multitamano(self) -> None:
        marca = recorte_marca(_logo_sintetico())
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            png, ico = guardar_iconos(marca, base)
            self.assertEqual(png.name, "icono.png")
            self.assertEqual(ico.name, "icono.ico")
            with Image.open(png) as exportada:
                self.assertEqual(exportada.format, "PNG")
                self.assertEqual(exportada.mode, "RGBA")
                self.assertEqual(exportada.size, (512, 512))
                self.assertEqual(exportada.getpixel((0, 0))[3], 0)
            with Image.open(ico) as icono:
                self.assertEqual(icono.format, "ICO")
                tamanos = set(icono.info["sizes"])
            for lado in TAMANOS_ICONO:
                self.assertIn((lado, lado), tamanos)
            self.assertEqual(resolver_icono_png(base), png)
            self.assertEqual(resolver_icono_ico(base), ico)
            cargada = imagen_icono_app(base)
            self.assertIsNotNone(cargada)
            assert cargada is not None
            self.assertEqual(cargada.size, (512, 512))

    def test_sin_png_recorta_el_logo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _logo_sintetico().save(base / "logo.png")
            self.assertIsNone(resolver_icono_png(base))
            icono = imagen_icono_app(base)
            self.assertIsNotNone(icono)
            assert icono is not None
            self.assertEqual(icono.size[0], icono.size[1])
            naranjas = sum(1 for pixel in icono.getdata() if pixel[0] > 180 and pixel[1] > 80 and pixel[2] < 80)
            self.assertEqual(naranjas, 0)

    def test_assets_oficiales(self) -> None:
        self.assertTrue(RUTA_ICONO_PNG.is_file())
        self.assertTrue(RUTA_ICONO_ICO.is_file())
        with Image.open(RUTA_LOGO) as logo:
            esperado = recorte_marca(logo)
        exportable = esperado.resize((512, 512), Image.Resampling.LANCZOS)
        with Image.open(RUTA_ICONO_PNG) as png:
            self.assertEqual(png.format, "PNG")
            self.assertEqual(png.size, (512, 512))
            self.assertEqual(list(png.getdata()), list(exportable.getdata()))
        with Image.open(RUTA_ICONO_ICO) as icono:
            self.assertEqual(icono.format, "ICO")
            tamanos = set(icono.info["sizes"])
            for lado in (16, 24, 32, 48, 64, 128, 256):
                self.assertIn((lado, lado), tamanos)
            self.assertEqual(icono.getpixel((0, 0))[3], 0)
            centro = icono.getpixel((icono.size[0] // 2, icono.size[1] // 2))
            self.assertGreater(centro[3], 200)


def _tk_disponible() -> bool:
    if not os.environ.get("DISPLAY"):
        return False
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(_tk_disponible(), "requiere display gráfico y tkinter")
class TestIconoEnVentana(unittest.TestCase):
    def test_la_ventana_toma_el_icono(self) -> None:
        import customtkinter as ctk

        from innova.ui import aplicar_icono_ventana

        raiz = ctk.CTk()
        raiz.withdraw()
        try:
            aplicar_icono_ventana(raiz)
            self.assertTrue(raiz._icono_aplicado)
            self.assertGreaterEqual(len(raiz._iconos_mamatlatolli), 4)
        finally:
            raiz.destroy()


if __name__ == "__main__":
    unittest.main()
