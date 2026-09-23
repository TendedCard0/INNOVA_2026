"""Exporta la biblioteca de señas de Mamatlatolli.

Ejemplo::

    python -m innova.exportar senas.mamatlatolli
    python -m innova.exportar senas.json --desde datos/plantillas
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from innova.config import RUTA_PLANTILLAS
from innova.paquete import ErrorPaquete, exportar_biblioteca
from innova.textos import mensaje_exportacion_lista


def parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m innova.exportar",
        description="Guarda las señas de Mamatlatolli en un archivo para llevarlas a otra computadora.",
    )
    parser.add_argument(
        "ruta",
        help="Dónde guardar el archivo. Si termina en .json, se escribe un solo archivo de texto; si no, un .mamatlatolli.",
    )
    parser.add_argument(
        "--desde",
        default=None,
        help="Carpeta de señas (por omisión: datos/plantillas).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parsear_argumentos(argv)
    origen = Path(args.desde) if args.desde else RUTA_PLANTILLAS
    try:
        resultado = exportar_biblioteca(origen, Path(args.ruta))
    except ErrorPaquete as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(mensaje_exportacion_lista(resultado.conteo, resultado.no_leidas))
    print(resultado.ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
