"""Sonidos de Mamatlatolli. Clips cortos sintetizados, sin red ni licencias de terceros.

Los WAV de ``assets/sonidos/`` se generan con numpy (tonos y envolvente).
En Windows se reproducen con ``winsound`` (no hace falta FFmpeg). En Linux y
macOS se usa ffplay, paplay o aplay en otro proceso, así el hilo de la cámara
no espera. Si no hay backend, falta el archivo o la salida falla, las
llamadas no hacen nada.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path
from typing import Callable

import numpy as np

RUTA_SONIDOS = Path(__file__).resolve().parent.parent / "assets" / "sonidos"
_FRECUENCIA = 22050
_NOMBRES = ("acierto", "error", "record", "tic", "tac")
_SALIDA_OK: bool | None = None

Lanzador = Callable[[Path], None]


def asegurar_sonidos(carpeta: Path | None = None) -> Path:
    """Crea los WAV que falten. Los que ya están no se reescriben."""
    destino = carpeta if carpeta is not None else RUTA_SONIDOS
    destino.mkdir(parents=True, exist_ok=True)
    pendientes = [nombre for nombre in _NOMBRES if not (destino / f"{nombre}.wav").is_file()]
    if not pendientes:
        return destino
    clips = _sintetizar()
    for nombre in pendientes:
        _escribir_wav(destino / f"{nombre}.wav", clips[nombre])
    return destino


def _sintetizar() -> dict[str, np.ndarray]:
    """Acierto, error, récord y un tic-tac suave. Amplitudes distintas a propósito."""

    def nota(frecuencia: float, duracion: float, *, volumen: float, caida: float) -> np.ndarray:
        n = max(1, int(_FRECUENCIA * duracion))
        t = np.arange(n, dtype=np.float64) / _FRECUENCIA
        envolvente = np.exp(-t / caida)
        ataque = min(n, max(1, int(_FRECUENCIA * 0.008)))
        envolvente[:ataque] *= np.linspace(0.0, 1.0, ataque)
        return np.sin(2.0 * np.pi * frecuencia * t) * envolvente * volumen

    def unir(trozos: list[np.ndarray]) -> np.ndarray:
        return np.concatenate(trozos) if trozos else np.zeros(1, dtype=np.float64)

    return {
        "acierto": unir(
            [
                nota(523.25, 0.11, volumen=0.42, caida=0.06),
                nota(659.25, 0.11, volumen=0.42, caida=0.06),
                nota(783.99, 0.20, volumen=0.46, caida=0.10),
            ]
        ),
        "error": unir(
            [
                nota(392.00, 0.14, volumen=0.40, caida=0.07),
                nota(311.13, 0.26, volumen=0.42, caida=0.11),
            ]
        ),
        "record": unir(
            [
                nota(523.25, 0.09, volumen=0.36, caida=0.05),
                nota(659.25, 0.09, volumen=0.38, caida=0.05),
                nota(783.99, 0.09, volumen=0.40, caida=0.05),
                nota(1046.50, 0.28, volumen=0.48, caida=0.14),
            ]
        ),
        # Más bajo que los eventos: es un reloj de fondo, no un golpe.
        "tic": nota(1760.0, 0.04, volumen=0.16, caida=0.015),
        "tac": nota(1174.0, 0.05, volumen=0.14, caida=0.018),
    }


def _escribir_wav(ruta: Path, onda: np.ndarray) -> None:
    audio = np.clip(onda, -1.0, 1.0)
    pcm = (audio * 32767.0).astype(np.int16)
    with wave.open(str(ruta), "w") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(_FRECUENCIA)
        archivo.writeframes(pcm.tobytes())


def comando_disponible() -> list[str] | None:
    """Programa de reproducción, o None si este equipo no trae uno conocido."""
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error"]
    if shutil.which("paplay"):
        return ["paplay"]
    if shutil.which("aplay"):
        return ["aplay", "-q"]
    return None


def winsound_disponible() -> bool:
    """True en Windows si el módulo estándar ``winsound`` se puede importar."""
    if sys.platform != "win32":
        return False
    try:
        import winsound
    except ImportError:
        return False
    return callable(getattr(winsound, "PlaySound", None))


def backend_utilizable(*, probar: bool) -> str | None:
    """``comando``, ``winsound`` o None.

    En Windows, la ausencia de ffplay/paplay/aplay no apaga el audio: queda
    ``winsound``. La prueba con un programa externo solo corre si ese programa
    existe.
    """
    comando = comando_disponible()
    if comando is not None and (not probar or _comando_abre_audio(comando)):
        return "comando"
    if winsound_disponible():
        return "winsound"
    return None


def salida_de_audio_disponible() -> bool:
    """True si hay un backend que puede abrir un clip. El resultado se recuerda."""
    global _SALIDA_OK
    if _SALIDA_OK is None:
        _SALIDA_OK = _probar_salida()
    return _SALIDA_OK


def _probar_salida() -> bool:
    return backend_utilizable(probar=True) is not None


def _comando_abre_audio(comando: list[str]) -> bool:
    carpeta = asegurar_sonidos()
    ruta = carpeta / "tic.wav"
    if not ruta.is_file():
        return False
    try:
        resultado = subprocess.run(
            [*comando, str(ruta)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    texto = (resultado.stderr or b"").decode("utf-8", errors="ignore").lower()
    if "audio open failed" in texto or "unknown pcm" in texto:
        return False
    return resultado.returncode == 0


class ReproductorSonidos:
    """Reproduce un nombre de ``assets/sonidos`` sin bloquear al llamador."""

    def __init__(
        self,
        carpeta: Path | None = None,
        *,
        lanzar: Lanzador | None = None,
        probar: bool | None = None,
    ) -> None:
        self.carpeta = carpeta if carpeta is not None else RUTA_SONIDOS
        self._lanzar = lanzar
        self._backend: str | None = None
        self._mudo = False
        if lanzar is None:
            if probar is None:
                probar = True
            self._backend = backend_utilizable(probar=probar)
            self._mudo = self._backend is None
            if not self._mudo:
                asegurar_sonidos(self.carpeta)
        elif probar:
            asegurar_sonidos(self.carpeta)

    @property
    def mudo(self) -> bool:
        return self._mudo

    def reproducir(self, nombre: str) -> None:
        if self._mudo:
            return
        ruta = self.carpeta / f"{nombre}.wav"
        if not ruta.is_file():
            return
        if self._lanzar is not None:
            try:
                self._lanzar(ruta)
            except OSError:
                self._mudo = True
            return
        if self._backend == "winsound":
            self._winsound(ruta)
            return
        comando = comando_disponible()
        if comando is None:
            self._mudo = True
            return
        try:
            subprocess.Popen(
                [*comando, str(ruta)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            self._mudo = True

    def _winsound(self, ruta: Path) -> None:
        try:
            import winsound

            resultado = winsound.PlaySound(
                str(ruta),
                winsound.SND_FILENAME | winsound.SND_ASYNC,
            )
        except (ImportError, OSError, RuntimeError):
            self._mudo = True
            return
        if resultado is False:
            self._mudo = True

    def iniciar_reloj(self) -> None:
        return

    def detener_reloj(self) -> None:
        return

    def cerrar(self) -> None:
        return


class RelojMiniJuego:
    """Tic-tac mientras la ronda está en curso. ``pulso`` es el paso testeable."""

    def __init__(
        self,
        reproductor: ReproductorSonidos,
        *,
        intervalo: float = 0.5,
        hilo: bool = True,
    ) -> None:
        self.reproductor = reproductor
        self.intervalo = intervalo
        self._activo = False
        self._paso = 0
        self._cerrar = False
        self._hilo: threading.Thread | None = None
        if hilo:
            self._hilo = threading.Thread(target=self._bucle, name="reloj-mini-juego", daemon=True)
            self._hilo.start()

    @property
    def activo(self) -> bool:
        return self._activo

    def iniciar(self) -> None:
        self._paso = 0
        self._activo = True

    def detener(self) -> None:
        self._activo = False

    def pulso(self) -> str | None:
        if not self._activo:
            return None
        nombre = "tic" if self._paso % 2 == 0 else "tac"
        self._paso += 1
        self.reproductor.reproducir(nombre)
        return nombre

    def cerrar(self) -> None:
        self._cerrar = True
        self._activo = False
        hilo = self._hilo
        if hilo is not None and hilo.is_alive() and threading.current_thread() is not hilo:
            hilo.join(timeout=1.0)

    def _bucle(self) -> None:
        while not self._cerrar:
            if not self._activo:
                time.sleep(0.05)
                continue
            self.pulso()
            limite = time.monotonic() + self.intervalo
            while time.monotonic() < limite and self._activo and not self._cerrar:
                time.sleep(0.05)


class AudioMiniJuego:
    """Fachada que la pantalla usa: eventos puntuales y el reloj de fondo."""

    def __init__(
        self,
        reproductor: ReproductorSonidos | None = None,
        *,
        hilo: bool = True,
        intervalo: float = 0.5,
    ) -> None:
        self.reproductor = reproductor if reproductor is not None else ReproductorSonidos()
        self.reloj = RelojMiniJuego(self.reproductor, intervalo=intervalo, hilo=hilo)

    def reproducir(self, nombre: str) -> None:
        self.reproductor.reproducir(nombre)

    def iniciar_reloj(self) -> None:
        self.reloj.iniciar()

    def detener_reloj(self) -> None:
        self.reloj.detener()

    def cerrar(self) -> None:
        self.reloj.cerrar()
