"""Carga y guarda plantillas LSM en `datos/plantillas/` (JSON versionado)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from innova.config import RUTA_PLANTILLAS
from innova.esquema import (
    CATEGORIA_TODAS,
    ErrorEsquema,
    MuestraLSM,
    muestra_desde_dict,
    normalizar_categoria,
)


@dataclass
class InventarioPlantilla:
    """Una plantilla en disco, con su ruta para listar o borrar."""

    ruta: Path
    muestra: MuestraLSM


def asegurar_directorio(ruta: Path | None = None) -> Path:
    destino = Path(ruta) if ruta is not None else RUTA_PLANTILLAS
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def listar_archivos(ruta: Path | None = None) -> list[Path]:
    destino = Path(ruta) if ruta is not None else RUTA_PLANTILLAS
    if not destino.is_dir():
        return []
    return sorted(p for p in destino.rglob("*.json") if p.is_file())


def cargar_muestra(ruta: Path) -> MuestraLSM:
    try:
        bruto = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ErrorEsquema(f"No se pudo leer {ruta.name}: {exc}") from exc
    return muestra_desde_dict(bruto)


def guardar_muestra(muestra: MuestraLSM, ruta: Path) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(muestra.a_dict(), ensure_ascii=False, indent=2)
    ruta.write_text(texto + "\n", encoding="utf-8")
    return ruta


def guardar_plantilla(muestra: MuestraLSM, directorio: Path | None = None) -> Path:
    destino = asegurar_directorio(directorio)
    seguro = nombre_archivo_seguro(muestra.etiqueta)
    ts = _marca_archivo(muestra.metadatos.marca_tiempo)
    cat = muestra.categoria or "letra"
    ruta = destino / f"{seguro}_{cat}_{muestra.tipo}_{ts}.json"
    if ruta.exists():
        ruta = destino / f"{seguro}_{cat}_{muestra.tipo}_{ts}_{id(muestra) % 10000}.json"
    return guardar_muestra(muestra, ruta)


def cargar_plantillas(ruta: Path | None = None) -> list[MuestraLSM]:
    """Lee todos los JSON válidos; ignora archivos rotos (se reportan aparte)."""
    muestras, _errores = cargar_plantillas_con_errores(ruta)
    return muestras


def cargar_plantillas_con_errores(
    ruta: Path | None = None,
) -> tuple[list[MuestraLSM], list[str]]:
    muestras: list[MuestraLSM] = []
    errores: list[str] = []
    for archivo in listar_archivos(ruta):
        try:
            muestras.append(cargar_muestra(archivo))
        except ErrorEsquema as exc:
            errores.append(f"{archivo.name}: {exc}")
    return muestras, errores


def inventario_plantillas(
    ruta: Path | None = None,
) -> tuple[list[InventarioPlantilla], list[str]]:
    items: list[InventarioPlantilla] = []
    errores: list[str] = []
    for archivo in listar_archivos(ruta):
        try:
            items.append(InventarioPlantilla(ruta=archivo, muestra=cargar_muestra(archivo)))
        except ErrorEsquema as exc:
            errores.append(f"{archivo.name}: {exc}")
    return items, errores


def eliminar_plantilla(ruta: Path) -> None:
    destino = Path(ruta)
    if destino.is_file():
        destino.unlink()


def plantillas_estaticas(muestras: list[MuestraLSM]) -> list[MuestraLSM]:
    return [m for m in muestras if m.tipo == "estatico" and m.mano is not None]


def plantillas_dinamicas(muestras: list[MuestraLSM]) -> list[MuestraLSM]:
    return [m for m in muestras if m.tipo == "dinamico" and m.secuencia is not None]


def filtrar_por_categoria(
    muestras: list[MuestraLSM],
    categoria: str | None = CATEGORIA_TODAS,
) -> list[MuestraLSM]:
    """Filtra por ``letra`` / ``palabra``. ``todas`` o vacío no recorta."""
    if categoria in (None, "", CATEGORIA_TODAS):
        return list(muestras)
    cat = normalizar_categoria(categoria)
    return [m for m in muestras if m.categoria == cat]


def filtrar_inventario(
    items: list[InventarioPlantilla],
    categoria: str | None = CATEGORIA_TODAS,
) -> list[InventarioPlantilla]:
    """Igual que ``filtrar_por_categoria`` sobre el inventario de la biblioteca."""
    if categoria in (None, "", CATEGORIA_TODAS):
        return list(items)
    cat = normalizar_categoria(categoria)
    return [item for item in items if item.muestra.categoria == cat]


def nombre_archivo_seguro(etiqueta: str) -> str:
    seguro = re.sub(r"[^\wÑñ-]+", "_", etiqueta.strip(), flags=re.UNICODE)
    seguro = seguro.strip("_")[:40]
    return seguro or "sena"


def _marca_archivo(marca_tiempo: str) -> str:
    compacto = re.sub(r"[^0-9T]", "", marca_tiempo)
    return compacto[:15] or "sintiestampa"
