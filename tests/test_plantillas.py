"""Inventario y filtro letra / palabra / todas de la biblioteca."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from innova.camara import esqueleto_mano_normalizado
from innova.detector import ManoDetectada, Punto
from innova.esquema import muestra_estatica_desde_mano
from innova.plantillas import (
    filtrar_inventario,
    filtrar_por_categoria,
    guardar_plantilla,
    inventario_plantillas,
)


def _mano() -> ManoDetectada:
    xy = esqueleto_mano_normalizado(0.5, 0.6, 0.25, 0.0, 0.0)
    return ManoDetectada(
        puntos=[Punto(x, y, 0.0) for x, y in xy],
        lateralidad="derecha",
        puntuacion=0.9,
    )


class TestFiltroBiblioteca(unittest.TestCase):
    def test_filtra_letra_palabra_todas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp)
            guardar_plantilla(
                muestra_estatica_desde_mano(_mano(), "A", categoria="letra"),
                ruta,
            )
            guardar_plantilla(
                muestra_estatica_desde_mano(_mano(), "B", categoria="letra"),
                ruta,
            )
            guardar_plantilla(
                muestra_estatica_desde_mano(_mano(), "HOLA", categoria="palabra"),
                ruta,
            )
            items, errores = inventario_plantillas(ruta)
            self.assertEqual(errores, [])
            self.assertEqual(len(items), 3)

            letras = filtrar_inventario(items, "letra")
            palabras = filtrar_inventario(items, "palabra")
            todas = filtrar_inventario(items, "todas")
            self.assertEqual({i.muestra.etiqueta for i in letras}, {"A", "B"})
            self.assertEqual({i.muestra.etiqueta for i in palabras}, {"HOLA"})
            self.assertEqual(len(todas), 3)
            self.assertEqual(len(filtrar_inventario(items, "")), 3)

            muestras = [i.muestra for i in items]
            self.assertEqual(len(filtrar_por_categoria(muestras, "letra")), 2)
            self.assertEqual(len(filtrar_por_categoria(muestras, "palabra")), 1)


if __name__ == "__main__":
    unittest.main()
