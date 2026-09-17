"""Pruebas del reconocedor estático (fábrica, matching y gancho dinámico)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from innova.camara import esqueleto_mano_normalizado
from innova.config import ETIQUETA_DETECTANDO, ETIQUETA_SIN_DETECCION
from innova.detector import ManoDetectada, Punto
from innova.esquema import FotogramaSecuencia, muestra_dinamica_desde_fotogramas, muestra_estatica_desde_mano
from innova.estabilidad import FiltroEstabilidad
from innova.reconocimiento import ReconocedorEstatico, crear_reconocedor


def _mano_abierta() -> ManoDetectada:
    xy = esqueleto_mano_normalizado(0.5, 0.6, 0.25, 0.0, 0.0)
    return ManoDetectada(
        puntos=[Punto(x, y, 0.0) for x, y in xy],
        lateralidad="derecha",
        puntuacion=0.9,
    )


class TestReconocedorEstatico(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = np.zeros((48, 64, 3), dtype=np.uint8)
        self._tmp = tempfile.TemporaryDirectory()
        self.ruta = Path(self._tmp.name)
        self.filtro = FiltroEstabilidad(
            umbral_confianza=0.55,
            umbral_histeresis=0.35,
            consecutivos=3,
            votos_m=3,
            ventana_k=5,
            paciencia=4,
        )
        self.reconocedor = ReconocedorEstatico(self.ruta, filtro=self.filtro)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_sin_manos_devuelve_guion(self) -> None:
        r = self.reconocedor.predecir(self.frame, [])
        self.assertEqual(r.etiqueta, ETIQUETA_SIN_DETECCION)
        self.assertEqual(r.confianza, 0.0)

    def test_con_manos_sin_plantillas_detectando(self) -> None:
        r = self.reconocedor.predecir(self.frame, [_mano_abierta()])
        self.assertEqual(r.etiqueta, ETIQUETA_DETECTANDO)
        self.assertIn("plantilla", r.mensaje.lower())

    def test_fabrica_devuelve_el_estatico(self) -> None:
        creado = crear_reconocedor(self.ruta)
        self.assertIsInstance(creado, ReconocedorEstatico)

    def test_estabiliza_la_letra_tras_varios_fotogramas(self) -> None:
        self.reconocedor.registrar_plantilla(
            muestra_estatica_desde_mano(_mano_abierta(), "A", origen="test")
        )
        cruda, _, conf = self.reconocedor.estimar_crudo([_mano_abierta()])
        self.assertEqual(cruda, "A")
        self.assertGreater(conf, 0.7)

        vistos = [self.reconocedor.predecir(self.frame, [_mano_abierta()]) for _ in range(4)]
        self.assertEqual(vistos[-1].etiqueta, "A")
        self.assertEqual(vistos[-1].etiqueta_cruda, "A")
        self.assertTrue(any(v.etiqueta == ETIQUETA_DETECTANDO for v in vistos[:-1]))

    def test_predecir_dinamico_es_gancho_2b(self) -> None:
        seq = muestra_dinamica_desde_fotogramas(
            "J",
            [FotogramaSecuencia(t=0.0, mano=None, pose=None, rostro=None)],
        )
        r = self.reconocedor.predecir_dinamico(seq)
        self.assertEqual(r.etiqueta, ETIQUETA_DETECTANDO)
        self.assertIn("2b", r.mensaje.lower())
        self.assertIn("dtw", r.mensaje.lower())


if __name__ == "__main__":
    unittest.main()
