"""Pruebas del esquema JSON versionado (ida y vuelta, pose/rostro nulos)."""

from __future__ import annotations

import unittest

from innova.camara import esqueleto_mano_normalizado
from innova.config import VERSION_ESQUEMA
from innova.detector import ManoDetectada, Punto
from innova.esquema import (
    ErrorEsquema,
    FotogramaSecuencia,
    muestra_desde_dict,
    muestra_dinamica_desde_fotogramas,
    muestra_estatica_desde_mano,
    validar_muestra,
)


def _mano(t: float = 0.0) -> ManoDetectada:
    xy = esqueleto_mano_normalizado(0.5, 0.6, 0.25, 0.1, t)
    return ManoDetectada(
        puntos=[Punto(x, y, 0.01 * i) for i, (x, y) in enumerate(xy)],
        lateralidad="derecha",
        puntuacion=0.95,
    )


class TestEsquemaEstatico(unittest.TestCase):
    def test_ida_y_vuelta_con_pose_y_rostro_nulos(self) -> None:
        original = muestra_estatica_desde_mano(
            _mano(),
            "a",
            consentimiento=True,
            notas="prueba",
            origen="test",
        )
        bruto = original.a_dict()
        self.assertEqual(bruto["version"], VERSION_ESQUEMA)
        self.assertEqual(bruto["etiqueta"], "A")
        self.assertEqual(bruto["tipo"], "estatico")
        self.assertIsNone(bruto["pose"])
        self.assertIsNone(bruto["rostro"])
        self.assertIsNone(bruto["secuencia"])
        self.assertEqual(len(bruto["mano"]["landmarks"]), 21)
        self.assertEqual(len(bruto["mano"]["landmarks"][0]), 3)
        self.assertTrue(bruto["metadatos"]["consentimiento"])
        self.assertEqual(validar_muestra(bruto), [])

        recuperada = muestra_desde_dict(bruto)
        otra_vez = recuperada.a_dict()
        self.assertEqual(otra_vez["etiqueta"], "A")
        self.assertIsNone(otra_vez["pose"])
        self.assertIsNone(otra_vez["rostro"])
        self.assertEqual(len(otra_vez["mano"]["caracteristicas"]), len(bruto["mano"]["caracteristicas"]))

    def test_completa_caracteristicas_si_faltan(self) -> None:
        bruto = muestra_estatica_desde_mano(_mano(), "B").a_dict()
        bruto["mano"]["caracteristicas"] = []
        bruto["mano"]["landmarks_normalizados"] = []
        recuperada = muestra_desde_dict(bruto)
        self.assertEqual(len(recuperada.mano.landmarks_normalizados), 21)
        self.assertGreaterEqual(len(recuperada.mano.caracteristicas), 63)


class TestEsquemaDinamico(unittest.TestCase):
    def test_secuencia_con_cuerpo_nulo(self) -> None:
        mano = muestra_estatica_desde_mano(_mano(), "J").mano
        muestra = muestra_dinamica_desde_fotogramas(
            "j",
            [
                FotogramaSecuencia(t=0.0, mano=mano, pose=None, rostro=None),
                FotogramaSecuencia(t=0.04, mano=mano, pose=None, rostro=None),
            ],
            consentimiento=True,
            notas="gancho 2b",
        )
        bruto = muestra.a_dict()
        self.assertEqual(bruto["tipo"], "dinamico")
        self.assertIsNone(bruto["pose"])
        self.assertIsNone(bruto["rostro"])
        self.assertEqual(len(bruto["secuencia"]["fotogramas"]), 2)
        self.assertIsNone(bruto["secuencia"]["fotogramas"][0]["pose"])
        self.assertEqual(validar_muestra(bruto), [])
        self.assertEqual(muestra_desde_dict(bruto).etiqueta, "J")

    def test_acepta_pose_y_rostro_futuros(self) -> None:
        bruto = muestra_estatica_desde_mano(_mano(), "A").a_dict()
        bruto["pose"] = {"landmarks": [[0.1, 0.2, 0.0]]}
        bruto["rostro"] = {"landmarks": [[0.3, 0.4, 0.0]]}
        self.assertEqual(validar_muestra(bruto), [])
        recuperada = muestra_desde_dict(bruto)
        self.assertIsNotNone(recuperada.pose)
        self.assertIsNotNone(recuperada.rostro)


class TestValidacion(unittest.TestCase):
    def test_rechaza_etiqueta_vacia_y_tipo_raro(self) -> None:
        errores = validar_muestra({"version": "1.0", "etiqueta": " ", "tipo": "otra"})
        textos = " ".join(errores)
        self.assertIn("etiqueta", textos)
        self.assertIn("tipo", textos)

    def test_estatico_exige_21_landmarks(self) -> None:
        bruto = muestra_estatica_desde_mano(_mano(), "C").a_dict()
        bruto["mano"]["landmarks"] = bruto["mano"]["landmarks"][:10]
        errores = validar_muestra(bruto)
        self.assertTrue(any("21" in e for e in errores))
        with self.assertRaises(ErrorEsquema):
            muestra_desde_dict(bruto)

    def test_dinamico_exige_secuencia(self) -> None:
        errores = validar_muestra(
            {
                "version": "1.0",
                "etiqueta": "J",
                "tipo": "dinamico",
                "mano": None,
                "pose": None,
                "rostro": None,
                "secuencia": None,
                "metadatos": {"marca_tiempo": "2026-01-01T00:00:00+00:00", "consentimiento": True},
            }
        )
        self.assertTrue(any("secuencia" in e for e in errores))


if __name__ == "__main__":
    unittest.main()
