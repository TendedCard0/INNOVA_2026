"""Ganchos de pose/rostro: hoy inactivos, listos para MediaPipe."""

from __future__ import annotations

import unittest

import numpy as np

from innova.cuerpo import (
    N_LANDMARKS_POSE,
    N_LANDMARKS_ROSTRO,
    POSE_ACTIVA,
    ROSTRO_ACTIVO,
    anotar_cuerpo,
    cuerpo_disponible,
    extraer_pose,
    extraer_rostro,
)


class TestGanchosCuerpo(unittest.TestCase):
    def test_hoy_estan_apagados(self) -> None:
        frame = np.zeros((48, 64, 3), dtype=np.uint8)
        self.assertFalse(POSE_ACTIVA)
        self.assertFalse(ROSTRO_ACTIVO)
        self.assertFalse(cuerpo_disponible())
        self.assertIsNone(extraer_pose(frame))
        self.assertIsNone(extraer_rostro(frame))
        self.assertEqual(anotar_cuerpo(frame), (None, None))
        self.assertEqual(anotar_cuerpo(None), (None, None))

    def test_conteos_de_referencia(self) -> None:
        self.assertEqual(N_LANDMARKS_POSE, 33)
        self.assertEqual(N_LANDMARKS_ROSTRO, 478)
