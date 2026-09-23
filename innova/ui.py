"""Ventana de escritorio (CustomTkinter) de Mamatlatolli."""

from __future__ import annotations

import sys
import tkinter
from dataclasses import replace

import customtkinter as ctk

from innova import tema
from innova.ajustes import Ajustes, cargar_ajustes, guardar_tema
from innova.esquema import CATEGORIA_LETRA, CATEGORIA_PALABRA
from innova.menu import (
    DESTINO_ABECEDARIO,
    DESTINO_ACERCA,
    DESTINO_BIBLIOTECA,
    DESTINO_CAPTURA,
    DESTINO_CONFIGURACION,
    DESTINO_DEMO,
    DESTINO_MENU,
    DESTINO_PRACTICA,
    DESTINO_VOCABULARIO,
    Navegador,
    categoria_de_destino,
)
from innova.pantallas import (
    PantallaAcercaDe,
    PantallaBiblioteca,
    PantallaCaptura,
    PantallaConfiguracion,
    PantallaMenu,
    PantallaPractica,
    PantallaReconocimiento,
)
from innova.tema import aplicar_tema
from innova import textos
from innova.textos import SUBTITULO_DEMO, titulo_pantalla, titulo_ventana


# Sin este id, Windows agrupa la ventana con python.exe y la barra de
# tareas sigue mostrando el icono de Python aunque la ventana tenga otro.
ID_APLICACION_WINDOWS = "Mamatlatolli.ReconocimientoLSM"


def preparar_identidad_windows() -> None:
    """Separa el proceso del icono de Python en la barra de tareas de Windows."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_APLICACION_WINDOWS)
    except (AttributeError, OSError):
        return


def aplicar_icono_ventana(ventana: ctk.CTk) -> None:
    """Pone la marca de Mamatlatolli en la barra de título y en la de tareas.

    En Windows, ``iconbitmap`` con el ``.ico`` multi-tamaño es lo que usa la
    barra de tareas. En los demás sistemas, ``iconphoto`` usa el PNG.
    """
    ventana._iconos_mamatlatolli = []
    ventana._icono_aplicado = False
    if sys.platform == "win32":
        ruta_ico = tema.resolver_icono_ico()
        if ruta_ico is not None:
            try:
                ventana.iconbitmap(default=ruta_ico.as_posix())
                ventana._icono_aplicado = True
                return
            except tkinter.TclError:
                pass
    imagen = tema.imagen_icono_app()
    if imagen is None:
        return
    try:
        from PIL import Image, ImageTk
    except ImportError:
        return
    fotos = []
    for lado in (16, 32, 48, 64, 128, 256):
        if min(imagen.size) < lado:
            continue
        copia = imagen if imagen.size == (lado, lado) else imagen.resize((lado, lado), Image.Resampling.LANCZOS)
        fotos.append(ImageTk.PhotoImage(copia, master=ventana))
    if not fotos:
        fotos.append(ImageTk.PhotoImage(imagen, master=ventana))
    try:
        ventana.iconphoto(True, *fotos)
    except tkinter.TclError:
        return
    ventana._iconos_mamatlatolli = fotos
    ventana._icono_aplicado = True


class VentanaMamatlatolli(ctk.CTk):
    def __init__(self, *, modo_demo: bool = False, indice_camara: int = 0) -> None:
        preparar_identidad_windows()
        ajustes = cargar_ajustes()
        aplicar_tema(ajustes.tema)
        super().__init__()
        aplicar_icono_ventana(self)
        self._modo_demo_cli = modo_demo
        self._indice_camara = indice_camara
        self._ajustes: Ajustes = ajustes
        self._navegador = Navegador()
        self._pantalla = None
        self._aviso_reconocimiento = ""
        self._vista_config: Ajustes | None = None

        self.geometry("1040x900")
        self.minsize(920, 720)
        self.configure(fg_color=tema.COLOR_FONDO)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.bind_all("<Escape>", self._al_escape)
        self.bind_all("q", self._salir_si_no_escribe)
        self.bind_all("Q", self._salir_si_no_escribe)
        self.bind_all("<KeyPress-space>", self._espacio_pulsado)
        self.bind_all("<KeyRelease-space>", self._espacio_soltado)

        self._contenedor = ctk.CTkFrame(self, fg_color=tema.COLOR_FONDO)
        self._contenedor.pack(fill="both", expand=True)
        self.mostrar_menu()

    def mostrar_menu(self) -> None:
        self._navegador.volver()
        self.title(titulo_ventana(DESTINO_MENU))
        self.geometry("1040x900")
        self._cambiar(
            PantallaMenu(
                self._contenedor,
                on_ir=self.ir_a,
                demo_cli=self._modo_demo_cli,
                on_cambiar_tema=self._programar_tema,
            )
        )

    def ir_a(self, destino: str) -> None:
        self._navegador.ir(destino)
        self.title(titulo_ventana(destino))
        if destino == DESTINO_MENU:
            self.mostrar_menu()
            return
        if destino == DESTINO_PRACTICA:
            self.geometry("1120x820")
            self._cambiar(
                PantallaPractica(
                    self._contenedor,
                    modo_demo=self._modo_demo_cli,
                    indice_camara=self._indice_camara,
                    ajustes=self._ajustes,
                    on_volver=self.mostrar_menu,
                    on_record=self._fijar_record,
                )
            )
            return
        if destino in {DESTINO_ABECEDARIO, DESTINO_VOCABULARIO}:
            self._abrir_reconocimiento(
                demo=self._modo_demo_cli,
                categoria=categoria_de_destino(destino),
            )
            return
        if destino == DESTINO_DEMO:
            self._abrir_reconocimiento(
                demo=True,
                categoria=CATEGORIA_LETRA,
                nombre=titulo_pantalla(DESTINO_DEMO),
                subtitulo=SUBTITULO_DEMO,
            )
            return
        if destino == DESTINO_CAPTURA:
            self.geometry("1120x780")
            self._cambiar(
                PantallaCaptura(
                    self._contenedor,
                    modo_demo=self._modo_demo_cli,
                    indice_camara=self._indice_camara,
                    ajustes=self._ajustes,
                    on_volver=self.mostrar_menu,
                )
            )
            return
        if destino == DESTINO_BIBLIOTECA:
            self.geometry("1040x860")
            self._cambiar(
                PantallaBiblioteca(
                    self._contenedor,
                    on_volver=self.mostrar_menu,
                    on_probar=self._probar_plantilla,
                )
            )
            return
        if destino == DESTINO_CONFIGURACION:
            self.geometry("1040x880")
            self._cambiar(
                PantallaConfiguracion(
                    self._contenedor,
                    ajustes=self._ajustes_para_config(),
                    on_volver=self.mostrar_menu,
                    on_guardar=self._guardar_ajustes,
                    on_cambiar_tema=self._programar_tema,
                )
            )
            return
        if destino == DESTINO_ACERCA:
            self.geometry("1040x720")
            self._cambiar(PantallaAcercaDe(self._contenedor, on_volver=self.mostrar_menu))
            return
        self.mostrar_menu()

    def _abrir_reconocimiento(
        self,
        *,
        demo: bool,
        categoria: str,
        nombre: str | None = None,
        subtitulo: str | None = None,
    ) -> None:
        self.geometry("1120x760")
        aviso = self._aviso_reconocimiento
        self._aviso_reconocimiento = ""
        self._cambiar(
            PantallaReconocimiento(
                self._contenedor,
                modo_demo=demo,
                indice_camara=self._indice_camara,
                ajustes=self._ajustes,
                on_volver=self.mostrar_menu,
                aviso_inicial=aviso,
                categoria=categoria,
                nombre_pantalla=nombre,
                subtitulo_pantalla=subtitulo,
            )
        )

    def _probar_plantilla(self, etiqueta: str, tipo: str, categoria: str = CATEGORIA_LETRA) -> None:
        self._aviso_reconocimiento = textos.aviso_probar(etiqueta, tipo, categoria)
        destino = DESTINO_VOCABULARIO if categoria == CATEGORIA_PALABRA else DESTINO_ABECEDARIO
        self.ir_a(destino)

    def _fijar_record(self, record: int) -> None:
        self._ajustes = replace(self._ajustes, record_practica=int(record)).normalizado()

    def _guardar_ajustes(self, ajustes: Ajustes) -> None:
        self._ajustes = ajustes
        self._vista_config = None

    def _ajustes_para_config(self) -> Ajustes:
        if self._vista_config is not None:
            vista = self._vista_config
            self._vista_config = None
            return vista
        return self._ajustes

    def _programar_tema(self, modo: str, vista: Ajustes | None = None) -> None:
        """Aplica el tema fuera del callback del botón, para poder reconstruir la pantalla."""
        self.after_idle(lambda: self._aplicar_cambio_tema(modo, vista))

    def _aplicar_cambio_tema(self, modo: str, vista: Ajustes | None) -> None:
        elegido = tema.normalizar_tema(modo)
        if elegido == tema.MODO_ACTUAL and (
            vista is None or tema.normalizar_tema(vista.tema) == tema.MODO_ACTUAL
        ):
            return
        self._ajustes = replace(self._ajustes, tema=elegido).normalizado()
        guardar_tema(elegido)
        aplicar_tema(elegido)
        if vista is not None:
            self._vista_config = replace(vista, tema=elegido).normalizado()
        self._repintar()

    def _repintar(self) -> None:
        self.configure(fg_color=tema.COLOR_FONDO)
        self._contenedor.configure(fg_color=tema.COLOR_FONDO)
        destino = self._navegador.actual
        if destino == DESTINO_MENU:
            self.mostrar_menu()
            return
        self.ir_a(destino)

    def _cambiar(self, pantalla) -> None:
        if self._pantalla is not None:
            cerrar = getattr(self._pantalla, "cerrar_pantalla", None)
            if callable(cerrar):
                cerrar()
            else:
                self._pantalla.destroy()
        self._pantalla = pantalla
        pantalla.pack(fill="both", expand=True)

    def _espacio_pulsado(self, _evento=None) -> None:
        if self._escribiendo() or self._es_boton_enfocado():
            return
        iniciar = getattr(self._pantalla, "iniciar_hold", None)
        if callable(iniciar):
            iniciar()

    def _espacio_soltado(self, _evento=None) -> None:
        if self._escribiendo() or self._es_boton_enfocado():
            return
        soltar = getattr(self._pantalla, "soltar_hold", None)
        if callable(soltar):
            soltar()

    def _escribiendo(self) -> bool:
        widget = self.focus_get()
        if widget is None:
            return False
        clase = widget.winfo_class()
        if clase in {"Entry", "Text", "TEntry"}:
            return True
        nombre = type(widget).__name__
        return "Entry" in nombre or "Textbox" in nombre or "Text" in nombre

    def _es_boton_enfocado(self) -> bool:
        widget = self.focus_get()
        if widget is None:
            return False
        nombre = type(widget).__name__
        return "Button" in nombre

    def _al_escape(self, _evento=None) -> None:
        if self._navegador.accion_escape() == "volver":
            self.mostrar_menu()
            return
        self._cerrar()

    def _salir_si_no_escribe(self, _evento=None) -> None:
        if self._escribiendo():
            return
        self._cerrar()

    def _cerrar(self) -> None:
        if self._pantalla is not None:
            cerrar = getattr(self._pantalla, "cerrar_pantalla", None)
            if callable(cerrar):
                try:
                    cerrar()
                except Exception:  # noqa: BLE001
                    pass
            self._pantalla = None
        self.destroy()


# Alias por si algún script de la fase 1 importaba el nombre anterior.
VentanaInnova = VentanaMamatlatolli


def ejecutar_app(*, modo_demo: bool = False, indice_camara: int = 0) -> None:
    aplicar_tema(cargar_ajustes().tema)
    ventana = VentanaMamatlatolli(modo_demo=modo_demo, indice_camara=indice_camara)
    ventana.mainloop()
