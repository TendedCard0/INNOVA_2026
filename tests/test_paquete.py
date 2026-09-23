"""Empaquetado, fusión y validación del archivo de señas de Mamatlatolli."""

from __future__ import annotations

import io
import json
import os
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from innova.camara import esqueleto_mano_normalizado
from innova.detector import ManoDetectada, Punto
from innova.esquema import FotogramaSecuencia, muestra_dinamica_desde_fotogramas, muestra_estatica_desde_mano
from innova.exportar import main as main_exportar
from innova.importar import main as main_importar
from innova.paquete import (
    FORMATO_PAQUETE,
    POLITICA_REEMPLAZAR,
    POLITICA_SOLO_NUEVAS,
    VERSION_PAQUETE,
    ErrorPaquete,
    aplicar_importacion,
    exportar_biblioteca,
    importar_paquete,
    leer_paquete,
    resumir_conflicto,
)
from innova.plantillas import cargar_plantillas, guardar_plantilla, inventario_plantillas
from innova.reconocimiento import crear_reconocedor
from innova import textos


def _mano() -> ManoDetectada:
    xy = esqueleto_mano_normalizado(0.5, 0.6, 0.25, 0.0, 0.0)
    return ManoDetectada(
        puntos=[Punto(x, y, 0.0) for x, y in xy],
        lateralidad="derecha",
        puntuacion=0.9,
    )


def _estatica(etiqueta: str, **kwargs):
    return muestra_estatica_desde_mano(_mano(), etiqueta, notas=kwargs.pop("notas", "toma"), **kwargs)


def _dinamica(etiqueta: str, *, fotogramas: int = 6, **kwargs):
    mano = _estatica("tmp").mano
    frames = [FotogramaSecuencia(t=round(i * 0.04, 4), mano=mano) for i in range(fotogramas)]
    return muestra_dinamica_desde_fotogramas(etiqueta, frames, notas=kwargs.pop("notas", "trayecto"), **kwargs)


def _firma(muestras) -> list[str]:
    return sorted(json.dumps(m.a_dict(), ensure_ascii=False, sort_keys=True) for m in muestras)


def _poblar(directorio: Path) -> None:
    guardar_plantilla(_estatica("A", notas="letra-a", categoria="letra"), directorio)
    guardar_plantilla(_estatica("A", notas="letra-a-2", categoria="letra"), directorio)
    guardar_plantilla(_dinamica("J", notas="letra-j", categoria="letra"), directorio)
    guardar_plantilla(
        _estatica(
            "HOLA",
            notas="hola",
            categoria="palabra",
            pose={"landmarks": [[0.2, 0.3, 0.0]], "visibilidad": [0.95]},
            rostro={"landmarks": [[0.4, 0.5, 0.1]]},
        ),
        directorio,
    )


def _manifiesto_minimo(**extra) -> dict:
    datos = {
        "formato": FORMATO_PAQUETE,
        "version": VERSION_PAQUETE,
        "producto": "Mamatlatolli",
        "creado": "2026-09-23T00:00:00+00:00",
        "conteo": 1,
        "idioma": "lsm",
        "idioma_glosa": "es-MX",
    }
    datos.update(extra)
    return datos


class TestEmpaquetado(unittest.TestCase):
    def test_zip_redondo_conserva_letras_palabras_y_cuerpo(self) -> None:
        with self._dirs() as (origen, destino, archivo):
            _poblar(origen)
            originales = cargar_plantillas(origen)
            resultado = exportar_biblioteca(origen, archivo, creado="2026-09-23T00:00:00+00:00")
            self.assertEqual(resultado.conteo, 4)
            self.assertEqual(resultado.letras, 3)
            self.assertEqual(resultado.palabras, 1)
            self.assertEqual(resultado.ruta.suffix, ".mamatlatolli")

            with zipfile.ZipFile(resultado.ruta) as paquete:
                nombres = paquete.namelist()
                self.assertIn("manifiesto.json", nombres)
                self.assertTrue(all(not n.startswith("/") and ".." not in n for n in nombres))
                manifiesto = json.loads(paquete.read("manifiesto.json"))
            self.assertEqual(manifiesto["formato"], FORMATO_PAQUETE)
            self.assertEqual(manifiesto["version"], "1.0")
            self.assertEqual(manifiesto["producto"], "Mamatlatolli")
            self.assertEqual(manifiesto["idioma"], "lsm")
            self.assertEqual(manifiesto["nombre_idioma"], "Lengua de Señas Mexicana")
            self.assertEqual(manifiesto["idioma_glosa"], "es-MX")
            self.assertEqual(manifiesto["conteo"], 4)
            self.assertEqual(len(manifiesto["archivos"]), 4)

            importar_paquete(resultado.ruta, destino)
            copiadas = cargar_plantillas(destino)
            self.assertEqual(_firma(originales), _firma(copiadas))
            hola = next(m for m in copiadas if m.etiqueta == "HOLA")
            self.assertEqual(hola.pose["landmarks"][0][0], 0.2)
            self.assertEqual(hola.rostro["landmarks"][0][1], 0.5)
            self.assertIsNone(next(m for m in copiadas if m.etiqueta == "A").pose)

    def test_json_empaquetado_tambien_viaja(self) -> None:
        with self._dirs() as (origen, destino, _archivo):
            guardar_plantilla(_estatica("B", categoria="letra"), origen)
            json_ruta = destino.parent / "senas.json"
            exportar_biblioteca(origen, json_ruta, creado="2026-09-23T00:00:00+00:00")
            paquete = leer_paquete(json_ruta)
            self.assertEqual(paquete.manifiesto.idioma, "lsm")
            self.assertEqual([m.etiqueta for m in paquete.muestras], ["B"])
            importar_paquete(json_ruta, destino)
            self.assertEqual([m.etiqueta for m in cargar_plantillas(destino)], ["B"])

    def test_campo_extra_del_manifiesto_no_estorba(self) -> None:
        with self._dirs() as (origen, destino, archivo):
            guardar_plantilla(_estatica("C"), origen)
            exportar_biblioteca(origen, archivo, creado="2026-09-23T00:00:00+00:00")
            with zipfile.ZipFile(archivo) as zf:
                manifiesto = json.loads(zf.read("manifiesto.json"))
                piezas = {nombre: zf.read(nombre) for nombre in zf.namelist()}
            manifiesto["banco_futuro"] = {"sync": False, "lenguas": ["lsm"]}
            crudo = io.BytesIO()
            with zipfile.ZipFile(crudo, "w") as zf:
                zf.writestr("manifiesto.json", json.dumps(manifiesto))
                for nombre, contenido in piezas.items():
                    if nombre != "manifiesto.json":
                        zf.writestr(nombre, contenido)
            retocado = archivo.with_name("extra.mamatlatolli")
            retocado.write_bytes(crudo.getvalue())
            paquete = leer_paquete(retocado)
            self.assertEqual(paquete.manifiesto.version, "1.0")
            importar_paquete(retocado, destino)
            self.assertEqual([m.etiqueta for m in cargar_plantillas(destino)], ["C"])

    def test_el_reconocedor_ve_lo_importado(self) -> None:
        with self._dirs() as (origen, destino, archivo):
            _poblar(origen)
            exportar_biblioteca(origen, archivo, creado="2026-09-23T00:00:00+00:00")
            importar_paquete(archivo, destino)
            letras = crear_reconocedor(destino, categoria="letra")
            palabras = crear_reconocedor(destino, categoria="palabra")
            self.assertEqual(letras.n_estaticas, 2)
            self.assertEqual(letras.n_dinamicas, 1)
            self.assertEqual({etiqueta for etiqueta, _vector in letras._vectores}, {"A"})
            self.assertEqual(palabras.n_estaticas, 1)
            self.assertEqual({etiqueta for etiqueta, _vector in palabras._vectores}, {"HOLA"})

    def test_exportar_vacio_no_crea_archivo(self) -> None:
        with self._dirs() as (origen, _destino, archivo):
            with self.assertRaises(ErrorPaquete) as ctx:
                exportar_biblioteca(origen, archivo)
            self.assertEqual(str(ctx.exception), textos.MENSAJE_EXPORTAR_VACIO)
            self.assertFalse(archivo.exists())

    def _dirs(self):
        import tempfile

        return _TresDirs(tempfile.TemporaryDirectory())


class _TresDirs:
    def __init__(self, temporal) -> None:
        self._temporal = temporal

    def __enter__(self):
        raiz = Path(self._temporal.__enter__())
        origen = raiz / "origen"
        destino = raiz / "destino"
        origen.mkdir()
        destino.mkdir()
        return origen, destino, raiz / "senas.mamatlatolli"

    def __exit__(self, *args):
        return self._temporal.__exit__(*args)


class TestFusion(unittest.TestCase):
    def test_reemplazar_sustituye_el_grupo_y_conserva_el_resto(self) -> None:
        with self._caso() as (origen, destino, archivo):
            guardar_plantilla(_estatica("A", notas="en-laptop"), origen)
            guardar_plantilla(_estatica("B", notas="solo-laptop"), origen)
            exportar_biblioteca(origen, archivo, creado="2026-09-23T00:00:00+00:00")

            guardar_plantilla(_estatica("A", notas="en-pc"), destino)
            guardar_plantilla(_estatica("Z", notas="solo-pc"), destino)
            guardar_plantilla(_dinamica("A", notas="a-con-movimiento"), destino)

            paquete = leer_paquete(archivo)
            resumen = resumir_conflicto(destino, paquete)
            self.assertEqual(resumen.en_comun, 1)
            self.assertEqual(resumen.nuevas, 1)

            resultado = aplicar_importacion(destino, paquete, POLITICA_REEMPLAZAR)
            self.assertEqual(resultado.reemplazadas, 1)
            self.assertEqual(resultado.agregadas, 1)
            self.assertEqual(resultado.eliminadas, 1)
            por_nota = {m.metadatos.notas: (m.etiqueta, m.tipo) for m in cargar_plantillas(destino)}
            self.assertEqual(por_nota["en-laptop"], ("A", "estatico"))
            self.assertNotIn("en-pc", por_nota)
            self.assertEqual(por_nota["solo-pc"], ("Z", "estatico"))
            self.assertEqual(por_nota["a-con-movimiento"], ("A", "dinamico"))
            self.assertEqual(por_nota["solo-laptop"], ("B", "estatico"))

    def test_solo_nuevas_no_toca_las_que_ya_estan(self) -> None:
        with self._caso() as (origen, destino, archivo):
            guardar_plantilla(_estatica("A", notas="nueva-toma-1"), origen)
            guardar_plantilla(_estatica("A", notas="nueva-toma-2"), origen)
            guardar_plantilla(_estatica("C", notas="recien-llegada"), origen)
            exportar_biblioteca(origen, archivo, creado="2026-09-23T00:00:00+00:00")
            guardar_plantilla(_estatica("A", notas="la-mia"), destino)

            resultado = importar_paquete(archivo, destino, politica=POLITICA_SOLO_NUEVAS)
            self.assertEqual(resultado.agregadas, 1)
            self.assertEqual(resultado.reemplazadas, 0)
            self.assertEqual(resultado.omitidas, 2)
            notas = {m.metadatos.notas for m in cargar_plantillas(destino)}
            self.assertEqual(notas, {"la-mia", "recien-llegada"})

    def test_misma_glosa_en_minusculas_cuenta_como_la_misma(self) -> None:
        with self._caso() as (origen, destino, archivo):
            guardar_plantilla(_estatica("HOLA", notas="pc", categoria="palabra"), destino)
            muestra = _estatica("HOLA", notas="laptop", categoria="palabra")
            bruto = muestra.a_dict()
            bruto["etiqueta"] = "hola"
            self._escribir_json(archivo.with_suffix(".json"), [bruto])
            resultado = importar_paquete(
                archivo.with_suffix(".json"),
                destino,
                politica=POLITICA_REEMPLAZAR,
            )
            self.assertEqual(resultado.reemplazadas, 1)
            quedaron = cargar_plantillas(destino)
            self.assertEqual(len(quedaron), 1)
            self.assertEqual(quedaron[0].etiqueta, "HOLA")
            self.assertEqual(quedaron[0].metadatos.notas, "laptop")

    def test_politica_desconocida_no_escribe(self) -> None:
        with self._caso() as (origen, destino, archivo):
            guardar_plantilla(_estatica("A"), origen)
            exportar_biblioteca(origen, archivo, creado="2026-09-23T00:00:00+00:00")
            guardar_plantilla(_estatica("Z", notas="queda"), destino)
            with self.assertRaises(ErrorPaquete):
                aplicar_importacion(destino, leer_paquete(archivo), "sufijo")
            self.assertEqual({m.etiqueta for m in cargar_plantillas(destino)}, {"Z"})

    def _caso(self):
        import tempfile

        return _TresDirs(tempfile.TemporaryDirectory())

    def _escribir_json(self, ruta: Path, plantillas: list[dict]) -> None:
        datos = _manifiesto_minimo(conteo=len(plantillas), plantillas=plantillas)
        ruta.write_text(json.dumps(datos), encoding="utf-8")


class TestValidacion(unittest.TestCase):
    def test_archivo_basura_version_y_sena_ilegible_no_tocan_la_biblioteca(self) -> None:
        with self._caso() as (_origen, destino, archivo):
            guardar_plantilla(_estatica("A", notas="intacta"), destino)
            antes = _firma(cargar_plantillas(destino))

            archivo.write_bytes(b"esto no es un paquete")
            with self.assertRaises(ErrorPaquete) as basura:
                importar_paquete(archivo, destino)
            self.assertEqual(str(basura.exception), textos.MENSAJE_NO_ES_PAQUETE)

            archivo.write_bytes(b"PK\x03\x04esto-esta-cortado")
            with self.assertRaises(ErrorPaquete) as cortado:
                importar_paquete(archivo, destino)
            self.assertEqual(str(cortado.exception), textos.MENSAJE_ARCHIVO_DANADO)

            self._zip(archivo, {"manifiesto.json": json.dumps(_manifiesto_minimo(version="2.0")).encode()})
            with self.assertRaises(ErrorPaquete) as version:
                importar_paquete(archivo, destino)
            self.assertEqual(str(version.exception), textos.MENSAJE_VERSION_INCOMPATIBLE)

            muestra = _estatica("B").a_dict()
            del muestra["mano"]
            self._zip(
                archivo,
                {
                    "manifiesto.json": json.dumps(
                        _manifiesto_minimo(archivos=["plantillas/0001_B_letra_estatico.json"])
                    ).encode(),
                    "plantillas/0001_B_letra_estatico.json": json.dumps(muestra).encode(),
                },
            )
            with self.assertRaises(ErrorPaquete) as ilegible:
                importar_paquete(archivo, destino)
            self.assertEqual(str(ilegible.exception), textos.MENSAJE_SENA_ILEGIBLE)

            self._zip(
                archivo,
                {
                    "manifiesto.json": json.dumps(_manifiesto_minimo(conteo=4)).encode(),
                    "plantillas/0001_A_letra_estatico.json": json.dumps(_estatica("A").a_dict()).encode(),
                },
            )
            with self.assertRaises(ErrorPaquete) as incompleto:
                leer_paquete(archivo)
            self.assertEqual(str(incompleto.exception), textos.MENSAJE_PAQUETE_INCOMPLETO)

            self._zip(
                archivo,
                {
                    "manifiesto.json": json.dumps(_manifiesto_minimo()).encode(),
                    "plantillas/../../fuera.json": b"{}",
                },
            )
            with self.assertRaises(ErrorPaquete) as travesura:
                leer_paquete(archivo)
            self.assertEqual(str(travesura.exception), textos.MENSAJE_PAQUETE_INCOMPLETO)
            self.assertFalse((destino.parent / "fuera.json").exists())

            self.assertEqual(_firma(cargar_plantillas(destino)), antes)
            self.assertEqual(inventario_plantillas(destino)[0][0].muestra.metadatos.notas, "intacta")

    def test_mensajes_en_espanol_sin_jerga(self) -> None:
        frases = [
            textos.MENSAJE_EXPORTAR_VACIO,
            textos.MENSAJE_ARCHIVO_DANADO,
            textos.MENSAJE_NO_ES_PAQUETE,
            textos.MENSAJE_PAQUETE_INCOMPLETO,
            textos.MENSAJE_VERSION_INCOMPATIBLE,
            textos.MENSAJE_SENA_ILEGIBLE,
            textos.MENSAJE_PAQUETE_SIN_SENAS,
            textos.texto_conflicto_importar(2, 1),
            textos.mensaje_exportacion_lista(3),
            textos.mensaje_importacion_lista(agregadas=1, reemplazadas=2, omitidas=0),
        ]
        prohibido = ("json", "zip", "esquema", "schema", "dtw", "traceback", "parse", "null")
        for frase in frases:
            bajo = frase.lower()
            self.assertIn("seña", bajo)
            for palabra in prohibido:
                self.assertNotIn(palabra, bajo)

    def _caso(self):
        import tempfile

        return _TresDirs(tempfile.TemporaryDirectory())

    def _zip(self, ruta: Path, miembros: dict[str, bytes]) -> None:
        crudo = io.BytesIO()
        with zipfile.ZipFile(crudo, "w") as archivo:
            for nombre, contenido in miembros.items():
                archivo.writestr(nombre, contenido)
        ruta.write_bytes(crudo.getvalue())


class TestLineaDeComandos(unittest.TestCase):
    def test_exportar_e_importar_por_ruta(self) -> None:
        with self._caso() as (origen, destino, archivo):
            guardar_plantilla(_estatica("Ñ", notas="enie"), origen)
            guardar_plantilla(_estatica("Ñ", notas="vieja"), destino)
            salida = io.StringIO()
            error = io.StringIO()
            with mock.patch("sys.stdout", salida), mock.patch("sys.stderr", error):
                codigo = main_exportar([str(archivo), "--desde", str(origen)])
            self.assertEqual(codigo, 0)
            self.assertIn("1 seña", salida.getvalue())
            self.assertTrue(archivo.is_file())

            salida = io.StringIO()
            with mock.patch("sys.stdout", salida), mock.patch("sys.stderr", error):
                codigo = main_importar([str(archivo), "--hacia", str(destino)])
            self.assertEqual(codigo, 0)
            self.assertIn("Reemplacé", salida.getvalue())
            quedaron = cargar_plantillas(destino)
            self.assertEqual([m.metadatos.notas for m in quedaron], ["enie"])

            salida = io.StringIO()
            with mock.patch("sys.stdout", salida):
                codigo = main_importar([str(archivo), "--hacia", str(destino), "--solo-nuevas"])
            self.assertEqual(codigo, 0)
            self.assertIn("No agregué", salida.getvalue())
            self.assertEqual([m.metadatos.notas for m in cargar_plantillas(destino)], ["enie"])

    def test_archivo_invalido_sale_con_error(self) -> None:
        with self._caso() as (_origen, destino, archivo):
            archivo.write_text("{}", encoding="utf-8")
            error = io.StringIO()
            with mock.patch("sys.stderr", error):
                codigo = main_importar([str(archivo), "--hacia", str(destino)])
            self.assertEqual(codigo, 1)
            self.assertEqual(error.getvalue().strip(), textos.MENSAJE_NO_ES_PAQUETE)
            self.assertEqual(cargar_plantillas(destino), [])

    def _caso(self):
        import tempfile

        return _TresDirs(tempfile.TemporaryDirectory())


def _tk_disponible() -> bool:
    if not os.environ.get("DISPLAY"):
        return False
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(_tk_disponible(), "requiere display gráfico y tkinter")
class TestBibliotecaTrasladoUi(unittest.TestCase):
    def test_botones_y_flujo_de_dialogos_mockeados(self) -> None:
        import customtkinter as ctk

        from innova.pantallas import DialogoPoliticaImportacion, PantallaBiblioteca
        from innova.tema import aplicar_tema

        aplicar_tema("claro")
        with self._caso() as (origen, destino, archivo):
            _poblar(origen)
            raiz = ctk.CTk()
            raiz.geometry("1040x860")
            try:
                pantalla = PantallaBiblioteca(raiz, on_volver=lambda: None, on_probar=lambda *a: None, ruta_plantillas=origen)
                pantalla.pack(fill="both", expand=True)
                raiz.update()
                self.assertEqual(pantalla.btn_exportar.cget("text"), "Exportar…")
                self.assertEqual(pantalla.btn_importar.cget("text"), "Importar…")
                self.assertIn("otra computadora", textos.AYUDA_TRASLADO)

                with mock.patch("innova.pantallas.messagebox.showinfo") as info:
                    pantalla._exportar_hacia(archivo)
                self.assertTrue(archivo.is_file())
                self.assertIn("Listo", pantalla.lbl_traslado.cget("text"))
                self.assertTrue(info.called)

                vacia = PantallaBiblioteca(
                    raiz,
                    on_volver=lambda: None,
                    on_probar=lambda *a: None,
                    ruta_plantillas=destino,
                )
                with mock.patch("innova.pantallas.messagebox.showinfo"):
                    vacia._importar_desde(archivo)
                etiquetas = {item.muestra.etiqueta for item in inventario_plantillas(destino)[0]}
                self.assertEqual(etiquetas, {"A", "J", "HOLA"})
                self.assertIn("Listo", vacia.lbl_traslado.cget("text"))

                (destino / "no-es-paquete.mamatlatolli").write_bytes(b"basura")
                with mock.patch("innova.pantallas.messagebox.showerror") as error:
                    vacia._importar_desde(destino / "no-es-paquete.mamatlatolli")
                self.assertEqual(error.call_args[0][1], textos.MENSAJE_NO_ES_PAQUETE)
                self.assertIn("no es un paquete", vacia.lbl_traslado.cget("text").lower())

                with mock.patch("innova.pantallas.filedialog.asksaveasfilename", return_value=str(archivo)), mock.patch(
                    "innova.pantallas.messagebox.showinfo"
                ):
                    pantalla._exportar()
                with mock.patch(
                    "innova.pantallas.filedialog.askopenfilename",
                    return_value=str(archivo),
                ), mock.patch(
                    "innova.pantallas.preguntar_politica_importacion",
                    return_value=POLITICA_SOLO_NUEVAS,
                ) as pregunta, mock.patch("innova.pantallas.messagebox.showinfo"):
                    vacia._importar()
                pregunta.assert_called_once()
                self.assertIn("No agregué", vacia.lbl_traslado.cget("text"))

                dialogo = DialogoPoliticaImportacion(raiz, en_comun=2, nuevas=1)
                dialogo.update()
                self.assertEqual(dialogo.btn_reemplazar.cget("text"), textos.ETIQUETA_REEMPLAZAR)
                self.assertEqual(dialogo.btn_solo_nuevas.cget("text"), textos.ETIQUETA_SOLO_NUEVAS)
                self.assertEqual(dialogo.btn_cancelar.cget("text"), textos.ETIQUETA_CANCELAR_IMPORTAR)
                self.assertIn("Ya tienes algunas", textos.TITULO_CONFLICTO_IMPORTAR)
                dialogo._cancelar()
            finally:
                raiz.destroy()

    def _caso(self):
        import tempfile

        return _TresDirs(tempfile.TemporaryDirectory())


if __name__ == "__main__":
    unittest.main()
