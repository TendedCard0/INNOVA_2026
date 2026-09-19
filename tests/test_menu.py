"""Pruebas de ajustes persistentes y del menú (sin ventana gráfica)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from innova.ajustes import Ajustes, cargar_ajustes, guardar_ajustes
from innova.menu import (
    DESTINO_ABECEDARIO,
    DESTINO_CAPTURA,
    DESTINO_MENU,
    DESTINO_VOCABULARIO,
    Navegador,
    OPCIONES_MENU,
    TEXTO_ACERCA,
    categoria_de_destino,
    etiquetas_menu,
)


class TestAjustes(unittest.TestCase):
    def test_ida_y_vuelta_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            original = Ajustes(
                umbral_confianza=0.72,
                umbral_histeresis=0.41,
                fotogramas_consecutivos=8,
                sensibilidad_movimiento=0.8,
                ventana_movimiento_s=0.55,
                metrica="coseno",
            )
            guardar_ajustes(original, ruta)
            leido = cargar_ajustes(ruta)
            self.assertAlmostEqual(leido.umbral_confianza, 0.72, places=5)
            self.assertAlmostEqual(leido.sensibilidad_movimiento, 0.8, places=5)
            self.assertAlmostEqual(leido.ventana_movimiento_s, 0.55, places=5)
            self.assertEqual(leido.metrica, "coseno")
            self.assertEqual(leido.fotogramas_consecutivos, 8)

    def test_archivo_ausente_usa_omision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            leido = cargar_ajustes(Path(tmp) / "no-existe.json")
            self.assertEqual(leido.metrica, "euclidiana")
            self.assertGreater(leido.umbral_confianza, 0.4)

    def test_recorta_valores_fuera_de_rango(self) -> None:
        aj = Ajustes(umbral_confianza=2.0, sensibilidad_movimiento=-1, ventana_movimiento_s=3).normalizado()
        self.assertLessEqual(aj.umbral_confianza, 0.95)
        self.assertGreaterEqual(aj.sensibilidad_movimiento, 0.0)
        self.assertLessEqual(aj.ventana_movimiento_s, 0.80)
        self.assertGreaterEqual(aj.ventana_movimiento_s, 0.40)


class TestMenuNavegacion(unittest.TestCase):
    def test_siete_opciones_abecedario_y_vocabulario(self) -> None:
        self.assertEqual(
            etiquetas_menu(),
            [
                "Abecedario",
                "Vocabulario",
                "Capturar plantillas",
                "Biblioteca de señas",
                "Configuración",
                "Modo demostración",
                "Acerca de Mamatlatolli",
            ],
        )
        self.assertEqual(len(OPCIONES_MENU), 7)
        self.assertNotIn("Iniciar reconocimiento", etiquetas_menu())
        destinos = [d for d, _e, _s in OPCIONES_MENU]
        self.assertEqual(destinos[0], DESTINO_ABECEDARIO)
        self.assertEqual(destinos[1], DESTINO_VOCABULARIO)

    def test_categoria_de_destino(self) -> None:
        self.assertEqual(categoria_de_destino(DESTINO_ABECEDARIO), "letra")
        self.assertEqual(categoria_de_destino(DESTINO_VOCABULARIO), "palabra")
        self.assertEqual(categoria_de_destino("demo"), "letra")

    def test_ir_y_volver_al_menu(self) -> None:
        nav = Navegador()
        self.assertTrue(nav.en_menu())
        nav.ir(DESTINO_CAPTURA)
        self.assertEqual(nav.actual, DESTINO_CAPTURA)
        self.assertTrue(nav.usa_video())
        nav.volver()
        self.assertEqual(nav.actual, DESTINO_MENU)

    def test_destino_invalido(self) -> None:
        nav = Navegador()
        with self.assertRaises(ValueError):
            nav.ir("no-existe")

    def test_acerca_nombra_mamatlatolli_y_fases(self) -> None:
        self.assertIn("Mamatlatolli", TEXTO_ACERCA)
        self.assertIn("2b", TEXTO_ACERCA)
        self.assertIn("Abecedario", TEXTO_ACERCA)
        self.assertIn("Vocabulario", TEXTO_ACERCA)
        self.assertIn("DTW", TEXTO_ACERCA)
        self.assertIn("Lengua de Señas Mexicana", TEXTO_ACERCA)
        self.assertNotIn("Iniciar reconocimiento", TEXTO_ACERCA)

    def test_demo_no_usa_camara(self) -> None:
        nav = Navegador()
        nav.ir("demo")
        self.assertTrue(nav.usa_demostracion())
        self.assertTrue(nav.usa_video())

    def test_abecedario_y_vocabulario_usan_video(self) -> None:
        nav = Navegador()
        nav.ir(DESTINO_ABECEDARIO)
        self.assertTrue(nav.usa_video())
        nav.ir(DESTINO_VOCABULARIO)
        self.assertTrue(nav.usa_video())
        self.assertFalse(nav.usa_demostracion())


if __name__ == "__main__":
    unittest.main()
