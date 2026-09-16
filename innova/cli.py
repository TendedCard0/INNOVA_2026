"""Interfaz de línea de comandos compartida por app.py y python -m innova."""

from __future__ import annotations

import argparse
import sys


def parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="app.py",
        description="INNOVA 2026: prototipo de reconocimiento de Lengua de Señas Mexicana (LSM).",
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
    args = parsear_argumentos(argv)
    from innova.ui import ejecutar_app

    ejecutar_app(modo_demo=args.demo, indice_camara=args.camara)
    return 0


if __name__ == "__main__":
    sys.exit(main())
