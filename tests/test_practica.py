"""Práctica: puntos, récord (solo el máximo) y el reloj de 5 segundos."""

from __future__ import annotations

import json
import os
import random
import tempfile
import unittest
from pathlib import Path

import numpy as np

from innova.ajustes import (
    Ajustes,
    cargar_ajustes,
    cargar_record_practica,
    guardar_ajustes,
    guardar_record_practica,
    guardar_tema,
)
from innova.camara import esqueleto_mano_normalizado
from innova.detector import ManoDetectada, Punto
from innova.esquema import (
    FotogramaSecuencia,
    mano_desde_deteccion,
    muestra_dinamica_desde_fotogramas,
    muestra_estatica_desde_mano,
)
from innova.estabilidad import FiltroEstabilidad
from innova.pipeline import PipelineVision
from innova.plantillas import guardar_plantilla
from innova.practica import (
    MOTIVO_FALLA,
    MOTIVO_TIEMPO,
    PUNTOS_ACIERTO,
    PartidaPractica,
    elegir_letra,
    letras_estaticas_disponibles,
    record_tras_partida,
)
from innova.reconocimiento import ReconocedorEstatico, ResultadoReconocimiento


def _mano() -> ManoDetectada:
    xy = esqueleto_mano_normalizado(0.5, 0.6, 0.25, 0.0, 0.0)
    return ManoDetectada(
        puntos=[Punto(x, y, 0.0) for x, y in xy],
        lateralidad="derecha",
        puntuacion=0.9,
    )


class _ReconocedorFalso:
    """Sustituye al reconocedor: la prueba decide la etiqueta estable."""

    def __init__(self, etiqueta: str = "—", modo: str = "estatico") -> None:
        self.etiqueta = etiqueta
        self.modo = modo

    def predecir(self, frame: object, manos: object) -> ResultadoReconocimiento:
        del frame, manos
        return ResultadoReconocimiento(
            etiqueta=self.etiqueta,
            confianza=0.91,
            etiqueta_cruda=self.etiqueta,
            confianza_cruda=0.91,
            modo=self.modo,
        )


class TestLetrasDisponibles(unittest.TestCase):
    def test_solo_estaticas_de_letra_sin_repetir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp)
            mano = _mano()
            guardar_plantilla(muestra_estatica_desde_mano(mano, "A", categoria="letra"), ruta)
            guardar_plantilla(muestra_estatica_desde_mano(mano, "a", categoria="letra"), ruta)
            guardar_plantilla(muestra_estatica_desde_mano(mano, "B", categoria="letra"), ruta)
            guardar_plantilla(muestra_estatica_desde_mano(mano, "HOLA", categoria="palabra"), ruta)
            dinamica = muestra_dinamica_desde_fotogramas(
                "J",
                [FotogramaSecuencia(t=0.0, mano=mano_desde_deteccion(mano))],
                categoria="letra",
            )
            guardar_plantilla(dinamica, ruta)
            self.assertEqual(letras_estaticas_disponibles(ruta), ["A", "B"])

    def test_carpeta_vacia(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(letras_estaticas_disponibles(Path(tmp)), [])


class TestPuntuacionYReloj(unittest.TestCase):
    def test_acierto_suma_y_cambia_letra_sin_repetir(self) -> None:
        rng = random.Random(0)
        partida = PartidaPractica(["A", "B", "C"], record=4, duracion_s=5.0, rng=rng)
        self.assertEqual(PUNTOS_ACIERTO, 1)
        t = 0.0
        for _ in range(12):
            objetivo = partida.letra
            t += 0.4
            vista = partida.observar(t, objetivo.lower(), comprometida=True)
            self.assertTrue(vista.acierto)
            self.assertFalse(vista.terminado)
            self.assertNotEqual(vista.letra, objetivo)
            self.assertAlmostEqual(vista.restante_s, 5.0, places=5)
            t += 0.1
            suelta = partida.observar(t, "—", comprometida=False)
            self.assertFalse(suelta.acierto)
            self.assertFalse(suelta.terminado)
        self.assertEqual(partida.puntuacion, 12)

    def test_sostener_el_acierto_no_suma_otra_vez_ni_falla(self) -> None:
        partida = PartidaPractica(["A"], duracion_s=5.0, rng=random.Random(1))
        vista = partida.observar(0.2, "A", comprometida=True)
        self.assertTrue(vista.acierto)
        self.assertEqual(vista.puntuacion, 1)
        sigue = partida.observar(0.5, "A", comprometida=True)
        self.assertFalse(sigue.acierto)
        self.assertFalse(sigue.terminado)
        self.assertEqual(sigue.puntuacion, 1)
        partida.observar(0.6, None, comprometida=False)
        otra = partida.observar(0.9, "A", comprometida=True)
        self.assertTrue(otra.acierto)
        self.assertEqual(otra.puntuacion, 2)

    def test_parpadeo_sin_compromiso_no_cuenta(self) -> None:
        partida = PartidaPractica(["A", "B"], rng=random.Random(2))
        objetivo = partida.letra
        vista = partida.observar(1.0, objetivo, comprometida=False)
        self.assertFalse(vista.acierto)
        self.assertFalse(vista.terminado)
        self.assertEqual(vista.puntuacion, 0)
        marcador = partida.observar(1.2, "detectando…", comprometida=True)
        self.assertFalse(marcador.acierto)
        self.assertFalse(marcador.terminado)

    def test_letra_equivocada_estable_termina_la_partida(self) -> None:
        partida = PartidaPractica(["A", "B"], record=5, rng=random.Random(3))
        otra = next(letra for letra in partida.letras if letra != partida.letra)
        vista = partida.observar(1.5, otra, comprometida=True)
        self.assertTrue(vista.terminado)
        self.assertEqual(vista.motivo, MOTIVO_FALLA)
        self.assertEqual(vista.puntuacion, 0)
        self.assertFalse(vista.nuevo_record)
        self.assertEqual(vista.record, 5)
        repetida = partida.observar(2.0, partida.letra, comprometida=True)
        self.assertTrue(repetida.terminado)
        self.assertEqual(repetida.puntuacion, 0)

    def test_se_acaba_el_tiempo_sin_acierto(self) -> None:
        partida = PartidaPractica(["A", "B"], record=2, duracion_s=5.0, rng=random.Random(4))
        partida.observar(0.0, None, comprometida=False)
        justo = partida.observar(5.0, None, comprometida=False)
        self.assertTrue(justo.terminado)
        self.assertEqual(justo.motivo, MOTIVO_TIEMPO)
        self.assertEqual(justo.puntuacion, 0)
        self.assertEqual(justo.record, 2)
        self.assertFalse(justo.nuevo_record)
        self.assertEqual(justo.restante_s, 0.0)

    def test_acierto_en_el_limite_y_tarde_no(self) -> None:
        a_tiempo = PartidaPractica(["Z"], duracion_s=5.0)
        a_tiempo.observar(0.0, None, comprometida=False)
        vista = a_tiempo.observar(5.0, "Z", comprometida=True)
        self.assertTrue(vista.acierto)
        self.assertEqual(vista.puntuacion, 1)
        self.assertFalse(vista.terminado)

        tarde = PartidaPractica(["Z"], duracion_s=5.0)
        tarde.observar(0.0, None, comprometida=False)
        vencida = tarde.observar(5.01, "Z", comprometida=True)
        self.assertFalse(vencida.acierto)
        self.assertTrue(vencida.terminado)
        self.assertEqual(vencida.motivo, MOTIVO_TIEMPO)
        self.assertEqual(vencida.puntuacion, 0)

    def test_tras_acierto_el_reloj_vuelve_a_empezar(self) -> None:
        partida = PartidaPractica(["A", "B"], duracion_s=5.0, rng=random.Random(5))
        objetivo = partida.letra
        partida.observar(1.0, objetivo, comprometida=True)
        sigue = partida.observar(5.9, None, comprometida=False)
        self.assertFalse(sigue.terminado)
        self.assertEqual(sigue.puntuacion, 1)
        fin = partida.observar(6.0, None, comprometida=False)
        self.assertTrue(fin.terminado)
        self.assertEqual(fin.motivo, MOTIVO_TIEMPO)
        self.assertEqual(fin.puntuacion, 1)

    def test_record_solo_si_supera(self) -> None:
        self.assertEqual(record_tras_partida(3, 5), (5, False))
        self.assertEqual(record_tras_partida(5, 5), (5, False))
        self.assertEqual(record_tras_partida(6, 5), (6, True))
        self.assertEqual(record_tras_partida(0, 0), (0, False))

        empata = self._partida_con_puntos(3, record=3)
        self.assertTrue(empata.terminado)
        self.assertFalse(empata.nuevo_record)
        self.assertEqual(empata.record, 3)

        supera = self._partida_con_puntos(2, record=1)
        self.assertTrue(supera.nuevo_record)
        self.assertEqual(supera.record, 2)
        self.assertEqual(supera.puntuacion, 2)

    def test_reconocedor_falso_acierto_y_tiempo(self) -> None:
        falso = _ReconocedorFalso()
        partida = PartidaPractica(["A", "M"], duracion_s=5.0, rng=random.Random(7))
        falso.etiqueta = "detectando…"
        arranque = partida.observar_resultado(0.0, falso.predecir(None, []))
        self.assertFalse(arranque.acierto)
        self.assertFalse(arranque.terminado)

        falso.etiqueta = partida.letra
        acierto = partida.observar_resultado(1.0, falso.predecir(None, []))
        self.assertTrue(acierto.acierto)
        self.assertEqual(acierto.puntuacion, 1)

        # La estimación cruda no se consulta: si la estable no coincide, no hay punto.
        cruda = ResultadoReconocimiento(
            etiqueta="detectando…",
            confianza=0.0,
            etiqueta_cruda=partida.letra,
            confianza_cruda=0.99,
            modo="estatico",
        )
        partida.observar(1.1, None, comprometida=False)
        sin_punto = partida.observar_resultado(1.3, cruda)
        self.assertFalse(sin_punto.acierto)
        self.assertEqual(sin_punto.puntuacion, 1)

        # Una trayectoria (DTW) no cierra ni suma en Práctica.
        dinamica = ResultadoReconocimiento(
            etiqueta=partida.letra,
            confianza=0.95,
            modo="dinamico",
        )
        ignorada = partida.observar_resultado(1.5, dinamica)
        self.assertFalse(ignorada.acierto)
        self.assertFalse(ignorada.terminado)

        falso.etiqueta = "—"
        fin = partida.observar_resultado(1.0 + 5.0, falso.predecir(None, []))
        self.assertTrue(fin.terminado)
        self.assertEqual(fin.motivo, MOTIVO_TIEMPO)
        self.assertEqual(fin.puntuacion, 1)

    def test_no_repite_si_hay_otra_letra(self) -> None:
        rng = random.Random(9)
        anterior = "A"
        for _ in range(30):
            elegida = elegir_letra(["A", "B", "C"], anterior, rng)
            self.assertNotEqual(elegida, anterior)
            anterior = elegida
        self.assertEqual(elegir_letra(["Ñ"], "Ñ", rng), "Ñ")

    def _partida_con_puntos(self, puntos: int, *, record: int):
        partida = PartidaPractica(["A"], record=record, duracion_s=5.0)
        t = 0.0
        for _ in range(puntos):
            t += 0.2
            partida.observar(t, "A", comprometida=True)
            t += 0.05
            partida.observar(t, None, comprometida=False)
        return partida.observar(t + 5.0, None, comprometida=False)


class TestRecordPersistente(unittest.TestCase):
    def test_solo_guarda_el_maximo_y_no_pisa_el_tema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            guardar_ajustes(
                Ajustes(umbral_confianza=0.77, metrica="coseno", tema="oscuro", record_practica=3),
                ruta,
            )
            self.assertEqual(guardar_record_practica(1, ruta), 3)
            self.assertEqual(cargar_record_practica(ruta), 3)
            bruto = json.loads(ruta.read_text(encoding="utf-8"))
            self.assertEqual(bruto["record_practica"], 3)
            self.assertEqual(bruto["tema"], "oscuro")
            self.assertAlmostEqual(bruto["umbral_confianza"], 0.77, places=5)

            self.assertEqual(guardar_record_practica(8, ruta), 8)
            self.assertEqual(cargar_ajustes(ruta).record_practica, 8)
            self.assertEqual(cargar_ajustes(ruta).metrica, "coseno")
            self.assertEqual(guardar_tema("claro", ruta), "claro")
            self.assertEqual(cargar_record_practica(ruta), 8)
            self.assertEqual(cargar_ajustes(ruta).tema, "claro")

    def test_archivo_nuevo_y_valor_invalido(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            self.assertEqual(cargar_record_practica(ruta), 0)
            self.assertEqual(guardar_record_practica(4, ruta), 4)
            self.assertTrue(ruta.is_file())
            ruta.write_text(json.dumps({"record_practica": -9, "tema": "oscuro"}), encoding="utf-8")
            self.assertEqual(cargar_record_practica(ruta), 0)
            self.assertEqual(guardar_record_practica(2, ruta), 2)
            bruto = json.loads(ruta.read_text(encoding="utf-8"))
            self.assertEqual(bruto["tema"], "oscuro")
            self.assertEqual(bruto["record_practica"], 2)


class TestGanchoEstatico(unittest.TestCase):
    def test_solo_estatico_no_graba_y_el_filtro_se_reinicia(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            filtro = FiltroEstabilidad(consecutivos=2, votos_m=2, ventana_k=3)
            reconocedor = ReconocedorEstatico(Path(tmp), filtro=filtro)
            reconocedor.set_forzar_dinamico(True)
            reconocedor.set_solo_estatico(True)
            frame = np.zeros((32, 32, 3), dtype=np.uint8)
            resultado = reconocedor.predecir(frame, [_mano()])
            self.assertEqual(resultado.modo, "estatico")
            filtro._comprometida = "A"
            reconocedor.reiniciar_filtro()
            self.assertIsNone(filtro._comprometida)

    def test_pipeline_prepara_practica(self) -> None:
        class _Fuente:
            def leer(self):
                return None

            def descripcion(self) -> str:
                return "prueba"

        class _Rec:
            def __init__(self) -> None:
                self.categoria = "letra"
                self.solo = False
                self.reinicios = 0

            def set_solo_estatico(self, activo: bool) -> None:
                self.solo = activo

            def reiniciar_filtro(self) -> None:
                self.reinicios += 1

        rec = _Rec()
        pipeline = PipelineVision(_Fuente(), object(), rec)  # type: ignore[arg-type]
        pipeline.set_solo_estatico(True)
        pipeline.reiniciar_estabilidad()
        self.assertTrue(rec.solo)
        self.assertEqual(rec.reinicios, 1)


@unittest.skipUnless(os.environ.get("DISPLAY"), "requiere un display gráfico")
class TestPantallaPractica(unittest.TestCase):
    def test_vacio_y_partida_en_espanol(self) -> None:
        try:
            import tkinter  # noqa: F401
            import customtkinter as ctk
        except ImportError:
            self.skipTest("requiere tkinter")

        from innova import ajustes, plantillas, tema
        from innova.pantallas import PantallaPractica

        tema.aplicar_tema("claro")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            vacio = base / "vacio"
            banco = base / "banco"
            vacio.mkdir()
            banco.mkdir()
            config = base / "config.json"
            mano = _mano()
            guardar_plantilla(muestra_estatica_desde_mano(mano, "A", categoria="letra"), banco)
            guardar_plantilla(muestra_estatica_desde_mano(mano, "L", categoria="letra"), banco)
            ajustes_previos = ajustes.RUTA_AJUSTES
            plantillas_previas = plantillas.RUTA_PLANTILLAS
            ajustes.RUTA_AJUSTES = config
            raiz = ctk.CTk()
            raiz.withdraw()
            try:
                plantillas.RUTA_PLANTILLAS = vacio
                pantalla = PantallaPractica(
                    raiz,
                    modo_demo=True,
                    indice_camara=0,
                    ajustes=Ajustes(),
                    on_volver=lambda: None,
                )
                raiz.update()
                self.assertIn("Capturar plantillas", pantalla.marco_vacio.winfo_children()[1].cget("text"))
                self.assertIn("Mamatlatolli", pantalla.marco_vacio.winfo_children()[1].cget("text"))
                pantalla.cerrar_pantalla()

                plantillas.RUTA_PLANTILLAS = banco
                pantalla = PantallaPractica(
                    raiz,
                    modo_demo=True,
                    indice_camara=0,
                    ajustes=Ajustes(),
                    on_volver=lambda: None,
                )
                raiz.update()
                self.assertIn(pantalla.lbl_letra.cget("text"), {"A", "L"})
                self.assertEqual(pantalla.lbl_tiempo.cget("text"), "5.0 s")
                self.assertEqual(pantalla.lbl_puntos.cget("text"), "Puntos: 0")
                self.assertIn("Récord", pantalla.lbl_record.cget("text"))
                pantalla.cerrar_pantalla()
            finally:
                ajustes.RUTA_AJUSTES = ajustes_previos
                plantillas.RUTA_PLANTILLAS = plantillas_previas
                raiz.destroy()


if __name__ == "__main__":
    unittest.main()
