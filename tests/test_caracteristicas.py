"""Pruebas de normalización de landmarks y matching por distancia."""

from __future__ import annotations

import unittest

import numpy as np

from innova.camara import esqueleto_mano_normalizado
from innova.caracteristicas import (
    ErrorCaracteristicas,
    confianza_desde_distancia,
    distancia_coseno,
    distancia_euclidiana,
    extraer_vector,
    normalizar_landmarks,
    vector_caracteristicas,
)
from innova.detector import ManoDetectada, Punto
from innova.esquema import muestra_estatica_desde_mano
from innova.estabilidad import FiltroEstabilidad
from innova.reconocimiento import ReconocedorEstatico


def _mano_abierta(dx: float = 0.0, dy: float = 0.0, escala: float = 0.25) -> ManoDetectada:
    xy = esqueleto_mano_normalizado(0.5 + dx, 0.6 + dy, escala, 0.0, 0.0)
    return ManoDetectada(
        puntos=[Punto(x, y, 0.0) for x, y in xy],
        lateralidad="derecha",
        puntuacion=1.0,
    )


def _mano_cerrada() -> ManoDetectada:
    """Aproxima un puño: las puntas se acercan a la palma."""
    abierta = _mano_abierta()
    pts = list(abierta.puntos)
    palma = pts[9]
    for i in (4, 8, 12, 16, 20, 3, 7, 11, 15, 19):
        p = pts[i]
        pts[i] = Punto(
            p.x * 0.35 + palma.x * 0.65,
            p.y * 0.35 + palma.y * 0.65,
            p.z,
        )
    return ManoDetectada(puntos=pts, lateralidad="derecha", puntuacion=1.0)


class TestNormalizacion(unittest.TestCase):
    def test_muneca_en_origen_y_palma_unitaria(self) -> None:
        mano = _mano_abierta(dx=0.2, dy=-0.1, escala=0.4)
        norm = normalizar_landmarks(mano.puntos)
        self.assertEqual(norm.shape, (21, 3))
        np.testing.assert_allclose(norm[0], [0.0, 0.0, 0.0], atol=1e-9)
        self.assertAlmostEqual(float(np.linalg.norm(norm[9])), 1.0, places=5)

    def test_invariante_a_traslacion_y_escala(self) -> None:
        a = extraer_vector(_mano_abierta(dx=0.0, escala=0.2).puntos)
        b = extraer_vector(_mano_abierta(dx=0.3, escala=0.35).puntos)
        self.assertLess(distancia_euclidiana(a, b), 1e-9)

    def test_vector_tiene_78_dimensiones(self) -> None:
        vec = extraer_vector(_mano_abierta().puntos)
        self.assertEqual(vec.shape, (78,))

    def test_degenerada_lanza_error(self) -> None:
        puntos = [Punto(0.4, 0.5, 0.0)] * 21
        with self.assertRaises(ErrorCaracteristicas):
            normalizar_landmarks(puntos)


class TestDistancias(unittest.TestCase):
    def test_identicos_distancia_cero(self) -> None:
        v = extraer_vector(_mano_abierta().puntos)
        self.assertAlmostEqual(distancia_euclidiana(v, v), 0.0, places=9)
        self.assertAlmostEqual(distancia_coseno(v, v), 0.0, places=9)
        self.assertGreater(confianza_desde_distancia(0.0), 0.99)

    def test_abierta_y_cerrada_no_son_iguales(self) -> None:
        a = extraer_vector(_mano_abierta().puntos)
        b = extraer_vector(_mano_cerrada().puntos)
        self.assertGreater(distancia_euclidiana(a, b), 0.15)
        self.assertGreater(distancia_coseno(a, np.zeros_like(a) + 1e-6), 0.0)

    def test_caracteristicas_desde_matriz_normalizada(self) -> None:
        norm = normalizar_landmarks(_mano_abierta().puntos)
        vec = vector_caracteristicas(norm)
        self.assertEqual(len(vec), 78)


class TestMatchingPlantillas(unittest.TestCase):
    def test_elige_la_plantilla_mas_cercana(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp)
            rec = ReconocedorEstatico(ruta, filtro=FiltroEstabilidad(consecutivos=3, votos_m=3, ventana_k=5))
            rec.registrar_plantilla(muestra_estatica_desde_mano(_mano_abierta(), "A", origen="test"))
            rec.registrar_plantilla(muestra_estatica_desde_mano(_mano_cerrada(), "S", origen="test"))
            etiq, dist, conf = rec.estimar_crudo([_mano_abierta(dx=0.05)])
            self.assertEqual(etiq, "A")
            self.assertGreater(conf, 0.7)
            self.assertLess(dist, 0.2)
            etiq_s, _, conf_s = rec.estimar_crudo([_mano_cerrada()])
            self.assertEqual(etiq_s, "S")
            self.assertGreater(conf_s, 0.7)

    def test_tambien_con_metrica_coseno(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            rec = ReconocedorEstatico(Path(tmp), metrica="coseno")
            rec.registrar_plantilla(muestra_estatica_desde_mano(_mano_abierta(), "A", origen="test"))
            rec.registrar_plantilla(muestra_estatica_desde_mano(_mano_cerrada(), "S", origen="test"))
            etiq, _, conf = rec.estimar_crudo([_mano_abierta()])
            self.assertEqual(etiq, "A")
            self.assertGreater(conf, 0.8)


if __name__ == "__main__":
    unittest.main()
