"""Pruebas de DTW y del matching dinámico."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from innova.camara import esqueleto_mano_normalizado
from innova.config import ETIQUETA_DETECTANDO, MIN_FOTOGRAMAS_DINAMICO
from innova.detector import ManoDetectada, Punto
from innova.caracteristicas import DIM_FUSION_DINAMICA
from innova.dtw import (
    confianza_dtw,
    dtw_distancia,
    mejor_plantilla_dtw,
    vectores_desde_landmarks,
    vectores_desde_secuencia,
    vectores_fusionados_desde_secuencia,
)
from innova.esquema import (
    FotogramaSecuencia,
    mano_desde_deteccion,
    muestra_dinamica_desde_fotogramas,
)
from innova.estabilidad import FiltroEstabilidad
from innova.reconocimiento import ReconocedorEstatico


def _mano(dx: float = 0.0, dy: float = 0.0) -> ManoDetectada:
    xy = esqueleto_mano_normalizado(0.5 + dx, 0.62 + dy, 0.25, 0.0, 0.0)
    return ManoDetectada(
        puntos=[Punto(x, y, 0.0) for x, y in xy],
        lateralidad="derecha",
        puntuacion=0.95,
    )


def _landmarks_barrido(n: int, eje: str) -> list[list[Punto]]:
    salida = []
    for i in range(n):
        frac = i / max(1, n - 1)
        dx = 0.22 * frac if eje == "x" else 0.0
        dy = 0.18 * frac if eje == "y" else 0.0
        salida.append(_mano(dx=dx, dy=dy).puntos)
    return salida


def _muestra_barrido(etiqueta: str, eje: str, n: int = 12):
    frames = []
    for i, pts in enumerate(_landmarks_barrido(n, eje)):
        mano = ManoDetectada(puntos=pts, lateralidad="derecha", puntuacion=0.95)
        frames.append(
            FotogramaSecuencia(
                t=i / 30.0,
                mano=mano_desde_deteccion(mano),
                pose=None,
                rostro=None,
            )
        )
    return muestra_dinamica_desde_fotogramas(etiqueta, frames, origen="test")


def _con_cuerpo(muestra):
    pts = [[0.5, 0.5, 0.0] for _ in range(33)]
    pts[11] = [0.40, 0.35, 0.0]
    pts[12] = [0.60, 0.35, 0.0]
    pts[23] = [0.42, 0.70, 0.0]
    pts[24] = [0.58, 0.70, 0.0]
    pose = {"landmarks": pts}
    for foto in muestra.secuencia.fotogramas:
        foto.pose = pose
    return muestra


class TestDTW(unittest.TestCase):
    def test_secuencias_identicas_distancia_cero(self) -> None:
        a = vectores_desde_landmarks(_landmarks_barrido(10, "x"))
        d = dtw_distancia(a, a)
        self.assertAlmostEqual(d, 0.0, places=6)
        self.assertGreater(confianza_dtw(d), 0.99)

    def test_estirar_en_el_tiempo_sigue_cerca(self) -> None:
        base = vectores_desde_landmarks(_landmarks_barrido(8, "x"))
        estirada = np.repeat(base, 2, axis=0)
        d = dtw_distancia(base, estirada)
        self.assertLess(d, 0.05)

    def test_trayectorias_distintas_alejan(self) -> None:
        horizontal = vectores_desde_landmarks(_landmarks_barrido(12, "x"))
        vertical = vectores_desde_landmarks(_landmarks_barrido(12, "y"))
        d_dif = dtw_distancia(horizontal, vertical)
        d_eq = dtw_distancia(horizontal, horizontal)
        self.assertGreater(d_dif, d_eq + 0.05)

    def test_elige_la_plantilla_del_mismo_eje(self) -> None:
        j = vectores_desde_secuencia(_muestra_barrido("J", "x"))
        zeta = vectores_desde_secuencia(_muestra_barrido("Z", "y"))
        consulta = vectores_desde_secuencia(_muestra_barrido("J", "x", n=14))
        etiq, dist = mejor_plantilla_dtw(consulta, [("J", j), ("Z", zeta)])
        self.assertEqual(etiq, "J")
        self.assertLess(dist, 0.12)

    def test_vector_dinamico_tiene_80_dimensiones(self) -> None:
        mat = vectores_desde_landmarks(_landmarks_barrido(6, "x"))
        self.assertEqual(mat.shape[1], 80)
        self.assertEqual(mat.shape[0], 6)

    def test_fusion_de_palabra_suma_pose_sin_cambiar_la_letra(self) -> None:
        muestra = _con_cuerpo(_muestra_barrido("J", "x", n=6))
        solo_mano = vectores_desde_secuencia(muestra)
        fusion = vectores_fusionados_desde_secuencia(muestra)
        self.assertEqual(solo_mano.shape[1], 80)
        self.assertEqual(fusion.shape, (6, DIM_FUSION_DINAMICA))
        self.assertTrue(np.all(np.isfinite(fusion[:, 80:179])))
        d = dtw_distancia(fusion, fusion)
        self.assertAlmostEqual(d, 0.0, places=6)


class TestReconocedorDinamico(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = np.zeros((48, 64, 3), dtype=np.uint8)
        self._tmp = tempfile.TemporaryDirectory()
        self.rec = ReconocedorEstatico(
            Path(self._tmp.name),
            filtro=FiltroEstabilidad(
                umbral_confianza=0.50,
                umbral_histeresis=0.30,
                consecutivos=3,
                votos_m=3,
                ventana_k=5,
            ),
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_sin_plantillas_dinamicas_explica_captura(self) -> None:
        r = self.rec.predecir_dinamico(_muestra_barrido("J", "x"))
        self.assertEqual(r.etiqueta, ETIQUETA_DETECTANDO)
        self.assertIn("dinámic", r.mensaje.lower())
        self.assertEqual(r.modo, "dinamico")

    def test_predecir_dinamico_elige_j(self) -> None:
        self.rec.registrar_plantilla(_muestra_barrido("J", "x"))
        self.rec.registrar_plantilla(_muestra_barrido("Z", "y"))
        r = self.rec.predecir_dinamico(_muestra_barrido("J", "x", n=14))
        self.assertEqual(r.etiqueta, "J")
        self.assertGreater(r.confianza, 0.7)
        self.assertIn("dtw", r.mensaje.lower())
        self.assertEqual(self.rec.n_dinamicas, 2)

    def test_secuencia_corta_no_compromete(self) -> None:
        self.rec.registrar_plantilla(_muestra_barrido("J", "x"))
        corta = _muestra_barrido("J", "x", n=max(1, MIN_FOTOGRAMAS_DINAMICO - 3))
        r = self.rec.predecir_dinamico(corta)
        self.assertEqual(r.etiqueta, ETIQUETA_DETECTANDO)
        self.assertIn("corta", r.mensaje.lower())

    def test_forzar_dinamico_graba_y_reconoce(self) -> None:
        self.rec.registrar_plantilla(_muestra_barrido("J", "x"))
        self.rec.set_forzar_dinamico(True)
        n = 12
        for i in range(n):
            frac = i / (n - 1)
            r = self.rec.predecir(self.frame, [_mano(dx=0.22 * frac)])
            self.assertEqual(r.modo, "grabando")
        self.rec.set_forzar_dinamico(False)
        final = self.rec.predecir(self.frame, [_mano(dx=0.22)])
        self.assertEqual(final.etiqueta, "J")
        self.assertEqual(final.modo, "dinamico")
        self.assertGreater(final.confianza, 0.55)

    def test_auto_enruta_si_hay_movimiento(self) -> None:
        self.rec.registrar_plantilla(_muestra_barrido("J", "x"))
        modos = []
        n = 16
        for i in range(n):
            frac = i / (n - 1)
            r = self.rec.predecir(self.frame, [_mano(dx=0.25 * frac)])
            modos.append(r.modo)
        self.assertIn("grabando", modos)
        ultimo = None
        for _ in range(8):
            ultimo = self.rec.predecir(self.frame, [_mano(dx=0.25)])
        assert ultimo is not None
        self.assertIn(ultimo.modo, {"dinamico", "grabando", "estatico"})
        if ultimo.modo == "dinamico":
            self.assertEqual(ultimo.etiqueta, "J")


if __name__ == "__main__":
    unittest.main()
