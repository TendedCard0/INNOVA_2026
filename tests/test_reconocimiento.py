"""Pruebas del reconocedor estático (fábrica, matching y gancho dinámico)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from innova.camara import esqueleto_mano_normalizado
from innova.caracteristicas import DIM_FUSION_DINAMICA
from innova.config import ETIQUETA_DETECTANDO, ETIQUETA_SIN_DETECCION
from innova.cuerpo import N_LANDMARKS_POSE, N_LANDMARKS_ROSTRO
from innova.detector import ManoDetectada, Punto
from innova.esquema import (
    FotogramaSecuencia,
    mano_desde_deteccion,
    muestra_dinamica_desde_fotogramas,
    muestra_estatica_desde_mano,
)
from innova.estabilidad import FiltroEstabilidad
from innova.plantillas import guardar_plantilla
from innova.reconocimiento import ReconocedorEstatico, crear_reconocedor


def _pose(muneca_y: float) -> dict:
    pts = [[0.5, 0.5, 0.0] for _ in range(N_LANDMARKS_POSE)]
    pts[11] = [0.40, 0.35, 0.0]
    pts[12] = [0.60, 0.35, 0.0]
    pts[23] = [0.42, 0.70, 0.0]
    pts[24] = [0.58, 0.70, 0.0]
    pts[15] = [0.28, muneca_y, 0.0]
    return {"landmarks": pts}


def _rostro(apertura: float) -> dict:
    pts = [[0.50, 0.50, 0.0] for _ in range(N_LANDMARKS_ROSTRO)]
    pts[1] = [0.50, 0.48, 0.0]
    pts[33] = [0.42, 0.45, 0.0]
    pts[263] = [0.58, 0.45, 0.0]
    pts[14] = [0.50, 0.64 + apertura, 0.0]
    return {"landmarks": pts}


def _secuencia_palabra(etiqueta: str, muneca_y: float):
    frames = []
    for i in range(8):
        frames.append(
            FotogramaSecuencia(
                t=i / 30.0,
                mano=mano_desde_deteccion(_mano_abierta()),
                pose=_pose(muneca_y),
                rostro=_rostro(0.0 if muneca_y < 0.5 else 0.08),
            )
        )
    return muestra_dinamica_desde_fotogramas(
        etiqueta, frames, categoria="palabra", origen="test"
    )


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

    def test_vocabulario_sin_plantillas_mensaje_en_espanol(self) -> None:
        rec = ReconocedorEstatico(self.ruta, categoria="palabra")
        r = rec.predecir(self.frame, [_mano_abierta()])
        self.assertEqual(r.etiqueta, ETIQUETA_DETECTANDO)
        self.assertIn("vocabulario", r.mensaje.lower())
        self.assertIn("palabra", r.mensaje.lower())

    def test_aisla_letra_y_palabra(self) -> None:
        guardar_plantilla(
            muestra_estatica_desde_mano(_mano_abierta(), "A", origen="test", categoria="letra"),
            self.ruta,
        )
        guardar_plantilla(
            muestra_estatica_desde_mano(_mano_abierta(), "HOLA", origen="test", categoria="palabra"),
            self.ruta,
        )
        rec_letra = ReconocedorEstatico(self.ruta, categoria="letra")
        rec_palabra = ReconocedorEstatico(self.ruta, categoria="palabra")
        self.assertEqual([e for e, _v in rec_letra._vectores], ["A"])
        self.assertEqual([e for e, _v in rec_palabra._vectores], ["HOLA"])
        self.assertEqual(rec_letra.n_estaticas, 1)
        self.assertEqual(rec_palabra.n_estaticas, 1)
        cruda_l, _, _ = rec_letra.estimar_crudo([_mano_abierta()])
        cruda_p, _, _ = rec_palabra.estimar_crudo([_mano_abierta()])
        self.assertEqual(cruda_l, "A")
        self.assertEqual(cruda_p, "HOLA")

    def test_palabra_usa_pose_y_rostro(self) -> None:
        mano = _mano_abierta()
        rec = ReconocedorEstatico(self.ruta, categoria="palabra", filtro=self.filtro)
        rec.registrar_plantilla(
            muestra_estatica_desde_mano(
                mano, "SI", categoria="palabra", origen="test", pose=_pose(0.2), rostro=_rostro(0.0)
            )
        )
        rec.registrar_plantilla(
            muestra_estatica_desde_mano(
                mano, "NO", categoria="palabra", origen="test", pose=_pose(0.85), rostro=_rostro(0.1)
            )
        )
        etiq, _dist, conf = rec.estimar_crudo([mano], _pose(0.2), _rostro(0.0))
        self.assertEqual(etiq, "SI")
        self.assertGreater(conf, 0.9)
        etiq_no, _, _ = rec.estimar_crudo([mano], _pose(0.85), _rostro(0.1))
        self.assertEqual(etiq_no, "NO")
        # Sin cuerpo la mano sigue bastando: no truena y elige una de las dos.
        etiq_mano, _, _ = rec.estimar_crudo([mano])
        self.assertIn(etiq_mano, {"SI", "NO"})

    def test_letra_ignora_pose(self) -> None:
        mano = _mano_abierta()
        self.reconocedor.registrar_plantilla(
            muestra_estatica_desde_mano(mano, "A", origen="test", pose=_pose(0.2))
        )
        self.reconocedor.registrar_plantilla(
            muestra_estatica_desde_mano(mano, "B", origen="test", pose=_pose(0.9))
        )
        etiq, dist, _ = self.reconocedor.estimar_crudo([mano], _pose(0.9), _rostro(0.1))
        self.assertEqual(etiq, "A")
        self.assertAlmostEqual(dist, 0.0, places=5)
        self.assertEqual(self.reconocedor._vectores[0][1].shape, (78,))
        self.assertEqual(self.reconocedor._extras, [])

    def test_dtw_de_palabra_prefiere_la_pose(self) -> None:
        rec = ReconocedorEstatico(self.ruta, categoria="palabra", filtro=self.filtro)
        rec.registrar_plantilla(_secuencia_palabra("HOLA", 0.2))
        rec.registrar_plantilla(_secuencia_palabra("GRACIAS", 0.85))
        self.assertEqual(rec._secuencias[0][1].shape[1], DIM_FUSION_DINAMICA)
        resultado = rec.predecir_dinamico(_secuencia_palabra("consulta", 0.2))
        self.assertEqual(resultado.etiqueta, "HOLA")
        self.assertGreater(resultado.confianza, 0.9)
        otra = rec.predecir_dinamico(_secuencia_palabra("consulta", 0.85))
        self.assertEqual(otra.etiqueta, "GRACIAS")

    def test_fabrica_respeta_categoria(self) -> None:
        creado = crear_reconocedor(self.ruta, categoria="palabra")
        self.assertIsInstance(creado, ReconocedorEstatico)
        self.assertEqual(creado.categoria, "palabra")

    def test_predecir_dinamico_sin_plantillas(self) -> None:
        seq = muestra_dinamica_desde_fotogramas(
            "J",
            [FotogramaSecuencia(t=0.0, mano=None, pose=None, rostro=None)],
        )
        r = self.reconocedor.predecir_dinamico(seq)
        self.assertEqual(r.etiqueta, ETIQUETA_DETECTANDO)
        self.assertIn("dinámic", r.mensaje.lower())
        self.assertEqual(r.modo, "dinamico")


if __name__ == "__main__":
    unittest.main()
