"""Pruebas del pipeline, la bitácora y la cámara ausente."""

from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch

from innova.camara import Camara, CamaraNoDisponibleError
from innova.cli import parsear_argumentos
from innova.config import ETIQUETA_DETECTANDO
from innova.esquema import muestra_desde_dict
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
                self.assertEqual(data["categoria"], "letra")
                self.assertIsNone(data["pose"])
                self.assertIsNone(data["rostro"])
                self.assertIsNone(data["secuencia"])
                self.assertEqual(len(data["mano"]["landmarks"]), 21)
                self.assertTrue(data["metadatos"]["consentimiento"])
                self.assertEqual(pipeline.n_plantillas, 1)
            finally:
                pipeline.cerrar()

    def test_guardar_plantilla_dinamica_con_secuencia(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = crear_pipeline(modo_demo=True, ruta_plantillas=tmp)
            try:
                pipeline.iniciar_grabacion()
                for _ in range(10):
                    self.assertIsNotNone(pipeline.procesar(reconocer=False))
                frames = pipeline.detener_grabacion()
                self.assertGreaterEqual(len(frames), 6)
                ruta = pipeline.guardar_plantilla("j", tipo="dinamico", fotogramas=frames)
                data = json.loads(ruta.read_text(encoding="utf-8"))
                self.assertEqual(data["etiqueta"], "J")
                self.assertEqual(data["tipo"], "dinamico")
                self.assertEqual(data["categoria"], "letra")
                self.assertIsNone(data["pose"])
                self.assertIsNone(data["rostro"])
                self.assertGreaterEqual(len(data["secuencia"]["fotogramas"]), 6)
                self.assertIsNotNone(data["secuencia"]["fotogramas"][0]["mano"])
                self.assertIsNone(data["secuencia"]["fotogramas"][0]["pose"])
                self.assertEqual(pipeline.n_dinamicas, 1)
                crudo = pipeline.reconocedor.predecir_dinamico(muestra_desde_dict(data))
                self.assertEqual(crudo.etiqueta, "J")
                self.assertGreater(crudo.confianza, 0.7)
            finally:
                pipeline.cerrar()


    def test_guardar_plantilla_palabra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = crear_pipeline(modo_demo=True, ruta_plantillas=tmp, categoria="palabra")
            try:
                self.assertIsNotNone(pipeline.procesar())
                ruta = pipeline.guardar_plantilla("hola", notas="demo", categoria="palabra")
                data = json.loads(ruta.read_text(encoding="utf-8"))
                self.assertEqual(data["etiqueta"], "HOLA")
                self.assertEqual(data["categoria"], "palabra")
                self.assertEqual(pipeline.n_plantillas, 1)
                rec_letra = crear_pipeline(modo_demo=True, ruta_plantillas=tmp, categoria="letra")
                try:
                    self.assertEqual(rec_letra.n_plantillas, 0)
                finally:
                    rec_letra.cerrar()
            finally:
                pipeline.cerrar()

    def test_vocabulario_guarda_pose_y_rostro(self) -> None:
        pose = {"landmarks": [[0.2, 0.3, 0.0]] * 33, "visibilidad": [0.9] * 33}
        rostro = {"landmarks": [[0.45, 0.4, 0.0]] * 478}
        with tempfile.TemporaryDirectory() as tmp:
            with patch("innova.pipeline.anotar_cuerpo", return_value=(pose, rostro)) as anotar:
                pipeline = crear_pipeline(modo_demo=True, ruta_plantillas=tmp, categoria="palabra")
                try:
                    self.assertTrue(pipeline.usar_cuerpo)
                    self.assertIsNotNone(pipeline.procesar())
                    self.assertGreaterEqual(anotar.call_count, 1)
                    ruta = pipeline.guardar_plantilla("gracias", categoria="palabra")
                    data = json.loads(ruta.read_text(encoding="utf-8"))
                    self.assertEqual(len(data["pose"]["landmarks"]), 33)
                    self.assertEqual(len(data["rostro"]["landmarks"]), 478)

                    pipeline.iniciar_grabacion()
                    for _ in range(8):
                        self.assertIsNotNone(pipeline.procesar(reconocer=False))
                    frames = pipeline.detener_grabacion()
                    ruta_d = pipeline.guardar_plantilla(
                        "hola", tipo="dinamico", fotogramas=frames, categoria="palabra"
                    )
                    dinamica = json.loads(ruta_d.read_text(encoding="utf-8"))
                    self.assertEqual(len(dinamica["pose"]["landmarks"]), 33)
                    self.assertIsNotNone(dinamica["secuencia"]["fotogramas"][0]["pose"])
                    self.assertIsNotNone(dinamica["secuencia"]["fotogramas"][0]["rostro"])
                finally:
                    pipeline.cerrar()

    def test_abecedario_no_pide_cuerpo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("innova.pipeline.anotar_cuerpo", return_value=({"landmarks": []}, {"landmarks": []})) as anotar:
                pipeline = crear_pipeline(modo_demo=True, ruta_plantillas=tmp, categoria="letra")
                try:
                    self.assertFalse(pipeline.usar_cuerpo)
                    self.assertIsNotNone(pipeline.procesar())
                    anotar.assert_not_called()
                    ruta = pipeline.guardar_plantilla("a")
                    data = json.loads(ruta.read_text(encoding="utf-8"))
                    self.assertIsNone(data["pose"])
                    self.assertIsNone(data["rostro"])
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
