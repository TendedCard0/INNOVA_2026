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
    # Récord de Mini juego. Solo sube; guardar_record_practica no lo baja.
    record_practica: int = 0

    def normalizado(self) -> Ajustes:
        metrica = self.metrica if self.metrica in {"euclidiana", "coseno"} else METRICA_DISTANCIA
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
            record_practica=_entero_no_negativo(self.record_practica),
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
    base = asdict(Ajustes())
    for clave in base:
        if clave in bruto:
            base[clave] = bruto[clave]
    return Ajustes(**base).normalizado()


def guardar_ajustes(ajustes: Ajustes, ruta: str | Path | None = None) -> Path:
    destino = Path(ruta) if ruta is not None else RUTA_AJUSTES
    destino.parent.mkdir(parents=True, exist_ok=True)
    limpio = ajustes.normalizado()
    destino.write_text(
        json.dumps(asdict(limpio), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destino


def cargar_record_practica(ruta: str | Path | None = None) -> int:
    """Récord personal de Mini juego guardado en ``datos/config.json``."""
    return cargar_ajustes(ruta).record_practica


def guardar_record_practica(puntuacion: int, ruta: str | Path | None = None) -> int:
    """Escribe el récord solo si ``puntuacion`` lo supera.

    No pisa el tema ni los demás ajustes. Si la puntuación es menor o igual,
    el archivo queda como estaba y se devuelve el récord ya guardado.
    """
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
    actual = _entero_no_negativo(bruto.get("record_practica", 0))
    candidato = _entero_no_negativo(puntuacion)
    vigente = max(actual, candidato)
    bruto["record_practica"] = vigente
    destino.write_text(
        json.dumps(bruto, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return vigente


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
    base = asdict(Ajustes())
    for clave in base:
        if clave in datos:
            base[clave] = datos[clave]
    return Ajustes(**base).normalizado()


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
