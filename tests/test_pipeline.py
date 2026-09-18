"""Pruebas del pipeline, la bitácora y la cámara ausente."""

from __future__ import annotations

import json
import tempfile
import unittest

from innova.camara import Camara, CamaraNoDisponibleError
from innova.cli import parsear_argumentos
from innova.config import ETIQUETA_DETECTANDO
from innova.pipeline import BitacoraTranscripcion, crear_pipeline


class TestPipelineDemo(unittest.TestCase):
    def test_un_fotograma_demo_trae_mano_y_marcador(self) -> None:
        pipeline = crear_pipeline(modo_demo=True)
        try:
            procesado = pipeline.procesar()
            self.assertIsNotNone(procesado)
            assert procesado is not None
            self.assertGreaterEqual(len(procesado.manos), 1)
            self.assertEqual(procesado.resultado.etiqueta, ETIQUETA_DETECTANDO)
            self.assertIn("demostración", procesado.fuente.lower())
            self.assertGreater(int(procesado.imagen.sum()), 0)
            self.assertEqual(procesado.transcripcion, [])
        finally:
            pipeline.cerrar()

    def test_guardar_plantilla_estatica_con_pose_nula(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = crear_pipeline(modo_demo=True, ruta_plantillas=tmp)
            try:
                self.assertIsNotNone(pipeline.procesar())
                ruta = pipeline.guardar_plantilla("a", notas="demo")
                self.assertTrue(ruta.is_file())
                data = json.loads(ruta.read_text(encoding="utf-8"))
                self.assertEqual(data["etiqueta"], "A")
                self.assertEqual(data["tipo"], "estatico")
                self.assertIsNone(data["pose"])
                self.assertIsNone(data["rostro"])
                self.assertIsNone(data["secuencia"])
                self.assertEqual(len(data["mano"]["landmarks"]), 21)
                self.assertTrue(data["metadatos"]["consentimiento"])
                self.assertEqual(pipeline.n_plantillas, 1)
            finally:
                pipeline.cerrar()


class TestBitacora(unittest.TestCase):
    def test_ignora_marcadores_y_acumula_letras(self) -> None:
        bitacora = BitacoraTranscripcion(max_lineas=3, intervalo_s=0.0)
        bitacora.registrar("—")
        bitacora.registrar("detectando…")
        bitacora.registrar("A")
        self.assertEqual(len(bitacora.lineas()), 1)
        self.assertTrue(bitacora.lineas()[0].endswith("A"))


class TestCamaraAusente(unittest.TestCase):
    def test_indice_invalido_lanza_error_en_espanol(self) -> None:
        with self.assertRaises(CamaraNoDisponibleError) as ctx:
            Camara(indice_preferido=99)
        self.assertIn("cámara", str(ctx.exception).lower())


class TestCLI(unittest.TestCase):
    def test_demo_y_camara(self) -> None:
        args = parsear_argumentos(["--demo", "--camara", "2"])
        self.assertTrue(args.demo)
        self.assertEqual(args.camara, 2)


if __name__ == "__main__":
    unittest.main()
