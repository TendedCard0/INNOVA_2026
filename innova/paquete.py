"""Traslado de la biblioteca de señas de Mamatlatolli entre equipos.

El archivo portable preferido es un ZIP con extensión ``.mamatlatolli``:

- ``manifiesto.json`` — versión del paquete, fecha, conteos e idioma.
- ``plantillas/*.json`` — las mismas muestras que viven en ``datos/plantillas/``.

También se acepta un solo JSON con el mismo manifiesto y las muestras
dentro de ``plantillas``. Sirve para el mismo traslado si conviene un
archivo de texto.

Hoy ``idioma`` va en ``lsm`` y la glosa en ``es-MX``. Es metadata para un
banco futuro de lenguas de señas; este módulo solo copia archivos locales.
No hay servidor ni sincronización.

La misma seña (para decidir un choque) es la glosa, la categoría
(``letra`` / ``palabra``) y si es quieta o con movimiento. Varias tomas
de esa seña se reemplazan o se conservan juntas.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from innova import textos
from innova.config import NOMBRE_PRODUCTO
from innova.esquema import (
    CATEGORIA_LETRA,
    CATEGORIA_PALABRA,
    ErrorEsquema,
    MuestraLSM,
    muestra_desde_dict,
    normalizar_categoria,
    normalizar_etiqueta,
)
from innova.plantillas import (
    asegurar_directorio,
    cargar_plantillas_con_errores,
    eliminar_plantilla,
    guardar_plantilla,
    inventario_plantillas,
    nombre_archivo_seguro,
)

FORMATO_PAQUETE = "mamatlatolli-plantillas"
VERSION_PAQUETE = "1.0"
VERSIONES_PAQUETE = frozenset({"1.0"})
EXTENSION_PAQUETE = ".mamatlatolli"
IDIOMA_POR_OMISION = "lsm"
NOMBRE_IDIOMA_POR_OMISION = "Lengua de Señas Mexicana"
IDIOMA_GLOSA_POR_OMISION = "es-MX"
NOMBRE_MANIFIESTO = "manifiesto.json"
CARPETA_PLANTILLAS = "plantillas"

POLITICA_REEMPLAZAR = "reemplazar"
POLITICA_SOLO_NUEVAS = "solo_nuevas"
POLITICAS = frozenset({POLITICA_REEMPLAZAR, POLITICA_SOLO_NUEVAS})

ClaveSena = tuple[str, str, str]


class ErrorPaquete(ValueError):
    """Archivo de señas ilegible, incompleto o de una versión que esta copia no entiende."""


@dataclass(frozen=True)
class ManifiestoPaquete:
    formato: str
    version: str
    creado: str
    conteo: int
    letras: int
    palabras: int
    quietas: int
    con_movimiento: int
    idioma: str
    nombre_idioma: str
    idioma_glosa: str
    notas: str
    producto: str = NOMBRE_PRODUCTO

    def a_dict(self, *, archivos: list[str] | None = None, plantillas: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        datos: dict[str, Any] = {
            "formato": self.formato,
            "version": self.version,
            "producto": self.producto,
            "creado": self.creado,
            "conteo": self.conteo,
            "letras": self.letras,
            "palabras": self.palabras,
            "quietas": self.quietas,
            "con_movimiento": self.con_movimiento,
            "idioma": self.idioma,
            "nombre_idioma": self.nombre_idioma,
            "idioma_glosa": self.idioma_glosa,
            "notas": self.notas,
        }
        if archivos is not None:
            datos["archivos"] = archivos
        if plantillas is not None:
            datos["plantillas"] = plantillas
        return datos


@dataclass(frozen=True)
class PaquetePlantillas:
    manifiesto: ManifiestoPaquete
    muestras: list[MuestraLSM]


@dataclass(frozen=True)
class ResultadoExportacion:
    ruta: Path
    conteo: int
    letras: int
    palabras: int
    no_leidas: int


@dataclass(frozen=True)
class ResumenConflicto:
    """Grupos de señas (glosa + categoría + quieta/movimiento) que chocan o son nuevas."""

    en_comun: int
    nuevas: int


@dataclass(frozen=True)
class ResultadoImportacion:
    agregadas: int
    reemplazadas: int
    omitidas: int
    eliminadas: int


def clave_sena(muestra: MuestraLSM) -> ClaveSena:
    """Identidad de conflicto: glosa, categoría y si es quieta o con movimiento."""
    return (
        normalizar_categoria(muestra.categoria),
        normalizar_etiqueta(muestra.etiqueta),
        muestra.tipo,
    )


def exportar_biblioteca(
    directorio: Path | None,
    destino: Path,
    *,
    creado: str | None = None,
    notas: str = "",
    idioma: str = IDIOMA_POR_OMISION,
    nombre_idioma: str = NOMBRE_IDIOMA_POR_OMISION,
    idioma_glosa: str = IDIOMA_GLOSA_POR_OMISION,
) -> ResultadoExportacion:
    """Guarda la biblioteca en ``.mamatlatolli`` o, si el nombre termina en ``.json``, en un solo JSON."""
    muestras, no_leidas = _recolectar(directorio)
    if not muestras:
        raise ErrorPaquete(textos.MENSAJE_EXPORTAR_VACIO)
    manifiesto = _manifiesto(
        muestras,
        creado=creado,
        notas=notas,
        idioma=idioma,
        nombre_idioma=nombre_idioma,
        idioma_glosa=idioma_glosa,
    )
    ruta = Path(destino)
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        if ruta.suffix.lower() == ".json":
            _escribir_json(ruta, manifiesto, muestras)
        else:
            if ruta.suffix.lower() != EXTENSION_PAQUETE:
                ruta = ruta.with_suffix(EXTENSION_PAQUETE)
            _escribir_zip(ruta, manifiesto, muestras)
    except OSError as exc:
        raise ErrorPaquete(textos.MENSAJE_NO_SE_PUDO_GUARDAR_ARCHIVO) from exc
    return ResultadoExportacion(
        ruta=ruta,
        conteo=manifiesto.conteo,
        letras=manifiesto.letras,
        palabras=manifiesto.palabras,
        no_leidas=no_leidas,
    )


def leer_paquete(ruta: Path) -> PaquetePlantillas:
    """Lee un ``.mamatlatolli`` o un JSON empaquetado. No modifica la biblioteca."""
    origen = Path(ruta)
    try:
        bruto = origen.read_bytes()
    except OSError as exc:
        raise ErrorPaquete(textos.MENSAJE_ARCHIVO_DANADO) from exc
    if not bruto:
        raise ErrorPaquete(textos.MENSAJE_NO_ES_PAQUETE)
    if bruto[:2] == b"PK":
        return _leer_zip(bruto)
    inicio = bruto.lstrip()[:1]
    if inicio == b"{":
        return _leer_json(bruto)
    raise ErrorPaquete(textos.MENSAJE_NO_ES_PAQUETE)


def resumir_conflicto(directorio: Path | None, paquete: PaquetePlantillas) -> ResumenConflicto:
    locales = _grupos_locales(directorio)
    llegadas = _grupos_muestras(paquete.muestras)
    en_comun = len(set(locales) & set(llegadas))
    nuevas = len(set(llegadas) - set(locales))
    return ResumenConflicto(en_comun=en_comun, nuevas=nuevas)


def aplicar_importacion(
    directorio: Path | None,
    paquete: PaquetePlantillas,
    politica: str,
) -> ResultadoImportacion:
    """Fusiona el paquete ya validado. No escribe nada si la política no se reconoce.

    ``reemplazar`` sustituye cada grupo que coincide y agrega los nuevos.
    ``solo_nuevas`` deja intactos los grupos que ya existen.
    """
    if politica not in POLITICAS:
        raise ErrorPaquete(textos.MENSAJE_POLITICA_DESCONOCIDA)
    if not paquete.muestras:
        raise ErrorPaquete(textos.MENSAJE_PAQUETE_SIN_SENAS)

    destino = asegurar_directorio(directorio)
    locales = _grupos_locales(destino)
    llegadas = _grupos_muestras(paquete.muestras)
    en_comun = set(locales) & set(llegadas)
    nuevas = set(llegadas) - set(locales)

    a_borrar: list[Path] = []
    a_escribir: list[MuestraLSM] = []
    omitidas = 0
    if politica == POLITICA_REEMPLAZAR:
        for clave in en_comun:
            a_borrar.extend(item.ruta for item in locales[clave])
            a_escribir.extend(llegadas[clave])
        for clave in nuevas:
            a_escribir.extend(llegadas[clave])
    else:
        for clave in nuevas:
            a_escribir.extend(llegadas[clave])
        omitidas = sum(len(llegadas[clave]) for clave in en_comun)

    try:
        for ruta in a_borrar:
            eliminar_plantilla(ruta)
        for muestra in a_escribir:
            _preparar_muestra(muestra)
            guardar_plantilla(muestra, destino)
    except OSError as exc:
        raise ErrorPaquete(textos.MENSAJE_NO_SE_PUDO_ACTUALIZAR) from exc

    reemplazadas = sum(len(llegadas[clave]) for clave in en_comun) if politica == POLITICA_REEMPLAZAR else 0
    agregadas = sum(len(llegadas[clave]) for clave in nuevas)
    return ResultadoImportacion(
        agregadas=agregadas,
        reemplazadas=reemplazadas,
        omitidas=omitidas,
        eliminadas=len(a_borrar),
    )


def importar_paquete(
    ruta_archivo: Path,
    directorio: Path | None,
    *,
    politica: str = POLITICA_REEMPLAZAR,
) -> ResultadoImportacion:
    """Lee el archivo y fusiona. Si el archivo no sirve, la biblioteca no cambia."""
    paquete = leer_paquete(ruta_archivo)
    return aplicar_importacion(directorio, paquete, politica)


def _recolectar(directorio: Path | None) -> tuple[list[MuestraLSM], int]:
    muestras, errores = cargar_plantillas_con_errores(directorio)
    muestras.sort(key=_orden_muestra)
    return muestras, len(errores)


def _orden_muestra(muestra: MuestraLSM) -> tuple[str, str, str, str]:
    try:
        etiqueta = normalizar_etiqueta(muestra.etiqueta)
    except ErrorEsquema:
        etiqueta = muestra.etiqueta
    return (muestra.categoria, etiqueta, muestra.tipo, muestra.metadatos.marca_tiempo)


def _manifiesto(
    muestras: list[MuestraLSM],
    *,
    creado: str | None,
    notas: str,
    idioma: str,
    nombre_idioma: str,
    idioma_glosa: str,
) -> ManifiestoPaquete:
    marca = creado or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return ManifiestoPaquete(
        formato=FORMATO_PAQUETE,
        version=VERSION_PAQUETE,
        creado=marca,
        conteo=len(muestras),
        letras=sum(1 for m in muestras if m.categoria == CATEGORIA_LETRA),
        palabras=sum(1 for m in muestras if m.categoria == CATEGORIA_PALABRA),
        quietas=sum(1 for m in muestras if m.tipo == "estatico"),
        con_movimiento=sum(1 for m in muestras if m.tipo == "dinamico"),
        idioma=(idioma or IDIOMA_POR_OMISION).strip() or IDIOMA_POR_OMISION,
        nombre_idioma=(nombre_idioma or NOMBRE_IDIOMA_POR_OMISION).strip() or NOMBRE_IDIOMA_POR_OMISION,
        idioma_glosa=(idioma_glosa or IDIOMA_GLOSA_POR_OMISION).strip() or IDIOMA_GLOSA_POR_OMISION,
        notas=notas or "",
    )


def _nombre_en_paquete(indice: int, muestra: MuestraLSM) -> str:
    try:
        etiqueta = normalizar_etiqueta(muestra.etiqueta)
    except ErrorEsquema:
        etiqueta = muestra.etiqueta or "sena"
    seguro = nombre_archivo_seguro(etiqueta)
    return f"{CARPETA_PLANTILLAS}/{indice:04d}_{seguro}_{muestra.categoria}_{muestra.tipo}.json"


def _escribir_zip(ruta: Path, manifiesto: ManifiestoPaquete, muestras: list[MuestraLSM]) -> None:
    nombres = [_nombre_en_paquete(i, muestra) for i, muestra in enumerate(muestras, start=1)]
    texto_manifiesto = _dumps(manifiesto.a_dict(archivos=nombres))
    with zipfile.ZipFile(ruta, "w", compression=zipfile.ZIP_DEFLATED) as archivo:
        archivo.writestr(NOMBRE_MANIFIESTO, texto_manifiesto)
        for nombre, muestra in zip(nombres, muestras, strict=True):
            archivo.writestr(nombre, _dumps(muestra.a_dict()))


def _escribir_json(ruta: Path, manifiesto: ManifiestoPaquete, muestras: list[MuestraLSM]) -> None:
    datos = manifiesto.a_dict(plantillas=[muestra.a_dict() for muestra in muestras])
    ruta.write_text(_dumps(datos), encoding="utf-8")


def _dumps(datos: dict[str, Any]) -> str:
    return json.dumps(datos, ensure_ascii=False, indent=2) + "\n"


def _leer_zip(bruto: bytes) -> PaquetePlantillas:
    from io import BytesIO

    try:
        with zipfile.ZipFile(BytesIO(bruto)) as archivo:
            originales: dict[str, str] = {}
            for info in archivo.infolist():
                if info.is_dir():
                    continue
                limpio = _miembro_permitido(info.filename)
                originales.setdefault(limpio, info.filename)
            if NOMBRE_MANIFIESTO not in originales:
                raise ErrorPaquete(textos.MENSAJE_PAQUETE_INCOMPLETO)
            try:
                manifiesto_bruto = json.loads(archivo.read(originales[NOMBRE_MANIFIESTO]).decode("utf-8-sig"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ErrorPaquete(textos.MENSAJE_PAQUETE_INCOMPLETO) from exc
            manifiesto = _validar_manifiesto(manifiesto_bruto)
            relativos = _archivos_del_manifiesto(manifiesto_bruto, list(originales))
            muestras = []
            for relativo in relativos:
                try:
                    pieza = json.loads(archivo.read(originales[relativo]).decode("utf-8-sig"))
                except (KeyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
                    raise ErrorPaquete(textos.MENSAJE_SENA_ILEGIBLE) from exc
                muestras.append(_muestra_de_paquete(pieza))
    except ErrorPaquete:
        raise
    except (zipfile.BadZipFile, OSError) as exc:
        raise ErrorPaquete(textos.MENSAJE_ARCHIVO_DANADO) from exc
    _exigir_conteo(manifiesto, muestras)
    return PaquetePlantillas(manifiesto=manifiesto, muestras=muestras)


def _leer_json(bruto: bytes) -> PaquetePlantillas:
    try:
        datos = json.loads(bruto.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ErrorPaquete(textos.MENSAJE_ARCHIVO_DANADO) from exc
    if not isinstance(datos, dict):
        raise ErrorPaquete(textos.MENSAJE_NO_ES_PAQUETE)
    manifiesto = _validar_manifiesto(datos)
    piezas = datos.get("plantillas")
    if not isinstance(piezas, list):
        raise ErrorPaquete(textos.MENSAJE_PAQUETE_INCOMPLETO)
    muestras = [_muestra_de_paquete(pieza) for pieza in piezas]
    _exigir_conteo(manifiesto, muestras)
    return PaquetePlantillas(manifiesto=manifiesto, muestras=muestras)


def _validar_manifiesto(datos: Any) -> ManifiestoPaquete:
    if not isinstance(datos, dict):
        raise ErrorPaquete(textos.MENSAJE_PAQUETE_INCOMPLETO)
    if datos.get("formato") != FORMATO_PAQUETE:
        raise ErrorPaquete(textos.MENSAJE_NO_ES_PAQUETE)
    version = str(datos.get("version") or "").strip()
    if version not in VERSIONES_PAQUETE:
        raise ErrorPaquete(textos.MENSAJE_VERSION_INCOMPATIBLE)
    try:
        conteo = int(datos.get("conteo"))
    except (TypeError, ValueError):
        conteo = -1
    return ManifiestoPaquete(
        formato=FORMATO_PAQUETE,
        version=version,
        creado=str(datos.get("creado") or ""),
        conteo=conteo,
        letras=_entero_suave(datos.get("letras")),
        palabras=_entero_suave(datos.get("palabras")),
        quietas=_entero_suave(datos.get("quietas")),
        con_movimiento=_entero_suave(datos.get("con_movimiento")),
        idioma=str(datos.get("idioma") or IDIOMA_POR_OMISION),
        nombre_idioma=str(datos.get("nombre_idioma") or NOMBRE_IDIOMA_POR_OMISION),
        idioma_glosa=str(datos.get("idioma_glosa") or IDIOMA_GLOSA_POR_OMISION),
        notas=str(datos.get("notas") or ""),
        producto=str(datos.get("producto") or NOMBRE_PRODUCTO),
    )


def _entero_suave(valor: Any) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return 0


def _archivos_del_manifiesto(datos: dict[str, Any], presentes: list[str]) -> list[str]:
    lista = datos.get("archivos")
    if lista is None:
        encontrados = sorted(
            nombre
            for nombre in presentes
            if nombre.startswith(f"{CARPETA_PLANTILLAS}/") and nombre.endswith(".json")
        )
        return encontrados
    if not isinstance(lista, list) or not lista:
        raise ErrorPaquete(textos.MENSAJE_PAQUETE_INCOMPLETO)
    vistos: list[str] = []
    ya: set[str] = set()
    presentes_set = set(presentes)
    for item in lista:
        if not isinstance(item, str):
            raise ErrorPaquete(textos.MENSAJE_PAQUETE_INCOMPLETO)
        nombre = _miembro_permitido(item)
        if not nombre.startswith(f"{CARPETA_PLANTILLAS}/") or not nombre.endswith(".json"):
            raise ErrorPaquete(textos.MENSAJE_PAQUETE_INCOMPLETO)
        if nombre not in presentes_set:
            raise ErrorPaquete(textos.MENSAJE_PAQUETE_INCOMPLETO)
        if nombre in ya:
            continue
        ya.add(nombre)
        vistos.append(nombre)
    if not vistos:
        raise ErrorPaquete(textos.MENSAJE_PAQUETE_SIN_SENAS)
    return vistos


def _miembro_permitido(nombre: str) -> str:
    limpio = nombre.replace("\\", "/").strip()
    if not limpio or limpio.startswith("/") or (len(limpio) >= 2 and limpio[1] == ":"):
        raise ErrorPaquete(textos.MENSAJE_PAQUETE_INCOMPLETO)
    partes = [parte for parte in limpio.split("/") if parte not in {"", "."}]
    if any(parte == ".." for parte in partes):
        raise ErrorPaquete(textos.MENSAJE_PAQUETE_INCOMPLETO)
    return "/".join(partes)


def _muestra_de_paquete(pieza: Any) -> MuestraLSM:
    if not isinstance(pieza, dict):
        raise ErrorPaquete(textos.MENSAJE_SENA_ILEGIBLE)
    try:
        return muestra_desde_dict(pieza)
    except ErrorEsquema as exc:
        raise ErrorPaquete(textos.MENSAJE_SENA_ILEGIBLE) from exc


def _exigir_conteo(manifiesto: ManifiestoPaquete, muestras: list[MuestraLSM]) -> None:
    if not muestras:
        raise ErrorPaquete(textos.MENSAJE_PAQUETE_SIN_SENAS)
    if manifiesto.conteo >= 0 and manifiesto.conteo != len(muestras):
        raise ErrorPaquete(textos.MENSAJE_PAQUETE_INCOMPLETO)


def _grupos_muestras(muestras: list[MuestraLSM]) -> dict[ClaveSena, list[MuestraLSM]]:
    grupos: dict[ClaveSena, list[MuestraLSM]] = {}
    for muestra in muestras:
        grupos.setdefault(clave_sena(muestra), []).append(muestra)
    return grupos


def _grupos_locales(directorio: Path | None) -> dict[ClaveSena, list[Any]]:
    items, _errores = inventario_plantillas(directorio)
    grupos: dict[ClaveSena, list[Any]] = {}
    for item in items:
        grupos.setdefault(clave_sena(item.muestra), []).append(item)
    return grupos


def _preparar_muestra(muestra: MuestraLSM) -> None:
    muestra.etiqueta = normalizar_etiqueta(muestra.etiqueta)
    muestra.categoria = normalizar_categoria(muestra.categoria)
