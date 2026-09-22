"""Paleta tríadica, logo placeholder y consistencia del menú visual."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from innova.menu import OPCIONES_MENU
from innova.tema import (
    COLOR_FONDO,
    COLOR_INDIGO,
    COLOR_LIMA,
    COLOR_NARANJA,
    COLOR_TEXTO,
    TRIDADA,
    acento_de_indice,
    hex_a_rgb,
    icono_menu,
    imagen_logo,
    nombres_iconos_menu,
    resolver_logo,
)


class TestPaleta(unittest.TestCase):
    def test_tridada_naranja_lima_indigo(self) -> None:
        self.assertEqual(TRIDADA, (COLOR_NARANJA, COLOR_LIMA, COLOR_INDIGO))
        self.assertEqual(len(set(TRIDADA)), 3)

    def test_fondo_claro_y_texto_oscuro(self) -> None:
        rf, gf, bf = hex_a_rgb(COLOR_FONDO)
        rt, gt, bt = hex_a_rgb(COLOR_TEXTO)
        self.assertGreater((rf + gf + bf) / 3, 180)
        self.assertLess((rt + gt + bt) / 3, 80)

    def test_acentos_rotan_en_tres(self) -> None:
        self.assertEqual(acento_de_indice(0), COLOR_NARANJA)
        self.assertEqual(acento_de_indice(1), COLOR_LIMA)
        self.assertEqual(acento_de_indice(2), COLOR_INDIGO)
        self.assertEqual(acento_de_indice(3), COLOR_NARANJA)

    def test_config_reexporta_el_tema(self) -> None:
        from innova import config, tema

        self.assertEqual(config.COLOR_FONDO, tema.COLOR_FONDO)
        self.assertEqual(config.COLOR_ACENTO, tema.COLOR_INDIGO)
        self.assertEqual(config.BGR_CAJA, tema.BGR_INDIGO)


class TestLogoEIconos(unittest.TestCase):
    def test_sin_png_usa_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.assertIsNone(resolver_logo(base))
            imagen, es_real = imagen_logo(64, base=base)
            self.assertFalse(es_real)
            self.assertEqual(imagen.size, (64, 64))

    def test_logo_png_se_carga_si_existe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            original = Image.new("RGB", (40, 20), (255, 140, 40))
            original.save(base / "logo.png")
            self.assertEqual(resolver_logo(base), base / "logo.png")
            imagen, es_real = imagen_logo(80, base=base)
            self.assertTrue(es_real)
            self.assertEqual(imagen.size, (80, 80))

    def test_iconos_del_menu_cuadrados(self) -> None:
        nombres = nombres_iconos_menu()
        self.assertEqual(len(nombres), len(OPCIONES_MENU))
        for indice, nombre in enumerate(nombres):
            icono = icono_menu(nombre, acento_de_indice(indice), lado=48)
            self.assertEqual(icono.size, (48, 48))


def _tk_disponible() -> bool:
    if not os.environ.get("DISPLAY"):
        return False
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(_tk_disponible(), "requiere display gráfico y tkinter")
class TestPantallaMenuTk(unittest.TestCase):
    def test_menu_construye_siete_tarjetas_y_navega(self) -> None:
        import customtkinter as ctk

        from innova.pantallas import PantallaMenu
        from innova.tema import aplicar_tema

        aplicar_tema()
        raiz = ctk.CTk()
        raiz.withdraw()
        destinos: list[str] = []
        try:
            pantalla = PantallaMenu(raiz, on_ir=destinos.append)
            self.assertEqual(len(pantalla._tarjetas), 7)
            etiquetas = [OPCIONES_MENU[i][1] for i in range(7)]
            self.assertEqual(etiquetas[0], "Abecedario")
            self.assertEqual(etiquetas[1], "Vocabulario")
            self.assertNotIn("Iniciar reconocimiento", etiquetas)
            pantalla._tarjetas[0]._on_ir(pantalla._tarjetas[0]._destino)
            self.assertEqual(destinos, ["abecedario"])
            pantalla._tarjetas[1]._on_ir(pantalla._tarjetas[1]._destino)
            self.assertEqual(destinos[-1], "vocabulario")
            pantalla._tarjetas[6]._on_ir(pantalla._tarjetas[6]._destino)
            self.assertEqual(destinos[-1], "acerca")
        finally:
            raiz.destroy()


if __name__ == "__main__":
    unittest.main()
