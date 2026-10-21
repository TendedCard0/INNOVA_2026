"""Ajustes persistentes de Mamatlatolli (JSON simple en datos/config.json)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from innova.config import (
    FOTOGRAMAS_CONSECUTIVOS,
    METRICA_DISTANCIA,
    RUTA_AJUSTES,
    SENSIBILIDAD_MOVIMIENTO,
    UMBRAL_CONFIANZA_LETRA,
    UMBRAL_HISTERSIS,
    UMBRAL_MOVIMIENTO,
    VENTANA_K,
    VENTANA_MOVIMIENTO_S,
    VOTOS_M,
)
from innova.practica import NIVEL_FACIL, NIVEL_MEDIO, NIVELES_ORDEN, normalizar_nivel
from innova.tema import TEMA_CLARO, normalizar_tema


@dataclass
class Ajustes:
    """Knobs que la pantalla de Configuración puede guardar y recargar."""

    umbral_confianza: float = UMBRAL_CONFIANZA_LETRA
    umbral_histeresis: float = UMBRAL_HISTERSIS
    fotogramas_consecutivos: int = FOTOGRAMAS_CONSECUTIVOS
    votos_m: int = VOTOS_M
    ventana_k: int = VENTANA_K
    sensibilidad_movimiento: float = SENSIBILIDAD_MOVIMIENTO
    ventana_movimiento_s: float = VENTANA_MOVIMIENTO_S
    umbral_movimiento: float = UMBRAL_MOVIMIENTO
    metrica: str = METRICA_DISTANCIA
    tema: str = TEMA_CLARO
    # ``record_practica`` es el máximo entre niveles y, en archivos viejos,
    # el único récord. ``records_practica`` guarda uno por nivel.
    record_practica: int = 0
    records_practica: dict[str, int] | None = None
    nivel_practica: str = NIVEL_FACIL

    def normalizado(self) -> Ajustes:
        metrica = self.metrica if self.metrica in {"euclidiana", "coseno"} else METRICA_DISTANCIA
        records = records_efectivos(self.records_practica, self.record_practica)
        resumen = max([_entero_no_negativo(self.record_practica), *records.values()])
        return Ajustes(
            umbral_confianza=_clip(self.umbral_confianza, 0.20, 0.95),
            umbral_histeresis=_clip(self.umbral_histeresis, 0.10, 0.90),
            fotogramas_consecutivos=int(_clip(self.fotogramas_consecutivos, 2, 20)),
            votos_m=int(_clip(self.votos_m, 2, 20)),
            ventana_k=int(_clip(self.ventana_k, 3, 24)),
            sensibilidad_movimiento=_clip(self.sensibilidad_movimiento, 0.0, 1.0),
            ventana_movimiento_s=_clip(self.ventana_movimiento_s, 0.40, 0.80),
            umbral_movimiento=_clip(self.umbral_movimiento, 0.02, 0.30),
            metrica=metrica,
            tema=normalizar_tema(self.tema),
            record_practica=resumen,
            records_practica=records,
            nivel_practica=normalizar_nivel(self.nivel_practica),
        )


def cargar_ajustes(ruta: str | Path | None = None) -> Ajustes:
    destino = Path(ruta) if ruta is not None else RUTA_AJUSTES
    if not destino.is_file():
        return Ajustes().normalizado()
    try:
        bruto = json.loads(destino.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Ajustes().normalizado()
    if not isinstance(bruto, dict):
        return Ajustes().normalizado()
    return _ajustes_desde_bruto(bruto)


def guardar_ajustes(ajustes: Ajustes, ruta: str | Path | None = None) -> Path:
    destino = Path(ruta) if ruta is not None else RUTA_AJUSTES
    destino.parent.mkdir(parents=True, exist_ok=True)
    limpio = ajustes.normalizado()
    destino.write_text(
        json.dumps(asdict(limpio), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destino


def cargar_nivel_practica(ruta: str | Path | None = None) -> str:
    """Último nivel de Mini juego. Fácil si nadie ha jugado; Medio si solo hay récord viejo."""
    return cargar_ajustes(ruta).nivel_practica


def cargar_records_practica(ruta: str | Path | None = None) -> dict[str, int]:
    """Récord de cada nivel. La copia se puede modificar sin tocar el archivo."""
    return dict(cargar_ajustes(ruta).records_practica or {})


def cargar_record_practica(ruta: str | Path | None = None, nivel: str | None = None) -> int:
    """Récord de Mini juego.

    Sin ``nivel``, devuelve el máximo guardado (la clave vieja ``record_practica``).
    Con nivel, devuelve solo el de ese nivel.
    """
    ajustes = cargar_ajustes(ruta)
    if nivel is None:
        return ajustes.record_practica
    records = ajustes.records_practica or {}
    return _entero_no_negativo(records.get(normalizar_nivel(nivel), 0))


def guardar_record_practica(
    puntuacion: int,
    ruta: str | Path | None = None,
    nivel: str | None = None,
) -> int:
    """Escribe el récord solo si ``puntuacion`` lo supera.

    No pisa el tema ni los demás ajustes. Con ``nivel``, sube solo ese nivel
    y devuelve el récord de ese nivel. Sin nivel, mantiene el comportamiento
    anterior: sube el récord único, que al leer pasa al nivel Medio.
    """
    destino = Path(ruta) if ruta is not None else RUTA_AJUSTES
    bruto = _leer_bruto(destino)
    if not bruto:
        bruto = asdict(cargar_ajustes(destino))
    records = records_efectivos(bruto.get("records_practica"), bruto.get("record_practica", 0))
    candidato = _entero_no_negativo(puntuacion)
    if nivel is None:
        records[NIVEL_MEDIO] = max(records[NIVEL_MEDIO], candidato)
        vigente = max(candidato, _entero_no_negativo(bruto.get("record_practica", 0)), *records.values())
        bruto["records_practica"] = records
        bruto["record_practica"] = vigente
        _escribir_bruto(destino, bruto)
        return vigente
    clave = normalizar_nivel(nivel)
    records[clave] = max(records[clave], candidato)
    bruto["records_practica"] = records
    bruto["record_practica"] = max(records.values())
    _escribir_bruto(destino, bruto)
    return records[clave]


def guardar_nivel_practica(nivel: str, ruta: str | Path | None = None) -> str:
    """Recuerda el último nivel de Mini juego sin pisar el resto de ajustes."""
    elegido = normalizar_nivel(nivel)
    destino = Path(ruta) if ruta is not None else RUTA_AJUSTES
    bruto = _leer_bruto(destino)
    if not bruto:
        bruto = asdict(cargar_ajustes(destino))
    bruto["nivel_practica"] = elegido
    _escribir_bruto(destino, bruto)
    return elegido


def guardar_tema(modo: str, ruta: str | Path | None = None) -> str:
    """Escribe solo la clave ``tema`` en config.json, sin pisar otros ajustes."""
    elegido = normalizar_tema(modo)
    destino = Path(ruta) if ruta is not None else RUTA_AJUSTES
    destino.parent.mkdir(parents=True, exist_ok=True)
    bruto: dict[str, Any] = {}
    if destino.is_file():
        try:
            cargado = json.loads(destino.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cargado = None
        if isinstance(cargado, dict):
            bruto = dict(cargado)
    if not bruto:
        bruto = asdict(cargar_ajustes(destino))
    bruto["tema"] = elegido
    destino.write_text(
        json.dumps(bruto, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return elegido


def ajustes_desde_dict(datos: dict[str, Any]) -> Ajustes:
    if not isinstance(datos, dict):
        return Ajustes().normalizado()
    return _ajustes_desde_bruto(datos)


def _ajustes_desde_bruto(bruto: dict[str, Any]) -> Ajustes:
    base = asdict(Ajustes())
    reservadas = {"records_practica", "nivel_practica", "record_practica"}
    for clave in base:
        if clave in bruto and clave not in reservadas:
            base[clave] = bruto[clave]
    records = records_efectivos(bruto.get("records_practica"), bruto.get("record_practica", 0))
    if "nivel_practica" in bruto:
        nivel = normalizar_nivel(str(bruto.get("nivel_practica") or ""))
    elif "records_practica" not in bruto and _entero_no_negativo(bruto.get("record_practica", 0)) > 0:
        nivel = NIVEL_MEDIO
    else:
        nivel = NIVEL_FACIL
    base["records_practica"] = records
    base["nivel_practica"] = nivel
    base["record_practica"] = max(
        [_entero_no_negativo(bruto.get("record_practica", 0)), *records.values()]
    )
    return Ajustes(**base).normalizado()


def records_efectivos(records: Any, legado: Any) -> dict[str, int]:
    """Un entero por nivel. Si solo existe el récord viejo, queda en Medio.

    El juego anterior duraba 5 s, entre Medio (6 s) y Difícil (4 s), y no
    mostraba foto. Medio es el lugar más cercano para no perder esa marca.
    Si ya hay ``records_practica`` pero todos los niveles están en cero y el
    número viejo es mayor, también se rescata: si no, un guardado a medias
    lo dejaría invisible.
    """
    base = {clave: 0 for clave in NIVELES_ORDEN}
    if isinstance(records, dict):
        for clave in NIVELES_ORDEN:
            if clave in records:
                base[clave] = _entero_no_negativo(records[clave])
    legado_n = _entero_no_negativo(legado)
    if legado_n and not any(base.values()):
        base[NIVEL_MEDIO] = legado_n
    return base


def _leer_bruto(destino: Path) -> dict[str, Any]:
    if not destino.is_file():
        return {}
    try:
        cargado = json.loads(destino.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(cargado, dict):
        return {}
    return dict(cargado)


def _escribir_bruto(destino: Path, bruto: dict[str, Any]) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(bruto, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _entero_no_negativo(valor: Any) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        try:
            numero = int(float(valor))
        except (TypeError, ValueError):
            return 0
    return max(0, numero)


def _clip(valor: float, minimo: float, maximo: float) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return minimo
    return max(minimo, min(maximo, numero))
