"""Archivos de build del instalador de Mamatlatolli. No generan un .exe."""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path


_RAIZ = Path(__file__).resolve().parent.parent


def _cargar_construir():
    ruta = _RAIZ / "empaquetado" / "construir.py"
    spec = importlib.util.spec_from_file_location("construir_mamatlatolli", ruta)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No pude cargar {ruta}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class TestEmpaquetado(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.construir = _cargar_construir()

    def test_comprobar_los_archivos_de_mamatlatolli(self) -> None:
        self.assertEqual(self.construir.comprobar(_RAIZ), [])

    def test_version_del_producto(self) -> None:
        self.assertEqual(self.construir.version_del_producto(_RAIZ), "0.5.0")
        self.assertEqual(self.construir.version_info_windows("0.5.0"), "0.5.0.0")

    def test_comando_de_inno_setup(self) -> None:
        comando = self.construir.comando_iscc(
            Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
            _RAIZ / "empaquetado" / "mamatlatolli.iss",
            "0.5.0",
            maquina=False,
        )
        self.assertIn("/DMyAppVersion=0.5.0", comando)
        self.assertIn("/DMyVersionInfo=0.5.0.0", comando)
        self.assertNotIn("/DInstalacionDeMaquina", comando)
        de_maquina = self.construir.comando_iscc(
            Path("ISCC.exe"),
            _RAIZ / "empaquetado" / "mamatlatolli.iss",
            "0.5.0",
            maquina=True,
        )
        self.assertIn("/DInstalacionDeMaquina", de_maquina)

    def test_pyinstaller_usa_el_spec(self) -> None:
        comando = self.construir.comando_pyinstaller("python", _RAIZ)
        self.assertEqual(comando[2], "PyInstaller")
        self.assertTrue(comando[-1].endswith("mamatlatolli.spec"))

    def test_el_portable_es_un_zip_con_el_exe_por_dentro(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            origen = base / "Mamatlatolli"
            origen.mkdir()
            (origen / "Mamatlatolli.exe").write_bytes(b"no-es-un-exe-real")
            (origen / "icono.ico").write_bytes(b"ico")
            destino = base / "Mamatlatolli-portable.zip"
            self.construir.empaquetar_portable(origen, destino)
            with zipfile.ZipFile(destino) as archivo:
                nombres = set(archivo.namelist())
            self.assertIn("Mamatlatolli/Mamatlatolli.exe", nombres)
            self.assertIn("Mamatlatolli/icono.ico", nombres)

    def test_en_este_sistema_no_finge_un_exe(self) -> None:
        if sys.platform == "win32":
            self.skipTest("en Windows el comando sí construye")
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = self.construir.main([])
        self.assertEqual(codigo, 2)
        texto = salida.getvalue()
        self.assertIn("Mamatlatolli", texto)
        self.assertIn("windows-latest", texto)
        self.assertIn("Mamatlatolli-Setup.exe", texto)
        self.assertFalse((_RAIZ / "dist" / "Mamatlatolli-Setup.exe").exists())

    def test_comprobar_por_la_cli(self) -> None:
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = self.construir.main(["--comprobar"])
        self.assertEqual(codigo, 0)
        self.assertIn("Mamatlatolli", salida.getvalue())

    def test_inno_setup_lee_acentos(self) -> None:
        for nombre in ("mamatlatolli.iss", "aviso-instalacion.txt"):
            datos = (_RAIZ / "empaquetado" / nombre).read_bytes()
            self.assertTrue(datos.startswith(b"\xef\xbb\xbf"), nombre)
        texto = (_RAIZ / "empaquetado" / "aviso-instalacion.txt").read_text(encoding="utf-8-sig")
        self.assertIn("SmartScreen", texto)
        self.assertIn("Mamatlatolli", texto)
        self.assertIn("%LOCALAPPDATA%\\Mamatlatolli", texto)

    def test_el_workflow_publica_el_setup(self) -> None:
        texto = (_RAIZ / ".github" / "workflows" / "instalador-windows.yml").read_text(encoding="utf-8")
        self.assertIn("windows-latest", texto)
        self.assertIn("Instalador Windows de Mamatlatolli", texto)
        self.assertIn("Mamatlatolli-Setup.exe", texto)
        self.assertIn("Mamatlatolli-portable.zip", texto)
        self.assertIn("upload-artifact", texto)
        self.assertIn("innosetup-6.7.3.exe", texto)
        self.assertIn("python empaquetado/construir.py", texto)
