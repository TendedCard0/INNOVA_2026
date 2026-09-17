"""Carga y guarda plantillas LSM en `datos/plantillas/` (JSON versionado)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from innova.config import RUTA_PLANTILLAS
from innova.esquema import ErrorEsquema, MuestraLSM, muestra_desde_dict


def asegurar_directorio(ruta: Path | None = None) -> Path:
    destino = Path(ruta) if ruta is not None else RUTA_PLANTILLAS
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def listar_archivos(ruta: Path | None = None) -> list[Path]:
    destino = Path(ruta) if ruta is not None else RUTA_PLANTILLAS
    if not destino.is_dir():
        return []
    return sorted(p for p in destino.glob("*.json") if p.is_file())


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
    ruta = destino / f"{seguro}_{muestra.tipo}_{ts}.json"
    if ruta.exists():
        ruta = destino / f"{seguro}_{muestra.tipo}_{ts}_{id(muestra) % 10000}.json"
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


def plantillas_estaticas(muestras: list[MuestraLSM]) -> list[MuestraLSM]:
    return [m for m in muestras if m.tipo == "estatico" and m.mano is not None]


def nombre_archivo_seguro(etiqueta: str) -> str:
    seguro = re.sub(r"[^\wÑñ-]+", "_", etiqueta.strip(), flags=re.UNICODE)
    seguro = seguro.strip("_")[:40]
    return seguro or "sena"


def _marca_archivo(marca_tiempo: str) -> str:
    compacto = re.sub(r"[^0-9T]", "", marca_tiempo)
    return compacto[:15] or "sintiestampa"
