"""Pruebas del marcador de reconocimiento LSM (fase 1)."""

from __future__ import annotations

import unittest

import numpy as np

from innova.config import ETIQUETA_DETECTANDO, ETIQUETA_SIN_DETECCION
from innova.detector import ManoDetectada, Punto
from innova.reconocimiento import ReconocedorMarcador, crear_reconocedor


def _mano_falsa() -> ManoDetectada:
    puntos = [Punto(0.1 * (i % 5), 0.1 * (i // 5)) for i in range(21)]
    return ManoDetectada(puntos=puntos, lateralidad="derecha", puntuacion=0.9)


class TestReconocedorMarcador(unittest.TestCase):
    def setUp(self) -> None:
        self.reconocedor = ReconocedorMarcador()
        self.frame = np.zeros((48, 64, 3), dtype=np.uint8)

    def test_sin_manos_devuelve_guion(self) -> None:
        r = self.reconocedor.predecir(self.frame, [])
        self.assertEqual(r.etiqueta, ETIQUETA_SIN_DETECCION)
        self.assertEqual(r.confianza, 0.0)

    def test_con_manos_devuelve_detectando(self) -> None:
        r = self.reconocedor.predecir(self.frame, [_mano_falsa()])
        self.assertEqual(r.etiqueta, ETIQUETA_DETECTANDO)
        self.assertIn("fase 2", r.mensaje.lower())

    def test_fabrica_devuelve_el_marcador(self) -> None:
        self.assertIsInstance(crear_reconocedor(), ReconocedorMarcador)


if __name__ == "__main__":
    unittest.main()
