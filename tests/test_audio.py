"""Sonidos de Mini juego: clips sintetizados y un reloj que no suena en espera."""

from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

from innova.audio import (
    AudioMiniJuego,
    RelojMiniJuego,
    ReproductorSonidos,
    asegurar_sonidos,
)


class TestClips(unittest.TestCase):
    def test_genera_wav_cortos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = asegurar_sonidos(Path(tmp))
            for nombre in ("acierto", "error", "record", "tic", "tac"):
                ruta = carpeta / f"{nombre}.wav"
                self.assertTrue(ruta.is_file(), nombre)
                with wave.open(str(ruta), "rb") as archivo:
                    self.assertEqual(archivo.getnchannels(), 1)
                    self.assertGreater(archivo.getnframes(), 0)
                    self.assertLess(archivo.getnframes() / archivo.getframerate(), 1.2)


class TestReproductor(unittest.TestCase):
    def test_lanza_el_archivo_y_calla_si_falta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            vistos: list[str] = []

            def lanzar(ruta: Path) -> None:
                vistos.append(ruta.name)

            reproductor = ReproductorSonidos(carpeta, lanzar=lanzar, probar=False)
            reproductor.reproducir("acierto")
            self.assertEqual(vistos, [])
            asegurar_sonidos(carpeta)
            reproductor.reproducir("acierto")
            reproductor.reproducir("no-existe")
            self.assertEqual(vistos, ["acierto.wav"])

    def test_un_fallo_del_backend_lo_deja_mudo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = asegurar_sonidos(Path(tmp))

            def lanzar(_ruta: Path) -> None:
                raise OSError("sin salida")

            reproductor = ReproductorSonidos(carpeta, lanzar=lanzar, probar=False)
            reproductor.reproducir("error")
            self.assertTrue(reproductor.mudo)
            reproductor.reproducir("error")


class TestReloj(unittest.TestCase):
    def test_tic_tac_solo_mientras_esta_activo(self) -> None:
        sonados: list[str] = []

        class _Falso(ReproductorSonidos):
            def reproducir(self, nombre: str) -> None:
                sonados.append(nombre)

        reloj = RelojMiniJuego(_Falso(Path("."), lanzar=lambda _ruta: None, probar=False), hilo=False)
        self.assertIsNone(reloj.pulso())
        reloj.iniciar()
        self.assertEqual(reloj.pulso(), "tic")
        self.assertEqual(reloj.pulso(), "tac")
        reloj.detener()
        self.assertIsNone(reloj.pulso())
        self.assertEqual(sonados, ["tic", "tac"])

    def test_fachada_arranca_y_detiene_el_reloj(self) -> None:
        audio = AudioMiniJuego(
            ReproductorSonidos(Path("."), lanzar=lambda _ruta: None, probar=False),
            hilo=False,
        )
        self.assertFalse(audio.reloj.activo)
        audio.iniciar_reloj()
        self.assertTrue(audio.reloj.activo)
        audio.detener_reloj()
        self.assertFalse(audio.reloj.activo)
        audio.cerrar()
        self.assertFalse(audio.reloj.activo)


if __name__ == "__main__":
    unittest.main()
