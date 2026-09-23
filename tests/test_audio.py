"""Sonidos de Mini juego: clips sintetizados y un reloj que no suena en espera."""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from innova import audio
from innova.audio import (
    AudioMiniJuego,
    RelojMiniJuego,
    ReproductorSonidos,
    asegurar_sonidos,
    backend_utilizable,
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


def _winsound_falso(play) -> types.ModuleType:
    modulo = types.ModuleType("winsound")
    modulo.SND_FILENAME = 0x00020000
    modulo.SND_ASYNC = 0x0001
    modulo.PlaySound = play
    return modulo


class TestWinsoundEnWindows(unittest.TestCase):
    def test_sin_cli_no_queda_mudo_y_llama_a_winsound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = asegurar_sonidos(Path(tmp))
            llamadas: list[tuple[str, int]] = []

            def play(ruta: str, flags: int) -> None:
                llamadas.append((ruta, flags))

            falso = _winsound_falso(play)
            with (
                patch("innova.audio.sys.platform", "win32"),
                patch("innova.audio.comando_disponible", return_value=None),
                patch.dict(sys.modules, {"winsound": falso}),
            ):
                self.assertEqual(backend_utilizable(probar=True), "winsound")
                reproductor = ReproductorSonidos(carpeta, probar=False)
                self.assertFalse(reproductor.mudo)
                reproductor.reproducir("acierto")
                reproductor.reproducir("tic")
            self.assertEqual(len(llamadas), 2)
            ruta, flags = llamadas[0]
            self.assertTrue(ruta.endswith("acierto.wav"))
            self.assertEqual(flags, falso.SND_FILENAME | falso.SND_ASYNC)
            self.assertTrue(llamadas[1][0].endswith("tic.wav"))

    def test_si_winsound_falla_queda_mudo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = asegurar_sonidos(Path(tmp))
            intentos = {"n": 0}

            def play(_ruta: str, _flags: int) -> None:
                intentos["n"] += 1
                raise RuntimeError("sin dispositivo")

            falso = _winsound_falso(play)
            with (
                patch("innova.audio.sys.platform", "win32"),
                patch("innova.audio.comando_disponible", return_value=None),
                patch.dict(sys.modules, {"winsound": falso}),
            ):
                reproductor = ReproductorSonidos(carpeta, probar=False)
                self.assertFalse(reproductor.mudo)
                reproductor.reproducir("error")
                self.assertTrue(reproductor.mudo)
                reproductor.reproducir("error")
            self.assertEqual(intentos["n"], 1)

    def test_probar_salida_en_windows_no_exige_un_programa(self) -> None:
        previo = audio._SALIDA_OK
        falso = _winsound_falso(lambda _ruta, _flags: None)
        try:
            audio._SALIDA_OK = None
            with (
                patch("innova.audio.sys.platform", "win32"),
                patch("innova.audio.comando_disponible", return_value=None),
                patch("innova.audio.subprocess.run") as correr,
                patch.dict(sys.modules, {"winsound": falso}),
            ):
                self.assertTrue(audio._probar_salida())
                correr.assert_not_called()
        finally:
            audio._SALIDA_OK = previo


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
