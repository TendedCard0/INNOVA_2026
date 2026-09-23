"""Paleta tríadica, logo placeholder y preferencia claro/oscuro."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from PIL import Image

from innova.ajustes import Ajustes, cargar_ajustes, guardar_ajustes, guardar_tema
from innova.menu import OPCIONES_MENU
from innova.tema import (
    COLOR_FONDO,
    COLOR_INDIGO,
    COLOR_LIMA,
    COLOR_NARANJA,
    COLOR_TEXTO,
    ETIQUETA_TEMA_CLARO,
    ETIQUETA_TEMA_OSCURO,
    PALETA_CLARA,
    PALETA_OSCURA,
    TOKENS_REQUERIDOS,
    TRIDADA,
    acento_de_indice,
    etiqueta_tema,
    hex_a_bgr,
    hex_a_rgb,
    icono_menu,
    imagen_logo,
    modo_desde_etiqueta,
    nombres_iconos_menu,
    normalizar_tema,
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

    def test_logo_oficial_en_assets(self) -> None:
        from innova.tema import RUTA_LOGO

        self.assertTrue(RUTA_LOGO.is_file())
        with Image.open(RUTA_LOGO) as original:
            self.assertEqual(original.format, "PNG")
            self.assertEqual(original.mode, "RGBA")
            self.assertGreater(min(original.size), 512)
            self.assertEqual(original.getchannel("A").getextrema()[0], 0)
        imagen, es_real = imagen_logo(96)
        self.assertTrue(es_real)
        self.assertEqual(imagen.size, (96, 96))
        self.assertLess(imagen.getchannel("A").getextrema()[0], 255)

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
    def test_menu_construye_tarjetas_y_navega(self) -> None:
        import customtkinter as ctk

        from innova.pantallas import MarcaMamatlatolli, PantallaMenu
        from innova.tema import aplicar_tema

        aplicar_tema("claro")
        raiz = ctk.CTk()
        raiz.withdraw()
        destinos: list[str] = []
        try:
            pantalla = PantallaMenu(raiz, on_ir=destinos.append)
            self.assertEqual(len(pantalla._tarjetas), 8)
            marca = next(
                w
                for w in pantalla.winfo_children()[0].winfo_children()
                if w.__class__.__name__ == "MarcaMamatlatolli"
            )
            self.assertTrue(marca._es_logo_archivo)
            ancho, alto = marca._logo_ctk._size
            self.assertLessEqual(ancho, MarcaMamatlatolli._ANCHO_LOGO)
            self.assertLessEqual(alto, MarcaMamatlatolli._ALTO_LOGO)
            self.assertGreater(ancho, alto)
            from innova.config import NOMBRE_PRODUCTO, SUBTITULO

            textos_marca = _textos_de(marca)
            self.assertNotIn(NOMBRE_PRODUCTO, textos_marca)
            self.assertNotIn(SUBTITULO, textos_marca)
            self.assertFalse(marca._sobre_placa_clara)
            etiquetas = [OPCIONES_MENU[i][1] for i in range(8)]
            self.assertEqual(etiquetas[0], "Abecedario")
            self.assertEqual(etiquetas[1], "Vocabulario")
            self.assertEqual(etiquetas[2], "Mini juego")
            self.assertNotIn("Iniciar reconocimiento", etiquetas)
            pantalla._tarjetas[0]._on_ir(pantalla._tarjetas[0]._destino)
            self.assertEqual(destinos, ["abecedario"])
            pantalla._tarjetas[1]._on_ir(pantalla._tarjetas[1]._destino)
            self.assertEqual(destinos[-1], "vocabulario")
            pantalla._tarjetas[2]._on_ir(pantalla._tarjetas[2]._destino)
            self.assertEqual(destinos[-1], "practica")
            pantalla._tarjetas[7]._on_ir(pantalla._tarjetas[7]._destino)
            self.assertEqual(destinos[-1], "acerca")
        finally:
            raiz.destroy()

    def test_en_oscuro_el_logo_queda_sobre_placa_clara_sin_titulo(self) -> None:
        import customtkinter as ctk

        from innova.config import NOMBRE_PRODUCTO, SUBTITULO
        from innova.pantallas import MarcaMamatlatolli
        from innova.tema import aplicar_tema

        aplicar_tema("oscuro")
        raiz = ctk.CTk()
        raiz.withdraw()
        try:
            marca = MarcaMamatlatolli(raiz)
            self.assertTrue(marca._es_logo_archivo)
            self.assertTrue(marca._sobre_placa_clara)
            textos = _textos_de(marca)
            self.assertNotIn(NOMBRE_PRODUCTO, textos)
            self.assertNotIn(SUBTITULO, textos)
        finally:
            raiz.destroy()
            aplicar_tema("claro")

    def test_sin_png_el_placeholder_conserva_nombre_y_subtitulo(self) -> None:
        import customtkinter as ctk

        from innova.config import NOMBRE_PRODUCTO, SUBTITULO
        from innova.pantallas import MarcaMamatlatolli

        raiz = ctk.CTk()
        raiz.withdraw()
        try:
            with unittest.mock.patch("innova.pantallas.resolver_logo", return_value=None), unittest.mock.patch(
                "innova.tema.resolver_logo", return_value=None
            ):
                marca = MarcaMamatlatolli(raiz)
            self.assertFalse(marca._es_logo_archivo)
            textos = _textos_de(marca)
            self.assertIn(NOMBRE_PRODUCTO, textos)
            self.assertIn(SUBTITULO, textos)
        finally:
            raiz.destroy()


def _luminancia(canal: float) -> float:
    c = canal / 255
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def contraste(a: str, b: str) -> float:
    def lum(color: str) -> float:
        rojo, verde, azul = hex_a_rgb(color)
        return 0.2126 * _luminancia(rojo) + 0.7152 * _luminancia(verde) + 0.0722 * _luminancia(azul)

    alta, baja = sorted((lum(a), lum(b)), reverse=True)
    return (alta + 0.05) / (baja + 0.05)


class TestPaletasClaroOscuro(unittest.TestCase):
    def test_ambas_exponen_los_mismos_tokens(self) -> None:
        self.assertEqual(set(PALETA_CLARA), set(TOKENS_REQUERIDOS))
        self.assertEqual(set(PALETA_OSCURA), set(TOKENS_REQUERIDOS))
        for token in TOKENS_REQUERIDOS:
            self.assertIsNotNone(PALETA_CLARA[token])
            self.assertIsNotNone(PALETA_OSCURA[token])
            self.assertEqual(type(PALETA_CLARA[token]), type(PALETA_OSCURA[token]))

    def test_tridada_distinta_en_cada_paleta(self) -> None:
        for paleta in (PALETA_CLARA, PALETA_OSCURA):
            triada = (paleta["COLOR_NARANJA"], paleta["COLOR_LIMA"], paleta["COLOR_INDIGO"])
            self.assertEqual(len(set(triada)), 3)
            self.assertEqual(paleta["COLOR_ACENTO"], paleta["COLOR_INDIGO"])
            self.assertEqual(paleta["COLOR_AVISO"], paleta["COLOR_NARANJA"])
            self.assertEqual(paleta["COLOR_OK"], paleta["COLOR_LIMA"])
            self.assertEqual(paleta["BGR_NARANJA"], hex_a_bgr(paleta["COLOR_NARANJA"]))
            self.assertEqual(paleta["BGR_LIMA"], hex_a_bgr(paleta["COLOR_LIMA"]))
            self.assertEqual(paleta["BGR_INDIGO"], hex_a_bgr(paleta["COLOR_INDIGO"]))
            self.assertEqual(paleta["BGR_CAJA"], paleta["BGR_INDIGO"])

    def test_paleta_clara_conserva_los_hex_de_fase_2b(self) -> None:
        self.assertEqual(PALETA_CLARA["COLOR_FONDO"], "#F4F6FB")
        self.assertEqual(PALETA_CLARA["COLOR_TEXTO"], "#1C2233")
        self.assertEqual(PALETA_CLARA["COLOR_NARANJA"], "#F08C28")
        self.assertEqual(PALETA_CLARA["COLOR_LIMA"], "#7CB342")
        self.assertEqual(PALETA_CLARA["COLOR_INDIGO"], "#3F51C9")
        self.assertEqual(PALETA_CLARA["BGR_NARANJA"], (40, 140, 240))
        self.assertEqual(PALETA_CLARA["BGR_LIMA"], (66, 179, 124))
        self.assertEqual(PALETA_CLARA["BGR_INDIGO"], (201, 81, 63))

    def test_oscuro_es_legible(self) -> None:
        oscuro = PALETA_OSCURA
        rf, gf, bf = hex_a_rgb(oscuro["COLOR_FONDO"])
        rt, gt, bt = hex_a_rgb(oscuro["COLOR_TEXTO"])
        self.assertLess((rf + gf + bf) / 3, 80)
        self.assertGreater((rt + gt + bt) / 3, 180)
        self.assertGreaterEqual(contraste(oscuro["COLOR_TEXTO"], oscuro["COLOR_FONDO"]), 7)
        self.assertGreaterEqual(contraste(oscuro["COLOR_TEXTO"], oscuro["COLOR_TARJETA"]), 7)
        self.assertGreaterEqual(contraste(oscuro["COLOR_TEXTO_MUDO"], oscuro["COLOR_FONDO"]), 4.5)
        for acento in ("COLOR_NARANJA", "COLOR_LIMA", "COLOR_INDIGO"):
            self.assertGreaterEqual(contraste(oscuro[acento], oscuro["COLOR_FONDO"]), 3)
            self.assertGreaterEqual(contraste(oscuro[acento], oscuro["COLOR_TARJETA"]), 3)
            self.assertGreaterEqual(contraste(oscuro["COLOR_TEXTO_INVERSO"], oscuro[acento]), 4.5)
        for acento, suave in (
            ("COLOR_NARANJA", "COLOR_NARANJA_SUAVE"),
            ("COLOR_LIMA", "COLOR_LIMA_SUAVE"),
            ("COLOR_INDIGO", "COLOR_INDIGO_SUAVE"),
        ):
            self.assertGreaterEqual(contraste(oscuro[suave], oscuro["COLOR_TARJETA"]), 1.5)
            self.assertGreaterEqual(contraste(oscuro[acento], oscuro[suave]), 3)
        self.assertGreaterEqual(
            contraste(oscuro["COLOR_TEXTO_INVERSO"], oscuro["COLOR_ERROR"]),
            4.5,
        )

    def test_etiquetas_en_espanol(self) -> None:
        self.assertEqual(ETIQUETA_TEMA_CLARO, "Modo claro")
        self.assertEqual(ETIQUETA_TEMA_OSCURO, "Modo oscuro")
        self.assertEqual(etiqueta_tema("oscuro"), "Modo oscuro")
        self.assertEqual(etiqueta_tema("light"), "Modo claro")
        self.assertEqual(modo_desde_etiqueta("Modo oscuro"), "oscuro")
        self.assertEqual(modo_desde_etiqueta("Modo claro"), "claro")
        self.assertEqual(normalizar_tema("dark"), "oscuro")
        self.assertEqual(normalizar_tema("no-existe"), "claro")


class TestPreferenciaTema(unittest.TestCase):
    def tearDown(self) -> None:
        from innova.tema import aplicar_tema

        aplicar_tema("claro")

    def test_guardar_y_cargar_tema_oscuro(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            guardar_ajustes(
                Ajustes(umbral_confianza=0.71, metrica="coseno", tema="oscuro"),
                ruta,
            )
            leido = cargar_ajustes(ruta)
            self.assertEqual(leido.tema, "oscuro")
            self.assertAlmostEqual(leido.umbral_confianza, 0.71, places=5)
            self.assertEqual(leido.metrica, "coseno")

    def test_json_sin_tema_queda_en_claro(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            ruta.write_text(
                json.dumps({"umbral_confianza": 0.66, "metrica": "coseno"}),
                encoding="utf-8",
            )
            leido = cargar_ajustes(ruta)
            self.assertEqual(leido.tema, "claro")
            self.assertAlmostEqual(leido.umbral_confianza, 0.66, places=5)
            self.assertEqual(leido.metrica, "coseno")

    def test_alias_dark_en_el_archivo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            ruta.write_text(json.dumps({"tema": "dark"}), encoding="utf-8")
            self.assertEqual(cargar_ajustes(ruta).tema, "oscuro")

    def test_guardar_tema_no_pisa_otros_ajustes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            guardar_ajustes(
                Ajustes(umbral_confianza=0.81, sensibilidad_movimiento=0.33, metrica="coseno"),
                ruta,
            )
            self.assertEqual(guardar_tema("oscuro", ruta), "oscuro")
            bruto = json.loads(ruta.read_text(encoding="utf-8"))
            self.assertEqual(bruto["tema"], "oscuro")
            self.assertAlmostEqual(bruto["umbral_confianza"], 0.81, places=5)
            self.assertAlmostEqual(bruto["sensibilidad_movimiento"], 0.33, places=5)
            self.assertEqual(bruto["metrica"], "coseno")
            leido = cargar_ajustes(ruta)
            self.assertEqual(leido.tema, "oscuro")
            self.assertEqual(leido.metrica, "coseno")

    def test_aplicar_tema_publica_la_paleta_y_restaura(self) -> None:
        from innova import config, tema
        from innova.tema import aplicar_tema

        aplicar_tema("oscuro")
        self.assertEqual(tema.MODO_ACTUAL, "oscuro")
        self.assertEqual(tema.MODO_APARIENCIA, "dark")
        self.assertEqual(tema.COLOR_FONDO, PALETA_OSCURA["COLOR_FONDO"])
        self.assertEqual(tema.COLOR_TEXTO, PALETA_OSCURA["COLOR_TEXTO"])
        self.assertEqual(tema.TRIDADA, (
            PALETA_OSCURA["COLOR_NARANJA"],
            PALETA_OSCURA["COLOR_LIMA"],
            PALETA_OSCURA["COLOR_INDIGO"],
        ))
        self.assertEqual(config.COLOR_FONDO, tema.COLOR_FONDO)
        self.assertEqual(config.COLOR_ACENTO, tema.COLOR_INDIGO)
        self.assertEqual(config.BGR_CAJA, tema.BGR_INDIGO)
        aplicar_tema("claro")
        self.assertEqual(tema.COLOR_FONDO, PALETA_CLARA["COLOR_FONDO"])
        self.assertEqual(config.COLOR_FONDO, PALETA_CLARA["COLOR_FONDO"])
        self.assertEqual(tema.MODO_ACTUAL, "claro")


def _textos_de(widget) -> list[str]:
    textos: list[str] = []

    def visitar(actual) -> None:
        try:
            valor = actual.cget("text")
        except Exception:  # noqa: BLE001 — no todos los widgets tienen texto
            valor = None
        if isinstance(valor, str) and valor:
            textos.append(valor)
        for hijo in actual.winfo_children():
            visitar(hijo)

    visitar(widget)
    return textos


def _widget_con_texto(widget, texto: str):
    try:
        if widget.cget("text") == texto:
            return widget
    except Exception:  # noqa: BLE001 — no todos los widgets tienen texto
        pass
    for hijo in widget.winfo_children():
        hallado = _widget_con_texto(hijo, texto)
        if hallado is not None:
            return hallado
    return None


@unittest.skipUnless(os.environ.get("DISPLAY"), "requiere un display gráfico")
class TestTemaEnVivo(unittest.TestCase):
    def tearDown(self) -> None:
        from innova.tema import aplicar_tema

        aplicar_tema("claro")

    def test_toggle_en_configuracion_repinta_y_persiste(self) -> None:
        import customtkinter as ctk

        from innova import ajustes, tema
        from innova.ui import VentanaMamatlatolli

        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            original = ajustes.RUTA_AJUSTES
            ajustes.RUTA_AJUSTES = ruta
            raiz = None
            try:
                tema.aplicar_tema("claro")
                raiz = VentanaMamatlatolli()
                raiz.withdraw()
                raiz.ir_a("configuracion")
                oscuro = _widget_con_texto(raiz, "Modo oscuro")
                self.assertIsNotNone(oscuro)
                assert oscuro is not None
                self.assertEqual(oscuro.winfo_manager(), "pack")
                self.assertGreater(oscuro.winfo_reqwidth(), 40)
                oscuro.invoke()
                raiz.update()
                self.assertEqual(tema.MODO_ACTUAL, "oscuro")
                self.assertEqual(str(raiz.cget("fg_color")).lower(), tema.COLOR_FONDO.lower())
                self.assertEqual(str(raiz._pantalla.cget("fg_color")).lower(), tema.COLOR_FONDO.lower())
                self.assertEqual(ajustes.cargar_ajustes(ruta).tema, "oscuro")
                claro = _widget_con_texto(raiz, "Modo claro")
                self.assertIsNotNone(claro)
                assert claro is not None
                claro.invoke()
                raiz.update()
                self.assertEqual(tema.MODO_ACTUAL, "claro")
                self.assertEqual(ajustes.cargar_ajustes(ruta).tema, "claro")
                raiz.mostrar_menu()
                raiz.update()
                self.assertEqual(len(raiz._pantalla._tarjetas), 8)
                self.assertIsNotNone(_widget_con_texto(raiz, "Abecedario"))
                self.assertIsNotNone(_widget_con_texto(raiz, "Vocabulario"))
                self.assertIsNotNone(_widget_con_texto(raiz, "Mini juego"))
                menu_oscuro = _widget_con_texto(raiz, "Modo oscuro")
                self.assertIsNotNone(menu_oscuro)
                assert menu_oscuro is not None
                self.assertEqual(menu_oscuro.winfo_manager(), "pack")
            finally:
                if raiz is not None:
                    raiz.destroy()
                ajustes.RUTA_AJUSTES = original
                ctk.set_appearance_mode("light")


if __name__ == "__main__":
    unittest.main()
