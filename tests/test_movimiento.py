"""Pruebas del detector de movimiento (enrutado estático vs dinámico)."""

from __future__ import annotations

import unittest

from innova.movimiento import DetectorMovimiento, puntuacion_movimiento


class TestPuntuacionMovimiento(unittest.TestCase):
    def test_quieta_da_casi_cero(self) -> None:
        trayectoria = [(0.50, 0.60)] * 18
        self.assertLess(puntuacion_movimiento(trayectoria), 0.01)

    def test_temblor_pequeno_no_parece_gesto(self) -> None:
        trayectoria = [(0.50 + (0.002 if i % 2 else -0.002), 0.60) for i in range(18)]
        self.assertLess(puntuacion_movimiento(trayectoria), 0.05)

    def test_barrido_tipo_j_supera_umbral_base(self) -> None:
        trayectoria = [(0.40 + 0.02 * i, 0.60) for i in range(16)]
        self.assertGreater(puntuacion_movimiento(trayectoria), 0.10)

    def test_pocos_puntos_son_cero(self) -> None:
        self.assertEqual(puntuacion_movimiento([(0.1, 0.1)]), 0.0)
        self.assertEqual(puntuacion_movimiento([(0.1, 0.1), (0.2, 0.2)]), 0.0)


class TestDetectorMovimiento(unittest.TestCase):
    def test_estable_no_enruta(self) -> None:
        det = DetectorMovimiento(ventana_s=0.60, umbral=0.08, sensibilidad=0.5)
        ultimo = None
        for i in range(20):
            ultimo = det.actualizar((0.51, 0.62), t=i * 0.03)
        assert ultimo is not None
        self.assertFalse(ultimo.en_movimiento)
        self.assertLess(ultimo.puntuacion, ultimo.umbral)

    def test_barrido_enruta_a_dinamico(self) -> None:
        det = DetectorMovimiento(ventana_s=0.60, umbral=0.08, sensibilidad=0.5)
        ultimo = None
        for i in range(20):
            ultimo = det.actualizar((0.40 + 0.012 * i, 0.62), t=i * 0.03)
        assert ultimo is not None
        self.assertTrue(ultimo.en_movimiento)
        self.assertGreaterEqual(ultimo.puntuacion, ultimo.umbral)

    def test_mas_sensibilidad_umbral_mas_bajo(self) -> None:
        alto = DetectorMovimiento(umbral=0.08, sensibilidad=1.0)
        bajo = DetectorMovimiento(umbral=0.08, sensibilidad=0.0)
        self.assertLess(alto.umbral_efectivo(), bajo.umbral_efectivo())

    def test_sin_mano_reinicia(self) -> None:
        det = DetectorMovimiento()
        for i in range(10):
            det.actualizar((0.4 + 0.02 * i, 0.6), t=i * 0.03)
        quieto = det.actualizar(None, t=0.40)
        self.assertFalse(quieto.en_movimiento)
        self.assertEqual(quieto.muestras, 0)

    def test_ventana_se_recorta_a_0_4_0_8(self) -> None:
        corto = DetectorMovimiento(ventana_s=0.1)
        largo = DetectorMovimiento(ventana_s=2.0)
        self.assertGreaterEqual(corto.ventana_s, 0.40)
        self.assertLessEqual(largo.ventana_s, 0.80)


if __name__ == "__main__":
    unittest.main()
