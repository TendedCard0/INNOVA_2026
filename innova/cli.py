"""Interfaz de línea de comandos compartida por app.py y python -m innova."""

from __future__ import annotations

import argparse
import sys
import traceback


def registrar_fallos_empaquetado(*, empaquetada: bool | None = None) -> None:
    """En el .exe, un cierre inesperado queda en la carpeta de datos del usuario.

    Sin consola, si no, el fallo desaparece. En desarrollo no cambia
    ``sys.excepthook``.
    """
    from innova.rutas import aplicacion_empaquetada

    activa = aplicacion_empaquetada() if empaquetada is None else empaquetada
    if not activa:
        return

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
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(
                    None,
                    "Mamatlatolli no pudo continuar.\n\n"
                    f"{valor}\n\n"
                    "El detalle quedó en:\n"
                    f"{carpeta / 'mamatlatolli.log'}",
                    "Mamatlatolli",
                    0x10,
                )
            except (AttributeError, OSError):
                return

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
