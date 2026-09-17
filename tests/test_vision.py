"""Pruebas del overlay y del detector / cámara de demostración."""

from __future__ import annotations

import unittest

import numpy as np

from innova.camara import FuenteDemo, esqueleto_mano_normalizado
from innova.detector import DetectorSimulado, ManoDetectada, Punto
from innova.overlay import dibujar_manos, frame_mensaje


def _mano_desde_puntos(xy: list[tuple[float, float]]) -> ManoDetectada:
    return ManoDetectada(
        puntos=[Punto(x, y) for x, y in xy],
        lateralidad="izquierda",
        puntuacion=0.8,
    )


class TestOverlay(unittest.TestCase):
    def test_dibuja_sobre_el_fotograma(self) -> None:
        base = np.zeros((240, 320, 3), dtype=np.uint8)
        xy = esqueleto_mano_normalizado(0.5, 0.6, 0.25, 0.0, 0.0)
        pintado = dibujar_manos(base, [_mano_desde_puntos(xy)])
        self.assertEqual(pintado.shape, base.shape)
        self.assertGreater(int(pintado.sum()), int(base.sum()))

    def test_frame_mensaje_tiene_el_tamano_pedido(self) -> None:
        img = frame_mensaje(["Hola", "Mamatlatolli"], 200, 120)
        self.assertEqual(img.shape, (120, 200, 3))


class TestFuenteDemo(unittest.TestCase):
    def test_genera_fotogramas_bgr(self) -> None:
        fuente = FuenteDemo(ancho=160, alto=120)
        frame = fuente.leer()
        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertEqual(frame.shape, (120, 160, 3))
        fuente.liberar()
        self.assertFalse(fuente.esta_abierta())

    def test_esqueleto_tiene_21_puntos(self) -> None:
        pts = esqueleto_mano_normalizado(0.5, 0.5, 0.2, 0.0)
        self.assertEqual(len(pts), 21)


class TestDetectorSimulado(unittest.TestCase):
    def test_devuelve_una_mano_con_21_landmarks(self) -> None:
        detector = DetectorSimulado()
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        manos = detector.detectar(frame)
        self.assertEqual(len(manos), 1)
        self.assertEqual(len(manos[0].puntos), 21)
        detector.cerrar()


if __name__ == "__main__":
    unittest.main()
