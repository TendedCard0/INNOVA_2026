"""Pruebas del filtro de estabilidad (umbral, voto, histéresis)."""

from __future__ import annotations

import unittest

from innova.config import ETIQUETA_DETECTANDO, ETIQUETA_SIN_DETECCION
from innova.estabilidad import FiltroEstabilidad


def _filtro() -> FiltroEstabilidad:
    return FiltroEstabilidad(
        umbral_confianza=0.6,
        umbral_histeresis=0.4,
        consecutivos=3,
        votos_m=3,
        ventana_k=5,
        paciencia=4,
    )


class TestFiltroEstabilidad(unittest.TestCase):
    def test_baja_confianza_nunca_compromete(self) -> None:
        f = _filtro()
        ultimo = None
        for _ in range(8):
            ultimo = f.actualizar("A", 0.2, hay_mano=True)
        assert ultimo is not None
        self.assertEqual(ultimo.etiqueta, ETIQUETA_DETECTANDO)
        self.assertFalse(ultimo.comprometida)

    def test_n_consecutivos_comprometen(self) -> None:
        f = _filtro()
        estados = [f.actualizar("A", 0.9, hay_mano=True) for _ in range(3)]
        self.assertTrue(all(e.etiqueta == ETIQUETA_DETECTANDO for e in estados[:-1]))
        self.assertEqual(estados[-1].etiqueta, "A")
        self.assertTrue(estados[-1].comprometida)

    def test_m_de_k_tambien_compromete(self) -> None:
        f = FiltroEstabilidad(
            umbral_confianza=0.6,
            umbral_histeresis=0.4,
            consecutivos=99,  # forzamos a que gane el voto M-de-K
            votos_m=3,
            ventana_k=5,
            paciencia=4,
        )
        f.actualizar("A", 0.9, hay_mano=True)
        f.actualizar("B", 0.9, hay_mano=True)
        f.actualizar("A", 0.9, hay_mano=True)
        f.actualizar("B", 0.1, hay_mano=True)
        ultimo = f.actualizar("A", 0.9, hay_mano=True)
        self.assertEqual(ultimo.etiqueta, "A")

    def test_histeresis_mantiene_ante_un_bache(self) -> None:
        f = _filtro()
        for _ in range(3):
            f.actualizar("A", 0.9, hay_mano=True)
        bache = f.actualizar("A", 0.45, hay_mano=True)  # entre umbrales
        self.assertEqual(bache.etiqueta, "A")
        hueco = f.actualizar(None, 0.0, hay_mano=False)
        self.assertEqual(hueco.etiqueta, "A")
        self.assertIn("misma seña", hueco.mensaje.lower())
        self.assertNotIn("histéresis", hueco.mensaje.lower())

    def test_no_cambia_de_letra_en_un_solo_fotograma(self) -> None:
        f = _filtro()
        for _ in range(3):
            f.actualizar("A", 0.9, hay_mano=True)
        parpadeo = f.actualizar("B", 0.95, hay_mano=True)
        self.assertEqual(parpadeo.etiqueta, "A")
        for _ in range(3):
            ultimo = f.actualizar("B", 0.95, hay_mano=True)
        self.assertEqual(ultimo.etiqueta, "B")

    def test_paciencia_agotada_vuelve_al_marcador(self) -> None:
        f = _filtro()
        for _ in range(3):
            f.actualizar("A", 0.9, hay_mano=True)
        ultimo = None
        for _ in range(4):
            ultimo = f.actualizar(None, 0.0, hay_mano=False)
        assert ultimo is not None
        self.assertEqual(ultimo.etiqueta, ETIQUETA_SIN_DETECCION)
        self.assertFalse(ultimo.comprometida)

    def test_sin_mano_antes_de_comprometer_es_guion(self) -> None:
        f = _filtro()
        r = f.actualizar(None, 0.0, hay_mano=False)
        self.assertEqual(r.etiqueta, ETIQUETA_SIN_DETECCION)


if __name__ == "__main__":
    unittest.main()
