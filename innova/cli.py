"""Interfaz de línea de comandos compartida por app.py y python -m innova."""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from collections.abc import Callable, Mapping

AvisoFallo = Callable[[str, str], None]


def debe_mostrar_cuadro(
    *,
    plataforma: str | None = None,
    entorno: Mapping[str, str] | None = None,
) -> bool:
    """El cuadro de Windows solo aparece en un equipo real, no en CI.

    ``MessageBoxW`` espera un clic. En el runner de GitHub Actions hay
    escritorio, así que el cuadro no falla: se queda abierto hasta que
    alguien lo cierra y el job no avanza.
    """
    sistema = sys.platform if plataforma is None else plataforma
    variables = os.environ if entorno is None else entorno
    if sistema != "win32":
        return False
    if variables.get("CI") or variables.get("GITHUB_ACTIONS"):
        return False
    return True


def avisar_con_cuadro(mensaje: str, titulo: str = "Mamatlatolli") -> None:
    """Avisa el fallo en un cuadro. No hace nada si no hay que mostrarlo."""
    if not debe_mostrar_cuadro():
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, mensaje, titulo, 0x10)
    except (AttributeError, OSError):
        return


def registrar_fallos_empaquetado(
    *,
    empaquetada: bool | None = None,
    avisar: AvisoFallo | None = None,
) -> None:
    """En el .exe, un cierre inesperado queda en la carpeta de datos del usuario.

    Sin consola, si no, el fallo desaparece. En desarrollo no cambia
    ``sys.excepthook``. ``avisar`` sustituye el cuadro (las pruebas no deben
    abrir uno de verdad).
    """
    from innova.rutas import aplicacion_empaquetada

    activa = aplicacion_empaquetada() if empaquetada is None else empaquetada
    if not activa:
        return
    notificar = avisar_con_cuadro if avisar is None else avisar

    def _gancho(tipo: type[BaseException], valor: BaseException, traza: object) -> None:
        from innova.rutas import ruta_datos_usuario

        carpeta = ruta_datos_usuario()
        detalle = "".join(traceback.format_exception(tipo, valor, traza))  # type: ignore[arg-type]
        try:
            carpeta.mkdir(parents=True, exist_ok=True)
            with (carpeta / "mamatlatolli.log").open("a", encoding="utf-8") as archivo:
                archivo.write(detalle)
                if not detalle.endswith("\n"):
                    archivo.write("\n")
        except OSError:
            pass
        notificar(
            "Mamatlatolli no pudo continuar.\n\n"
            f"{valor}\n\n"
            "El detalle quedó en:\n"
            f"{carpeta / 'mamatlatolli.log'}",
            "Mamatlatolli",
        )

    sys.excepthook = _gancho


def parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="app.py",
        description="Mamatlatolli: prototipo de reconocimiento de Lengua de Señas Mexicana (LSM).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Usa una fuente de video sintética (no requiere cámara física).",
    )
    parser.add_argument(
        "--camara",
        type=int,
        default=0,
        metavar="INDICE",
        help="Índice de la cámara a abrir (por omisión: 0).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    from innova.rutas import aplicacion_empaquetada, preparar_datos_usuario

    if aplicacion_empaquetada():
        registrar_fallos_empaquetado()
    args = parsear_argumentos(argv)
    preparar_datos_usuario()
    from innova.ui import ejecutar_app

    ejecutar_app(modo_demo=args.demo, indice_camara=args.camara)
    return 0


if __name__ == "__main__":
    sys.exit(main())
