"""Copia visible: estados vacíos, cámara y cierre del mini juego."""

from __future__ import annotations

import unittest

from innova.config import MENSAJE_CAMARA_AUSENTE
from innova.practica import MOTIVO_FALLA, MOTIVO_TIEMPO, VistaPractica, texto_fin
from innova import textos


class TestMensajesVisibles(unittest.TestCase):
    def test_camara_no_pide_comandos(self) -> None:
        self.assertNotIn("python", MENSAJE_CAMARA_AUSENTE.lower())
        self.assertNotIn("--demo", MENSAJE_CAMARA_AUSENTE.lower())
        self.assertIn("Reintentar cámara", MENSAJE_CAMARA_AUSENTE)
        self.assertIn("Modo demostración", MENSAJE_CAMARA_AUSENTE)
        self.assertIn("Reintentar cámara", " ".join(textos.LINEAS_CAMARA_VIDEO))

    def test_vacios_invitan_a_capturar(self) -> None:
        for titulo, detalle in (
            textos.texto_vacio_biblioteca("Todas"),
            textos.texto_vacio_biblioteca("Letra"),
            textos.texto_vacio_biblioteca("Palabra"),
            textos.texto_vacio_reconocimiento("letra"),
            textos.texto_vacio_reconocimiento("palabra"),
        ):
            junto = f"{titulo} {detalle}".lower()
            self.assertIn("capturar plantillas", junto)
            self.assertNotIn("dtw", junto)
            self.assertNotIn("error", junto)
        titulo_captura, detalle_captura = textos.texto_vacio_captura()
        junto_captura = f"{titulo_captura} {detalle_captura}".lower()
        self.assertIn("guardar", junto_captura)
        self.assertIn("abecedario", junto_captura)
        self.assertNotIn("dtw", junto_captura)
        self.assertIn("Capturar plantillas", textos.DETALLE_MINIJUEGO_VACIO)
        self.assertIn("Mamatlatolli", textos.DETALLE_MINIJUEGO_VACIO)
        self.assertIn("letras", textos.titulo_vacio_minijuego().lower())

    def test_banco_vacio_en_abecedario_y_vocabulario(self) -> None:
        letras = textos.mensaje_banco_vacio("letra").lower()
        palabras = textos.mensaje_banco_vacio("palabra").lower()
        self.assertIn("capturar plantillas", letras)
        self.assertIn("letra", letras)
        self.assertIn("vocabulario", palabras)
        self.assertIn("palabra", palabras)
        self.assertNotIn("dtw", letras)
        self.assertNotIn("dtw", palabras)

    def test_acierto_tiempo_y_falla_del_mini_juego(self) -> None:
        tiempo = texto_fin(
            VistaPractica(
                letra="A",
                puntuacion=700,
                record=1000,
                restante_s=0,
                acierto=False,
                terminado=True,
                motivo=MOTIVO_TIEMPO,
                nuevo_record=False,
            )
        )
        falla = texto_fin(
            VistaPractica(
                letra="A",
                puntuacion=1000,
                record=1000,
                restante_s=2,
                acierto=False,
                terminado=True,
                motivo=MOTIVO_FALLA,
                nuevo_record=True,
            )
        )
        self.assertIn("Se acabó el tiempo", tiempo)
        self.assertIn("700", tiempo)
        self.assertIn("1000", tiempo)
        self.assertIn("no era la letra", falla)
        self.assertIn("Nuevo récord", falla)
        self.assertIn("1000", textos.mensaje_acierto(1000))

    def test_guardado_y_ajustes_sin_rutas(self) -> None:
        aviso = textos.mensaje_plantilla_guardada("hola", palabra=True, dinamica=False)
        self.assertIn("HOLA", aviso)
        self.assertIn("Listo", aviso)
        self.assertNotIn(".json", aviso)
        self.assertNotIn("datos/", textos.MENSAJE_AJUSTES_GUARDADOS)
        self.assertNotIn("DTW", textos.ETIQUETA_SENSIBILIDAD)
        self.assertNotIn("Histéresis", textos.ETIQUETA_MANTENER)
        self.assertNotIn("json", textos.SUBTITULO_CONFIG.lower())

    def test_modo_y_lectura_sin_jerga(self) -> None:
        self.assertNotIn("DTW", textos.texto_modo("dinamico", True))
        self.assertIn("movimiento", textos.texto_modo("dinamico", False))
        self.assertEqual(textos.etiqueta_visible("detectando…"), "Buscando…")
        self.assertEqual(textos.texto_fuente("Cámara 0"), "Cámara lista")
        self.assertNotIn("fotograma", textos.mensaje_grabando().lower())
        self.assertNotIn("histéresis", textos.mensaje_mantener_sena().lower())


if __name__ == "__main__":
    unittest.main()
