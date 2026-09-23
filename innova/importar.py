"""Importa un archivo de señas de Mamatlatolli a la biblioteca local.

Ejemplo::

    python -m innova.importar senas.mamatlatolli
    python -m innova.importar senas.mamatlatolli --solo-nuevas --hacia datos/plantillas

Sin diálogo: si una seña ya existe, se reemplaza. ``--solo-nuevas`` deja
intactas las que ya están y solo agrega las que faltan.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from innova.config import RUTA_PLANTILLAS
from innova.paquete import (
    POLITICA_REEMPLAZAR,
    POLITICA_SOLO_NUEVAS,
    ErrorPaquete,
    importar_paquete,
)
from innova.textos import mensaje_importacion_lista


def parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m innova.importar",
        description=(
            "Copia señas de un archivo de Mamatlatolli a este equipo. "
            "Si una letra o palabra ya existe, por omisión se reemplaza."
        ),
    )
    parser.add_argument("ruta", help="Archivo .mamatlatolli o .json exportado desde Mamatlatolli.")
    parser.add_argument(
        "--hacia",
        default=None,
        help="Carpeta de señas. Si se omite, se usa la biblioteca de Mamatlatolli (en desarrollo: datos/plantillas).",
    )
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument(
        "--reemplazar",
        action="store_true",
        help="Sustituye las señas que ya están (mismo nombre, letra o palabra, quieta o con movimiento). Es la opción por omisión.",
    )
    modo.add_argument(
        "--solo-nuevas",
        action="store_true",
        help="No toca las señas que ya están. Solo agrega las que faltan.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parsear_argumentos(argv)
    destino = Path(args.hacia) if args.hacia else RUTA_PLANTILLAS
    politica = POLITICA_SOLO_NUEVAS if args.solo_nuevas else POLITICA_REEMPLAZAR
    try:
        resultado = importar_paquete(Path(args.ruta), destino, politica=politica)
    except ErrorPaquete as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        mensaje_importacion_lista(
            agregadas=resultado.agregadas,
            reemplazadas=resultado.reemplazadas,
            omitidas=resultado.omitidas,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
