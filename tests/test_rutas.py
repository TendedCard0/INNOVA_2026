"""Rutas de desarrollo y de la app instalada de Mamatlatolli."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from innova.audio import asegurar_sonidos
from innova.config import RUTA_AJUSTES, RUTA_PLANTILLAS
from innova.menu import texto_acerca
from innova.rutas import (
    NOMBRE_CARPETA_DATOS,
    carpeta_para_dialogos,
    preparar_datos_usuario,
    resolver_datos_usuario,
    resolver_recursos,
    ruta_ajustes,
    ruta_assets,
    ruta_datos_usuario,
    ruta_plantillas,
    ruta_sonidos,
    sembrar_plantillas,
)
from innova.tema import RUTA_ICONO_ICO, RUTA_LOGO


_RAIZ = Path(__file__).resolve().parent.parent


def _plano(ruta: Path) -> str:
    """Compara rutas de Windows aunque la prueba corra en Linux."""
    return str(ruta).replace("\\", "/")


class TestRutasDesarrollo(unittest.TestCase):
    def test_datos_siguen_en_el_repositorio(self) -> None:
        self.assertEqual(RUTA_PLANTILLAS, _RAIZ / "datos" / "plantillas")
        self.assertEqual(RUTA_AJUSTES, _RAIZ / "datos" / "config.json")
        anterior = os.environ.pop("MAMATLATOLLI_DATOS", None)
        try:
            self.assertEqual(ruta_plantillas(), _RAIZ / "datos" / "plantillas")
            self.assertEqual(ruta_ajustes(), _RAIZ / "datos" / "config.json")
            self.assertEqual(ruta_datos_usuario(), _RAIZ / "datos")
        finally:
            if anterior is not None:
                os.environ["MAMATLATOLLI_DATOS"] = anterior

    def test_assets_siguen_en_el_repositorio(self) -> None:
        self.assertEqual(ruta_assets(), _RAIZ / "assets")
        self.assertEqual(ruta_sonidos(), _RAIZ / "assets" / "sonidos")
        self.assertEqual(RUTA_LOGO, _RAIZ / "assets" / "logo.png")
        self.assertEqual(RUTA_ICONO_ICO, _RAIZ / "assets" / "icono.ico")
        self.assertTrue(RUTA_ICONO_ICO.is_file())

    def test_acerca_de_muestra_la_carpeta_real(self) -> None:
        self.assertIn(str(ruta_datos_usuario()), texto_acerca())
        self.assertIn("Mamatlatolli", texto_acerca())


class TestResolverRutas(unittest.TestCase):
    def test_windows_empaquetado_usa_localappdata(self) -> None:
        ruta = resolver_datos_usuario(
            empaquetada=True,
            plataforma="win32",
            entorno={"LOCALAPPDATA": r"C:\Users\ana\AppData\Local"},
            home=Path(r"C:\Users\ana"),
            raiz=Path(r"C:\repo"),
        )
        self.assertEqual(ruta, Path(r"C:\Users\ana\AppData\Local") / NOMBRE_CARPETA_DATOS)

    def test_sin_localappdata_arma_la_ruta_estandar(self) -> None:
        ruta = resolver_datos_usuario(
            empaquetada=True,
            plataforma="win32",
            entorno={},
            home=Path(r"C:\Users\ana"),
            raiz=Path(r"C:\repo"),
        )
        self.assertEqual(_plano(ruta), "C:/Users/ana/AppData/Local/Mamatlatolli")

    def test_la_variable_de_entorno_gana(self) -> None:
        ruta = resolver_datos_usuario(
            empaquetada=True,
            plataforma="win32",
            entorno={"MAMATLATOLLI_DATOS": r"D:\banco", "LOCALAPPDATA": r"C:\Users\ana\AppData\Local"},
            home=Path(r"C:\Users\ana"),
            raiz=Path(r"C:\repo"),
        )
        self.assertEqual(ruta, Path(r"D:\banco"))

    def test_desarrollo_ignora_la_plataforma(self) -> None:
        ruta = resolver_datos_usuario(
            empaquetada=False,
            plataforma="win32",
            entorno={"LOCALAPPDATA": r"C:\Users\ana\AppData\Local"},
            home=Path(r"C:\Users\ana"),
            raiz=Path(r"C:\repo"),
        )
        self.assertEqual(_plano(ruta), "C:/repo/datos")

    def test_macos_y_linux_empaquetados(self) -> None:
        home = Path("/home/ana")
        mac = resolver_datos_usuario(
            empaquetada=True,
            plataforma="darwin",
            entorno={},
            home=home,
            raiz=Path("/repo"),
        )
        linux = resolver_datos_usuario(
            empaquetada=True,
            plataforma="linux",
            entorno={},
            home=home,
            raiz=Path("/repo"),
        )
        self.assertEqual(mac, home / "Library" / "Application Support" / "Mamatlatolli")
        self.assertEqual(linux, home / ".local" / "share" / "Mamatlatolli")

    def test_recursos_empaquetados_salen_de_meipass(self) -> None:
        raiz = Path(r"C:\repo")
        self.assertEqual(
            resolver_recursos(empaquetada=True, meipass=r"C:\app\_internal", raiz=raiz),
            Path(r"C:\app\_internal"),
        )
        self.assertEqual(resolver_recursos(empaquetada=False, meipass=r"C:\app\_internal", raiz=raiz), raiz)
        self.assertEqual(resolver_recursos(empaquetada=True, meipass=None, raiz=raiz), raiz)


class TestSiembra(unittest.TestCase):
    def test_no_pisa_y_agrega_lo_que_falta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            origen = base / "fabrica"
            origen.mkdir()
            (origen / "a.json").write_text('{"etiqueta": "A"}\n', encoding="utf-8")
            destino = base / "usuario"
            self.assertEqual(sembrar_plantillas(origen, destino), 1)
            (destino / "a.json").write_text("mio\n", encoding="utf-8")
            (origen / "b.json").write_text("{}\n", encoding="utf-8")
            anidada = origen / "extra"
            anidada.mkdir()
            (anidada / "c.json").write_text("{}\n", encoding="utf-8")
            self.assertEqual(sembrar_plantillas(origen, destino), 2)
            self.assertEqual((destino / "a.json").read_text(encoding="utf-8"), "mio\n")
            self.assertTrue((destino / "extra" / "c.json").is_file())

    def test_la_misma_carpeta_no_se_copia_encima(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            origen = Path(tmp)
            (origen / "a.json").write_text("{}\n", encoding="utf-8")
            self.assertEqual(sembrar_plantillas(origen, origen), 0)

    def test_preparar_en_desarrollo_no_siembra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            origen = base / "fabrica"
            origen.mkdir()
            (origen / "a.json").write_text("{}\n", encoding="utf-8")
            destino = base / "usuario"
            anterior = os.environ.get("MAMATLATOLLI_DATOS")
            os.environ["MAMATLATOLLI_DATOS"] = str(destino)
            try:
                preparar_datos_usuario(empaquetada=False, origen_plantillas=origen)
                self.assertTrue((destino / "plantillas").is_dir())
                self.assertFalse((destino / "plantillas" / "a.json").exists())
                preparar_datos_usuario(empaquetada=True, origen_plantillas=origen)
                self.assertTrue((destino / "plantillas" / "a.json").is_file())
            finally:
                if anterior is None:
                    os.environ.pop("MAMATLATOLLI_DATOS", None)
                else:
                    os.environ["MAMATLATOLLI_DATOS"] = anterior

    def test_sonidos_de_solo_lectura_no_rompen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bloqueo = Path(tmp) / "no-es-carpeta"
            bloqueo.write_text("x", encoding="utf-8")
            self.assertEqual(asegurar_sonidos(bloqueo), bloqueo)


class TestDialogosYArranque(unittest.TestCase):
    def test_dialogo_prefiere_documentos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            documentos = home / "Documents"
            documentos.mkdir()
            with mock.patch("innova.rutas.Path.home", return_value=home):
                self.assertEqual(carpeta_para_dialogos(), documentos)

    def test_el_gancho_de_fallos_no_cambia_el_desarrollo(self) -> None:
        from innova.cli import registrar_fallos_empaquetado

        anterior = sys.excepthook
        registrar_fallos_empaquetado(empaquetada=False)
        self.assertIs(sys.excepthook, anterior)

    def test_el_gancho_escribe_la_bitacora(self) -> None:
        from innova.cli import registrar_fallos_empaquetado

        anterior_gancho = sys.excepthook
        anterior = os.environ.get("MAMATLATOLLI_DATOS")
        avisos: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["MAMATLATOLLI_DATOS"] = tmp
            try:
                registrar_fallos_empaquetado(
                    empaquetada=True,
                    avisar=lambda mensaje, _titulo: avisos.append(mensaje),
                )
                sys.excepthook(RuntimeError, RuntimeError("falla de prueba"), None)
                texto = (Path(tmp) / "mamatlatolli.log").read_text(encoding="utf-8")
                self.assertIn("falla de prueba", texto)
                self.assertEqual(len(avisos), 1)
                self.assertIn("falla de prueba", avisos[0])
            finally:
                sys.excepthook = anterior_gancho
                if anterior is None:
                    os.environ.pop("MAMATLATOLLI_DATOS", None)
                else:
                    os.environ["MAMATLATOLLI_DATOS"] = anterior

    def test_el_cuadro_no_se_abre_en_ci(self) -> None:
        from innova.cli import avisar_con_cuadro, debe_mostrar_cuadro

        self.assertFalse(debe_mostrar_cuadro(plataforma="win32", entorno={"GITHUB_ACTIONS": "true"}))
        self.assertFalse(debe_mostrar_cuadro(plataforma="win32", entorno={"CI": "true"}))
        self.assertTrue(debe_mostrar_cuadro(plataforma="win32", entorno={}))
        self.assertFalse(debe_mostrar_cuadro(plataforma="linux", entorno={}))
        with mock.patch.dict(os.environ, {"CI": "true", "GITHUB_ACTIONS": "true"}):
            avisar_con_cuadro("no debe bloquear")

    def test_main_prepara_datos_antes_de_la_ventana(self) -> None:
        from innova.cli import main

        with (
            mock.patch("innova.rutas.preparar_datos_usuario") as preparar,
            mock.patch("innova.rutas.aplicacion_empaquetada", return_value=False),
            mock.patch("innova.ui.ejecutar_app") as ejecutar,
        ):
            codigo = main(["--demo", "--camara", "1"])
        self.assertEqual(codigo, 0)
        preparar.assert_called_once()
        ejecutar.assert_called_once_with(modo_demo=True, indice_camara=1)
