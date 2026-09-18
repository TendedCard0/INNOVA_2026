"""Ventana de escritorio (CustomTkinter) de Mamatlatolli."""

from __future__ import annotations

import customtkinter as ctk

from innova.ajustes import Ajustes, cargar_ajustes
from innova.config import TITULO_VENTANA
from innova.menu import (
    DESTINO_ACERCA,
    DESTINO_BIBLIOTECA,
    DESTINO_CAPTURA,
    DESTINO_CONFIGURACION,
    DESTINO_DEMO,
    DESTINO_MENU,
    DESTINO_RECONOCIMIENTO,
    Navegador,
)
from innova.pantallas import (
    PantallaAcercaDe,
    PantallaBiblioteca,
    PantallaCaptura,
    PantallaConfiguracion,
    PantallaMenu,
    PantallaReconocimiento,
)
from innova.tema import COLOR_FONDO, aplicar_tema


class VentanaMamatlatolli(ctk.CTk):
    def __init__(self, *, modo_demo: bool = False, indice_camara: int = 0) -> None:
        super().__init__()
        self._modo_demo_cli = modo_demo
        self._indice_camara = indice_camara
        self._ajustes: Ajustes = cargar_ajustes()
        self._navegador = Navegador()
        self._pantalla = None
        self._aviso_reconocimiento = ""

        self.title(TITULO_VENTANA)
        self.geometry("1040x820")
        self.minsize(920, 700)
        self.configure(fg_color=COLOR_FONDO)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.bind_all("<Escape>", lambda _e: self._cerrar())
        self.bind_all("q", self._salir_si_no_escribe)
        self.bind_all("Q", self._salir_si_no_escribe)
        self.bind_all("<KeyPress-space>", self._espacio_pulsado)
        self.bind_all("<KeyRelease-space>", self._espacio_soltado)

        self._contenedor = ctk.CTkFrame(self, fg_color=COLOR_FONDO)
        self._contenedor.pack(fill="both", expand=True)
        self.mostrar_menu()

    def mostrar_menu(self) -> None:
        self._navegador.volver()
        self.geometry("1040x820")
        self._cambiar(
            PantallaMenu(
                self._contenedor,
                on_ir=self.ir_a,
                demo_cli=self._modo_demo_cli,
            )
        )

    def ir_a(self, destino: str) -> None:
        self._navegador.ir(destino)
        if destino == DESTINO_MENU:
            self.mostrar_menu()
            return
        if destino == DESTINO_RECONOCIMIENTO:
            self._abrir_reconocimiento(demo=self._modo_demo_cli)
            return
        if destino == DESTINO_DEMO:
            self._abrir_reconocimiento(demo=True)
            return
        if destino == DESTINO_CAPTURA:
            self.geometry("1120x760")
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
            self.geometry("1040x760")
            self._cambiar(
                PantallaBiblioteca(
                    self._contenedor,
                    on_volver=self.mostrar_menu,
                    on_probar=self._probar_plantilla,
                )
            )
            return
        if destino == DESTINO_CONFIGURACION:
            self.geometry("1040x780")
            self._cambiar(
                PantallaConfiguracion(
                    self._contenedor,
                    ajustes=self._ajustes,
                    on_volver=self.mostrar_menu,
                    on_guardar=self._guardar_ajustes,
                )
            )
            return
        if destino == DESTINO_ACERCA:
            self.geometry("1040x720")
            self._cambiar(PantallaAcercaDe(self._contenedor, on_volver=self.mostrar_menu))
            return
        self.mostrar_menu()

    def _abrir_reconocimiento(self, *, demo: bool) -> None:
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
            )
        )

    def _probar_plantilla(self, etiqueta: str, tipo: str) -> None:
        clase = "dinámica" if tipo == "dinamico" else "estática"
        self._aviso_reconocimiento = (
            f"Prueba la seña «{etiqueta}» ({clase}). "
            "Si es dinámica, muévete o usa «Seña con movimiento»."
        )
        self.ir_a(DESTINO_RECONOCIMIENTO)

    def _guardar_ajustes(self, ajustes: Ajustes) -> None:
        self._ajustes = ajustes

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
    aplicar_tema()
    ventana = VentanaMamatlatolli(modo_demo=modo_demo, indice_camara=indice_camara)
    ventana.mainloop()
