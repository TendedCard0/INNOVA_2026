"""Pantallas CustomTkinter del menú de Mamatlatolli."""

from __future__ import annotations

import time
from dataclasses import replace
from tkinter import messagebox
from typing import Any, Callable, Optional

import customtkinter as ctk
import cv2
from PIL import Image, ImageDraw

from innova import tema
from innova.ajustes import Ajustes, cargar_record_practica, guardar_ajustes, guardar_record_practica
from innova.audio import AudioMiniJuego
from innova.camara import CamaraNoDisponibleError
from innova.config import (
    ALTO_VIDEO,
    ANCHO_VIDEO,
    FPS_OBJETIVO,
    MENSAJE_CAMARA_AUSENTE,
    NOMBRE_PRODUCTO,
    RUTA_PLANTILLAS,
    SUBTITULO,
)
from innova.esquema import CATEGORIA_LETRA, CATEGORIA_PALABRA, CATEGORIA_TODAS
from innova.menu import OPCIONES_MENU, TEXTO_ACERCA
from innova.overlay import frame_mensaje
from innova.pipeline import PipelineVision, crear_pipeline
from innova.plantillas import eliminar_plantilla, filtrar_inventario, inventario_plantillas
from innova.practica import (
    MENSAJE_SIN_LETRAS,
    PartidaPractica,
    VistaPractica,
    letras_estaticas_disponibles,
    sonidos_para,
    texto_fin,
)
from innova import textos
from innova.tema import (
    acento_de_indice,
    hex_a_rgb,
    icono_menu,
    imagen_logo,
    imagen_logo_encajada,
    nombres_iconos_menu,
    resolver_logo,
)

_INTERVALO_MS = max(15, int(1000 / FPS_OBJETIVO))


def _encabezado(
    parent: ctk.CTkBaseClass,
    titulo: str,
    subtitulo: str,
    on_volver: Callable[[], None] | None,
) -> ctk.CTkFrame:
    barra = ctk.CTkFrame(parent, fg_color="transparent")
    barra.pack(fill="x", padx=28, pady=(18, 10))
    if on_volver is not None:
        ctk.CTkButton(
            barra,
            text="← Menú",
            width=108,
            height=36,
            corner_radius=12,
            fg_color=tema.COLOR_ACENTO,
            hover_color=tema.COLOR_ACENTO_HOVER,
            text_color=tema.COLOR_TEXTO_INVERSO,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=on_volver,
        ).pack(side="left", padx=(0, 16))
    textos = ctk.CTkFrame(barra, fg_color="transparent")
    textos.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(
        textos,
        text=titulo,
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=tema.COLOR_TEXTO,
    ).pack(anchor="w")
    ctk.CTkLabel(
        textos,
        text=subtitulo,
        font=ctk.CTkFont(size=13),
        text_color=tema.COLOR_TEXTO_MUDO,
    ).pack(anchor="w")
    return barra


def _pie(parent: ctk.CTkBaseClass, texto: str) -> None:
    pie = ctk.CTkFrame(parent, fg_color="transparent")
    pie.pack(fill="x", padx=24, pady=(4, 14))
    ctk.CTkLabel(
        pie,
        text=texto,
        font=ctk.CTkFont(size=12),
        text_color=tema.COLOR_TEXTO_MUDO,
        wraplength=1000,
        justify="left",
    ).pack(anchor="w")


def _tarjeta_aviso(parent: ctk.CTkBaseClass, titulo: str, detalle: str, *, wrap: int = 300) -> ctk.CTkFrame:
    """Aviso amable (biblioteca vacía, sin señas, etc.), alineado con las tarjetas."""
    marco = ctk.CTkFrame(
        parent,
        fg_color=tema.COLOR_TARJETA,
        corner_radius=16,
        border_width=1,
        border_color=tema.COLOR_INDIGO,
    )
    ctk.CTkLabel(
        marco,
        text=titulo,
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=tema.COLOR_TEXTO,
        wraplength=wrap,
        justify="left",
        anchor="w",
    ).pack(anchor="w", padx=16, pady=(14, 4))
    ctk.CTkLabel(
        marco,
        text=detalle,
        font=ctk.CTkFont(size=13),
        text_color=tema.COLOR_TEXTO,
        wraplength=wrap,
        justify="left",
        anchor="w",
    ).pack(anchor="w", padx=16, pady=(0, 14))
    return marco


class SelectorPastillas(ctk.CTkFrame):
    """Par de opciones con el mismo aspecto que el cambio de tema del menú."""

    def __init__(
        self,
        master: Any,
        opciones: tuple[tuple[str, str], ...],
        valor: str,
        command: Callable[[str], None] | None = None,
        ancho: int | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=tema.COLOR_CAMPO,
            corner_radius=14,
            border_width=1,
            border_color=tema.COLOR_BORDE,
        )
        self._valor = valor if any(clave == valor for _etiq, clave in opciones) else opciones[0][1]
        self._command = command
        self._botones: dict[str, ctk.CTkButton] = {}
        for etiqueta, clave in opciones:
            extras: dict[str, Any] = {}
            if ancho is not None:
                extras["width"] = ancho
            boton = ctk.CTkButton(
                self,
                text=etiqueta,
                height=32,
                corner_radius=10,
                command=lambda c=clave: self._elegir(c),
                **extras,
            )
            boton.pack(side="left", padx=3, pady=3)
            self._botones[clave] = boton
        self._pintar()

    def get(self) -> str:
        return self._valor

    def set(self, valor: str) -> None:
        if valor not in self._botones or valor == self._valor:
            return
        self._valor = valor
        self._pintar()

    def _elegir(self, clave: str) -> None:
        if clave == self._valor:
            return
        self._valor = clave
        self._pintar()
        if self._command is not None:
            self._command(clave)

    def _pintar(self) -> None:
        for clave, boton in self._botones.items():
            activo = clave == self._valor
            boton.configure(
                fg_color=tema.COLOR_ACENTO if activo else tema.COLOR_CAMPO,
                hover_color=tema.COLOR_ACENTO_HOVER if activo else tema.COLOR_BORDE,
                text_color=tema.COLOR_TEXTO_INVERSO if activo else tema.COLOR_TEXTO,
                font=ctk.CTkFont(size=13, weight="bold" if activo else "normal"),
            )


def selector_apariencia(
    parent: ctk.CTkBaseClass,
    modo: str,
    on_cambiar: Callable[[str], None] | None,
) -> SelectorPastillas:
    """Modo claro / Modo oscuro. El botón activo usa el acento índigo."""
    return SelectorPastillas(
        parent,
        (
            (tema.ETIQUETA_TEMA_CLARO, tema.TEMA_CLARO),
            (tema.ETIQUETA_TEMA_OSCURO, tema.TEMA_OSCURO),
        ),
        tema.normalizar_tema(modo),
        on_cambiar,
        ancho=128,
    )


def _recorrer_widgets(widget: Any, fn: Callable[[Any], None]) -> None:
    fn(widget)
    for hijo in widget.winfo_children():
        _recorrer_widgets(hijo, fn)


class MarcaMamatlatolli(ctk.CTkFrame):
    """Logo oficial (`assets/logo.png`) o marco placeholder, centrado.

    El PNG ya trae la M, el nombre y «Comunicación sin barreras.»: no se
    repite un título ni el subtítulo de LSM debajo. Si el archivo no está,
    el marco tríadico sí muestra el nombre, el subtítulo y la tira de color.
    """

    _ANCHO_LOGO = 440
    _ALTO_LOGO = 210
    _LADO_PLACEHOLDER = 104

    def __init__(self, master: Any) -> None:
        super().__init__(master, fg_color="transparent")
        if resolver_logo() is not None:
            pil, self._es_logo_archivo = imagen_logo_encajada(self._ANCHO_LOGO, self._ALTO_LOGO)
        else:
            pil, self._es_logo_archivo = imagen_logo(self._LADO_PLACEHOLDER)
        self._logo_ctk = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
        # El PNG oficial trae el nombre en azul marino. En modo oscuro esa tinta
        # se pierde sobre el fondo; una placa clara lo deja legible sin repetir el texto.
        self._sobre_placa_clara = self._es_logo_archivo and tema.MODO_ACTUAL == tema.TEMA_OSCURO
        if self._sobre_placa_clara:
            placa = ctk.CTkFrame(
                self,
                fg_color=tema.PALETA_CLARA["COLOR_FONDO"],
                corner_radius=28,
            )
            placa.pack(pady=(4, 8))
            ctk.CTkLabel(placa, image=self._logo_ctk, text="").pack(padx=22, pady=12)
        else:
            ctk.CTkLabel(self, image=self._logo_ctk, text="").pack(pady=(4, 8))
        if self._es_logo_archivo:
            return
        ctk.CTkLabel(
            self,
            text=NOMBRE_PRODUCTO,
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=tema.COLOR_TEXTO,
        ).pack(pady=(12, 0))
        ctk.CTkLabel(
            self,
            text=SUBTITULO,
            font=ctk.CTkFont(size=14),
            text_color=tema.COLOR_TEXTO_MUDO,
        ).pack(pady=(2, 10))
        tira = ctk.CTkFrame(self, fg_color="transparent")
        tira.pack(pady=(0, 6))
        for color in tema.TRIDADA:
            segmento = ctk.CTkFrame(
                tira,
                fg_color=color,
                width=36,
                height=6,
                corner_radius=3,
            )
            segmento.pack_propagate(False)
            segmento.pack(side="left", padx=3)


class TarjetaMenu(ctk.CTkFrame):
    """Tarjeta clicable: icono + título + subtítulo, con hover/press."""

    def __init__(
        self,
        master: Any,
        *,
        destino: str,
        etiqueta: str,
        descripcion: str,
        indice: int,
        on_ir: Callable[[str], None],
    ) -> None:
        self._destino = destino
        self._on_ir = on_ir
        self._acento = acento_de_indice(indice)
        super().__init__(
            master,
            fg_color=tema.COLOR_TARJETA,
            corner_radius=22,
            border_width=1,
            border_color=tema.COLOR_BORDE,
            cursor="hand2",
        )
        glifo = nombres_iconos_menu()[indice]
        pil = icono_menu(glifo, self._acento, lado=58)
        self._icono_ctk = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)

        interior = ctk.CTkFrame(self, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(interior, image=self._icono_ctk, text="").pack(side="left", padx=(0, 14))

        textos = ctk.CTkFrame(interior, fg_color="transparent")
        textos.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(
            textos,
            text=etiqueta,
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=tema.COLOR_TEXTO,
            anchor="w",
            justify="left",
        ).pack(anchor="w")
        ctk.CTkLabel(
            textos,
            text=descripcion,
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
            wraplength=320,
            anchor="w",
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        ctk.CTkLabel(
            interior,
            text="›",
            font=ctk.CTkFont(size=28),
            text_color=self._acento,
            width=24,
        ).pack(side="right", padx=(8, 0))

        self._reposo()
        _recorrer_widgets(self, self._vincular)

    def _vincular(self, widget: Any) -> None:
        try:
            widget.configure(cursor="hand2")
        except Exception:  # noqa: BLE001 — canvas interno de CTk
            pass
        widget.bind("<Enter>", self._al_entrar)
        widget.bind("<Leave>", self._al_salir)
        widget.bind("<ButtonPress-1>", self._al_presionar)
        widget.bind("<ButtonRelease-1>", self._al_soltar)

    def _puntero_dentro(self) -> bool:
        try:
            x, y = self.winfo_pointerxy()
            return (
                self.winfo_rootx() <= x <= self.winfo_rootx() + self.winfo_width()
                and self.winfo_rooty() <= y <= self.winfo_rooty() + self.winfo_height()
            )
        except Exception:  # noqa: BLE001
            return False

    def _reposo(self) -> None:
        self.configure(fg_color=tema.COLOR_TARJETA, border_color=tema.COLOR_BORDE, border_width=1)

    def _al_entrar(self, _evento=None) -> None:
        self.configure(
            fg_color=tema.COLOR_TARJETA_HOVER,
            border_color=self._acento,
            border_width=2,
        )

    def _al_salir(self, _evento=None) -> None:
        if not self._puntero_dentro():
            self._reposo()

    def _al_presionar(self, _evento=None) -> None:
        self.configure(
            fg_color=tema.COLOR_TARJETA_PRESION,
            border_color=self._acento,
            border_width=2,
        )

    def _al_soltar(self, _evento=None) -> None:
        if self._puntero_dentro():
            self._on_ir(self._destino)
            return
        try:
            self._reposo()
        except Exception:  # noqa: BLE001 — la tarjeta puede haberse destruido
            pass


class PantallaMenu(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        *,
        on_ir: Callable[[str], None],
        demo_cli: bool = False,
        on_cambiar_tema: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=tema.COLOR_FONDO)
        self._tarjetas: list[TarjetaMenu] = []

        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x", padx=28, pady=(22, 8))
        MarcaMamatlatolli(cabecera).pack(anchor="center")

        if demo_cli:
            aviso = ctk.CTkFrame(
                self,
                fg_color=tema.COLOR_TARJETA,
                corner_radius=14,
                border_width=1,
                border_color=tema.COLOR_NARANJA,
            )
            aviso.pack(fill="x", padx=36, pady=(4, 8))
            ctk.CTkLabel(
                aviso,
                text=textos.AVISO_DEMO_CLI,
                text_color=tema.COLOR_TEXTO,
                font=ctk.CTkFont(size=13),
                wraplength=720,
                justify="center",
            ).pack(padx=16, pady=10)

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=28, pady=(4, 8))
        cuerpo.grid_columnconfigure(0, weight=1, uniform="menu")
        cuerpo.grid_columnconfigure(1, weight=1, uniform="menu")

        n = len(OPCIONES_MENU)
        for indice, (destino, etiqueta, descripcion) in enumerate(OPCIONES_MENU):
            fila, col = divmod(indice, 2)
            span = 1
            if indice == n - 1 and n % 2 == 1:
                col = 0
                span = 2
            cuerpo.grid_rowconfigure(fila, weight=1)
            tarjeta = TarjetaMenu(
                cuerpo,
                destino=destino,
                etiqueta=etiqueta,
                descripcion=descripcion,
                indice=indice,
                on_ir=on_ir,
            )
            tarjeta.grid(
                row=fila,
                column=col,
                columnspan=span,
                sticky="nsew",
                padx=10,
                pady=8,
            )
            self._tarjetas.append(tarjeta)

        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", padx=24, pady=(4, 14))
        ctk.CTkLabel(
            pie,
            text=textos.PIE_MENU,
            font=ctk.CTkFont(size=12),
            text_color=tema.COLOR_TEXTO_MUDO,
        ).pack(side="left")
        apariencia = ctk.CTkFrame(pie, fg_color="transparent")
        apariencia.pack(side="right")
        ctk.CTkLabel(
            apariencia,
            text="Apariencia",
            font=ctk.CTkFont(size=12),
            text_color=tema.COLOR_TEXTO_MUDO,
        ).pack(side="left", padx=(12, 8))
        selector_apariencia(apariencia, tema.MODO_ACTUAL, on_cambiar_tema).pack(side="left")


class _PantallaConCamara(ctk.CTkFrame):
    """Base: pipeline + video a la izquierda, panel a la derecha."""

    def __init__(
        self,
        master: Any,
        *,
        modo_demo: bool,
        indice_camara: int,
        ajustes: Ajustes,
        on_volver: Callable[[], None],
        titulo: str,
        subtitulo: str,
        reconocer: bool = True,
        categoria: str = CATEGORIA_TODAS,
        texto_pie: str = textos.PIE_RECONOCIMIENTO,
    ) -> None:
        super().__init__(master, fg_color=tema.COLOR_FONDO)
        self._modo_demo = modo_demo
        self._indice_camara = indice_camara
        self._ajustes = ajustes
        self._on_volver = on_volver
        self._reconocer = reconocer
        self._categoria = categoria
        self._pipeline: Optional[PipelineVision] = None
        self._vivo = True
        self._img_ref: Optional[ctk.CTkImage] = None
        self._aviso_hasta = 0.0
        self._tick_id: str | None = None
        self._hold_activo = False

        _encabezado(self, titulo, subtitulo, on_volver=self.cerrar_y_volver)

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=24, pady=8)

        panel_video = ctk.CTkFrame(
            cuerpo,
            fg_color=tema.COLOR_TARJETA,
            corner_radius=20,
            border_width=1,
            border_color=tema.COLOR_BORDE,
        )
        panel_video.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.lbl_video = ctk.CTkLabel(panel_video, text="")
        self.lbl_video.pack(padx=12, pady=12, expand=True)

        self.lateral = ctk.CTkFrame(
            cuerpo,
            fg_color=tema.COLOR_TARJETA,
            corner_radius=20,
            border_width=1,
            border_color=tema.COLOR_BORDE,
            width=350,
        )
        self.lateral.pack(side="right", fill="y")
        self.lateral.pack_propagate(False)

        self._construir_lateral()

        self.btn_reintentar = ctk.CTkButton(
            self.lateral,
            text="Reintentar cámara",
            height=40,
            fg_color=tema.COLOR_ACENTO,
            hover_color=tema.COLOR_ACENTO_HOVER,
            text_color=tema.COLOR_TEXTO_INVERSO,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=12,
            command=self._iniciar_pipeline,
        )

        _pie(self, texto_pie)

        self._iniciar_pipeline()
        self.focus_set()
        self.bind("<Button-1>", lambda _e: self.focus_set())
        self._tick_id = self.after(_INTERVALO_MS, self._tick)

    def _construir_lateral(self) -> None:
        raise NotImplementedError

    def cerrar_y_volver(self) -> None:
        self.cerrar_pantalla()
        self._on_volver()

    def cerrar_pantalla(self) -> None:
        self._vivo = False
        self._soltar_hold_interno()
        if self._tick_id is not None:
            try:
                self.after_cancel(self._tick_id)
            except Exception:  # noqa: BLE001
                pass
            self._tick_id = None
        if self._pipeline is not None:
            self._pipeline.cerrar()
            self._pipeline = None
        self.destroy()

    def iniciar_hold(self) -> None:
        if self._hold_activo or self._pipeline is None:
            return
        self._hold_activo = True
        self._al_iniciar_hold()

    def soltar_hold(self) -> None:
        if not self._hold_activo:
            return
        self._hold_activo = False
        self._al_soltar_hold()

    def _soltar_hold_interno(self) -> None:
        if self._hold_activo:
            self._hold_activo = False
            try:
                self._al_soltar_hold()
            except Exception:  # noqa: BLE001
                pass

    def _al_iniciar_hold(self) -> None:
        return

    def _al_soltar_hold(self) -> None:
        return

    def _iniciar_pipeline(self) -> None:
        if self._pipeline is not None:
            self._pipeline.cerrar()
            self._pipeline = None
        try:
            self._pipeline = crear_pipeline(
                modo_demo=self._modo_demo,
                indice_camara=self._indice_camara,
                ajustes=self._ajustes,
                categoria=self._categoria,
            )
            self.btn_reintentar.pack_forget()
            self._al_pipeline_listo()
        except CamaraNoDisponibleError:
            self.btn_reintentar.pack(padx=20, pady=(4, 20), fill="x")
            self._mostrar_error_camara()

    def _al_pipeline_listo(self) -> None:
        return

    def _mostrar_error_camara(self) -> None:
        self._mostrar_bgr(
            frame_mensaje(
                list(textos.LINEAS_CAMARA_VIDEO),
                ANCHO_VIDEO,
                ALTO_VIDEO,
                color_titulo_bgr=tema.BGR_INDIGO,
            )
        )

    def _tick(self) -> None:
        if not self._vivo:
            return
        if self._pipeline is not None:
            try:
                procesado = self._pipeline.procesar(reconocer=self._reconocer)
            except Exception as exc:  # noqa: BLE001
                self._on_error_tick(exc)
            else:
                if procesado is not None:
                    self._mostrar_bgr(procesado.imagen)
                    self._on_procesado(procesado)
        self._tick_id = self.after(_INTERVALO_MS, self._tick)

    def _on_error_tick(self, exc: Exception) -> None:
        del exc

    def _on_procesado(self, procesado: Any) -> None:
        del procesado

    def _mostrar_aviso_vacio(self, aviso: ctk.CTkFrame, visible: bool) -> None:
        mostrado = bool(getattr(aviso, "_mamatlatolli_visible", True))
        if visible == mostrado:
            return
        if visible:
            aviso.pack(fill="x", padx=16, pady=(16, 4), before=self.lateral.winfo_children()[0])
        else:
            aviso.pack_forget()
        aviso._mamatlatolli_visible = visible

    def _mostrar_bgr(self, frame_bgr) -> None:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        imagen = ctk.CTkImage(light_image=pil, dark_image=pil, size=(ANCHO_VIDEO, ALTO_VIDEO))
        self._img_ref = imagen
        self.lbl_video.configure(image=imagen)

    def _avisar(self, texto: str, color: str, segundos: float = 2.8) -> None:
        self._aviso_hasta = time.monotonic() + segundos
        widget = getattr(self, "lbl_mensaje", None)
        if widget is not None:
            widget.configure(text=texto, text_color=color)


class PantallaReconocimiento(_PantallaConCamara):
    def __init__(
        self,
        master: Any,
        *,
        modo_demo: bool,
        indice_camara: int,
        ajustes: Ajustes,
        on_volver: Callable[[], None],
        aviso_inicial: str = "",
        categoria: str = CATEGORIA_LETRA,
        nombre_pantalla: str | None = None,
        subtitulo_pantalla: str | None = None,
    ) -> None:
        self._aviso_inicial = aviso_inicial
        self._es_vocabulario = categoria == CATEGORIA_PALABRA
        if nombre_pantalla:
            titulo = nombre_pantalla
            sub = subtitulo_pantalla or textos.SUBTITULO_DEMO
        elif self._es_vocabulario:
            titulo = "Vocabulario"
            sub = textos.SUBTITULO_VOCABULARIO_DEMO if modo_demo else textos.SUBTITULO_VOCABULARIO
        else:
            titulo = "Abecedario"
            sub = textos.SUBTITULO_ABECEDARIO_DEMO if modo_demo else textos.SUBTITULO_ABECEDARIO
        super().__init__(
            master,
            modo_demo=modo_demo,
            indice_camara=indice_camara,
            ajustes=ajustes,
            on_volver=on_volver,
            titulo=titulo,
            subtitulo=sub,
            reconocer=True,
            categoria=categoria,
        )
        if aviso_inicial:
            self._avisar(aviso_inicial, tema.COLOR_AVISO, 4.0)

    def _construir_lateral(self) -> None:
        titulo_vacio, detalle_vacio = textos.texto_vacio_reconocimiento(
            CATEGORIA_PALABRA if self._es_vocabulario else CATEGORIA_LETRA
        )
        self.aviso_vacio = _tarjeta_aviso(self.lateral, titulo_vacio, detalle_vacio)
        self.aviso_vacio.pack(fill="x", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            self.lateral,
            text="Seña estable",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(12, 4))
        self.lbl_sena = ctk.CTkLabel(
            self.lateral,
            text="—",
            font=ctk.CTkFont(size=40, weight="bold"),
            text_color=tema.COLOR_ACENTO,
            wraplength=300,
        )
        self.lbl_sena.pack(anchor="w", padx=20, pady=(0, 6))
        self.lbl_cruda = ctk.CTkLabel(
            self.lateral,
            text=textos.texto_lectura("—", 0),
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        )
        self.lbl_cruda.pack(anchor="w", padx=20, pady=(0, 4))
        self.lbl_modo = ctk.CTkLabel(
            self.lateral,
            text=textos.texto_modo("estatico", False),
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO,
            wraplength=310,
            justify="left",
        )
        self.lbl_modo.pack(anchor="w", padx=20, pady=(0, 8))
        self.lbl_mensaje = ctk.CTkLabel(
            self.lateral,
            text="Esperando la cámara…",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO,
            wraplength=310,
            justify="left",
        )
        self.lbl_mensaje.pack(anchor="w", padx=20, pady=(0, 10))

        self.btn_movimiento = ctk.CTkButton(
            self.lateral,
            text="Seña con movimiento",
            height=40,
            fg_color=tema.COLOR_NARANJA,
            hover_color=tema.COLOR_NARANJA_HOVER,
            text_color=tema.COLOR_TEXTO_INVERSO,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=12,
            command=self._alternar_hold,
        )
        self.btn_movimiento.pack(fill="x", padx=20, pady=(4, 4))
        ctk.CTkLabel(
            self.lateral,
            text="Clic para grabar o soltar. También puedes mantener Espacio.",
            font=ctk.CTkFont(size=12),
            text_color=tema.COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 8))

        self.lbl_plantillas = ctk.CTkLabel(
            self.lateral,
            text=textos.texto_conteo_senas(0, 0),
            font=ctk.CTkFont(size=12),
            text_color=tema.COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        )
        self.lbl_plantillas.pack(anchor="w", padx=20, pady=(0, 8))

        ctk.CTkLabel(
            self.lateral,
            text="Lo que ya leímos",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(4, 4))
        self.txt_transcripcion = ctk.CTkTextbox(
            self.lateral,
            height=140,
            fg_color=tema.COLOR_CAMPO,
            text_color=tema.COLOR_TEXTO,
            border_color=tema.COLOR_BORDE,
            font=ctk.CTkFont(size=14),
            wrap="word",
            state="disabled",
        )
        self.txt_transcripcion.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.lbl_estado = ctk.CTkLabel(
            self.lateral,
            text="Manos: 0   ·   Cámara: —",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
            wraplength=300,
            justify="left",
        )
        self.lbl_estado.pack(anchor="w", padx=20, pady=(4, 8))

    def _alternar_hold(self) -> None:
        if self._hold_activo:
            self.soltar_hold()
        else:
            self.iniciar_hold()

    def _al_iniciar_hold(self) -> None:
        if self._pipeline is not None:
            self._pipeline.set_forzar_dinamico(True)
        self.btn_movimiento.configure(text="Grabando… (clic o suelta Espacio)", fg_color=tema.COLOR_NARANJA_HOVER)

    def _al_soltar_hold(self) -> None:
        if self._pipeline is not None:
            self._pipeline.set_forzar_dinamico(False)
        self.btn_movimiento.configure(text="Seña con movimiento", fg_color=tema.COLOR_NARANJA)

    def _al_pipeline_listo(self) -> None:
        if self._pipeline is not None:
            self._actualizar_conteo(self._pipeline.n_estaticas, self._pipeline.n_dinamicas)

    def _mostrar_error_camara(self) -> None:
        self.lbl_sena.configure(text="—")
        self.lbl_cruda.configure(text=textos.texto_lectura("—", 0))
        self.lbl_mensaje.configure(text=MENSAJE_CAMARA_AUSENTE, text_color=tema.COLOR_ERROR)
        self.lbl_estado.configure(text=textos.texto_estado_manos(0, "", camara_ausente=True))
        super()._mostrar_error_camara()

    def _on_error_tick(self, exc: Exception) -> None:
        del exc
        self.lbl_mensaje.configure(text=textos.MENSAJE_ERROR_IMAGEN, text_color=tema.COLOR_ERROR)

    def _on_procesado(self, procesado: Any) -> None:
        self.lbl_sena.configure(text=textos.etiqueta_visible(procesado.resultado.etiqueta))
        self.lbl_cruda.configure(
            text=textos.texto_lectura(
                procesado.resultado.etiqueta_cruda,
                procesado.resultado.confianza_cruda,
            )
        )
        self.lbl_modo.configure(text=textos.texto_modo(procesado.resultado.modo, procesado.resultado.en_movimiento))
        if time.monotonic() >= self._aviso_hasta:
            color_msg = tema.COLOR_AVISO if procesado.manos else tema.COLOR_TEXTO_MUDO
            if procesado.resultado.etiqueta not in {"—", "detectando…"}:
                color_msg = tema.COLOR_ACENTO
            if procesado.resultado.modo == "grabando":
                color_msg = tema.COLOR_AVISO
            self.lbl_mensaje.configure(text=procesado.resultado.mensaje or "", text_color=color_msg)
        self.lbl_estado.configure(text=textos.texto_estado_manos(len(procesado.manos), procesado.fuente))
        self._actualizar_conteo(procesado.n_estaticas, procesado.n_dinamicas)
        self._escribir_transcripcion(procesado.transcripcion)

    def _actualizar_conteo(self, n_e: int, n_d: int) -> None:
        self.lbl_plantillas.configure(text=textos.texto_conteo_senas(n_e, n_d))
        self._mostrar_aviso_vacio(self.aviso_vacio, n_e + n_d == 0)

    def _escribir_transcripcion(self, lineas: list[str]) -> None:
        vacio = textos.texto_transcripcion_vacia(palabras=getattr(self, "_es_vocabulario", False))
        texto = "\n".join(lineas) if lineas else vacio
        caja = self.txt_transcripcion
        caja.configure(state="normal")
        actual = caja.get("1.0", "end-1c")
        if actual != texto:
            caja.delete("1.0", "end")
            caja.insert("1.0", texto)
            caja.see("end")
        caja.configure(state="disabled")


class PantallaPractica(_PantallaConCamara):
    """Mini juego: letra estática, cronómetro de 5 s y puntos por rapidez."""

    def __init__(
        self,
        master: Any,
        *,
        modo_demo: bool,
        indice_camara: int,
        ajustes: Ajustes,
        on_volver: Callable[[], None],
        on_record: Callable[[int], None] | None = None,
        audio: AudioMiniJuego | None = None,
    ) -> None:
        self._on_record = on_record
        self._audio = audio if audio is not None else AudioMiniJuego()
        self._letras = letras_estaticas_disponibles()
        self._record_guardado = False
        self._record_anunciado = False
        self._record_referencia = cargar_record_practica()
        self._partida: PartidaPractica | None = None
        if self._letras:
            self._partida = PartidaPractica(self._letras, record=self._record_referencia)
        super().__init__(
            master,
            modo_demo=modo_demo,
            indice_camara=indice_camara,
            ajustes=ajustes,
            on_volver=on_volver,
            titulo=textos.titulo_pantalla("practica"),
            subtitulo=textos.SUBTITULO_MINIJUEGO,
            reconocer=True,
            categoria=CATEGORIA_LETRA,
            texto_pie=textos.PIE_JUEGO,
        )

    def _construir_lateral(self) -> None:
        self.marco_juego = ctk.CTkFrame(self.lateral, fg_color="transparent")
        self.marco_vacio = ctk.CTkFrame(
            self.lateral,
            fg_color=tema.COLOR_TARJETA,
            corner_radius=16,
            border_width=1,
            border_color=tema.COLOR_INDIGO,
        )

        ctk.CTkLabel(
            self.marco_juego,
            text="Seña esta letra",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(18, 0))
        self.lbl_letra = ctk.CTkLabel(
            self.marco_juego,
            text="—",
            font=ctk.CTkFont(size=84, weight="bold"),
            text_color=tema.COLOR_ACENTO,
        )
        self.lbl_letra.pack(anchor="w", padx=20, pady=(0, 0))
        self._crono_lado = 132
        self._crono_ref: ctk.CTkImage | None = None
        self.lbl_crono = ctk.CTkLabel(self.marco_juego, text="")
        self.lbl_crono.pack(anchor="w", padx=20, pady=(0, 0))
        self.lbl_tiempo = ctk.CTkLabel(
            self.marco_juego,
            text="5.0 s",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=tema.COLOR_TEXTO,
        )
        self.lbl_tiempo.pack(anchor="w", padx=20, pady=(0, 6))
        self.lbl_puntos = ctk.CTkLabel(
            self.marco_juego,
            text="Puntos: 0",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=tema.COLOR_TEXTO,
        )
        self.lbl_puntos.pack(anchor="w", padx=20, pady=(0, 2))
        self.lbl_record = ctk.CTkLabel(
            self.marco_juego,
            text="Récord: 0",
            font=ctk.CTkFont(size=16),
            text_color=tema.COLOR_TEXTO_MUDO,
        )
        self.lbl_record.pack(anchor="w", padx=20, pady=(0, 8))
        self.lbl_sena = ctk.CTkLabel(
            self.marco_juego,
            text="Tu seña estable: —",
            font=ctk.CTkFont(size=14),
            text_color=tema.COLOR_TEXTO,
            wraplength=310,
            justify="left",
        )
        self.lbl_sena.pack(anchor="w", padx=20, pady=(0, 6))
        self.lbl_mensaje = ctk.CTkLabel(
            self.marco_juego,
            text="Seña la letra y mantenla quieta antes de que termine el tiempo.",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        )
        self.lbl_mensaje.pack(anchor="w", padx=20, pady=(0, 8))

        self.btn_inicio = ctk.CTkButton(
            self.marco_juego,
            text="Inicio",
            height=42,
            fg_color=tema.COLOR_ACENTO,
            hover_color=tema.COLOR_ACENTO_HOVER,
            text_color=tema.COLOR_TEXTO_INVERSO,
            font=ctk.CTkFont(size=16, weight="bold"),
            corner_radius=12,
            command=self._pulsar_inicio,
        )

        self.marco_fin = ctk.CTkFrame(self.marco_juego, fg_color="transparent")
        ctk.CTkButton(
            self.marco_fin,
            text="Menú",
            fg_color=tema.COLOR_CAMPO,
            hover_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO,
            corner_radius=12,
            command=self.cerrar_y_volver,
        ).pack(fill="x")

        ctk.CTkLabel(
            self.marco_vacio,
            text=textos.titulo_vacio_minijuego(),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=tema.COLOR_TEXTO,
            wraplength=310,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(22, 8))
        ctk.CTkLabel(
            self.marco_vacio,
            text=MENSAJE_SIN_LETRAS,
            font=ctk.CTkFont(size=14),
            text_color=tema.COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))
        self.lbl_record_vacio = ctk.CTkLabel(
            self.marco_vacio,
            text=f"Récord: {cargar_record_practica()}",
            font=ctk.CTkFont(size=16),
            text_color=tema.COLOR_TEXTO,
        )
        self.lbl_record_vacio.pack(anchor="w", padx=20, pady=(0, 8))

        if self._partida is None:
            self.marco_vacio.pack(fill="both", expand=True)
        else:
            self.marco_juego.pack(fill="both", expand=True)
            self._pintar(_vista_inicial(self._partida))

        self.lbl_estado = ctk.CTkLabel(
            self.lateral,
            text="Manos: 0   ·   Cámara: —",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
            wraplength=300,
            justify="left",
        )
        self.lbl_estado.pack(anchor="w", padx=20, pady=(8, 12))

    def _al_pipeline_listo(self) -> None:
        if self._pipeline is not None:
            self._pipeline.set_solo_estatico(True)
            self._pipeline.reiniciar_estabilidad()

    def _mostrar_error_camara(self) -> None:
        if getattr(self, "lbl_mensaje", None) is not None and self._partida is not None:
            self.lbl_mensaje.configure(text=MENSAJE_CAMARA_AUSENTE, text_color=tema.COLOR_ERROR)
        self.lbl_estado.configure(text=textos.texto_estado_manos(0, "", camara_ausente=True))
        super()._mostrar_error_camara()

    def _on_error_tick(self, exc: Exception) -> None:
        del exc
        if getattr(self, "lbl_mensaje", None) is not None:
            self.lbl_mensaje.configure(text=textos.MENSAJE_ERROR_IMAGEN, text_color=tema.COLOR_ERROR)

    def cerrar_pantalla(self) -> None:
        audio = getattr(self, "_audio", None)
        if audio is not None:
            audio.cerrar()
        super().cerrar_pantalla()

    def _on_procesado(self, procesado: Any) -> None:
        n = len(procesado.manos)
        self.lbl_estado.configure(text=textos.texto_estado_manos(n, procesado.fuente))
        if self._partida is None or not self._partida.en_curso:
            return
        estable = procesado.resultado.etiqueta or "—"
        self.lbl_sena.configure(text=f"Tu seña estable: {estable}")
        antes = self._partida.puntuacion
        vista = self._partida.observar_resultado(time.monotonic(), procesado.resultado)
        # No se reinicia el filtro aquí: un fotograma sin compromiso parece
        # que la persona soltó la seña y el bloqueo se levanta. Si la misma
        # seña sigue estable, volvería a sumar o cerraría la ronda al instante.
        self._pintar(vista)
        if vista.terminado:
            self._audio.detener_reloj()
        if vista.acierto or vista.terminado:
            for nombre in sonidos_para(
                vista,
                puntuacion_antes=antes,
                record_guardado=self._record_referencia,
                record_anunciado=self._record_anunciado,
            ):
                if nombre == "record":
                    self._record_anunciado = True
                self._audio.reproducir(nombre)
        if vista.terminado:
            self._guardar_record(vista)

    def _pintar(self, vista: VistaPractica) -> None:
        visible = vista.letra if vista.en_curso or vista.terminado else "—"
        self.lbl_letra.configure(
            text=visible,
            text_color=tema.COLOR_ERROR if vista.terminado else tema.COLOR_ACENTO,
        )
        color_tiempo = _color_tiempo(vista.restante_s, terminado=vista.terminado)
        self.lbl_tiempo.configure(text=f"{vista.restante_s:.1f} s", text_color=color_tiempo)
        self._pintar_cronometro(vista.restante_s, color_tiempo, terminado=vista.terminado)
        self.lbl_puntos.configure(text=f"Puntos: {vista.puntuacion}")
        self.lbl_record.configure(text=f"Récord: {vista.record}")
        self._colocar_inicio(vista)
        if vista.terminado:
            color = tema.COLOR_OK if vista.nuevo_record else tema.COLOR_AVISO
            self.lbl_mensaje.configure(text=texto_fin(vista), text_color=color)
            if not self.marco_fin.winfo_ismapped():
                self.marco_fin.pack(fill="x", padx=20, pady=(4, 8))
            return
        if self.marco_fin.winfo_ismapped():
            self.marco_fin.pack_forget()
        if vista.acierto:
            self._aviso_hasta = time.monotonic() + 1.2
            self.lbl_mensaje.configure(
                text=textos.mensaje_acierto(vista.puntos_obtenidos),
                text_color=tema.COLOR_OK,
            )
            return
        if not vista.en_curso:
            if time.monotonic() >= self._aviso_hasta or vista.puntuacion <= 0:
                self.lbl_mensaje.configure(
                    text=textos.mensaje_espera_inicio(),
                    text_color=tema.COLOR_TEXTO_MUDO,
                )
            return
        if time.monotonic() >= self._aviso_hasta:
            self.lbl_mensaje.configure(
                text=textos.mensaje_durante_ronda(),
                text_color=tema.COLOR_TEXTO_MUDO,
            )

    def _colocar_inicio(self, vista: VistaPractica) -> None:
        if vista.en_curso:
            if self.btn_inicio.winfo_ismapped():
                self.btn_inicio.pack_forget()
            return
        self.btn_inicio.configure(text="Inicio")
        if not self.btn_inicio.winfo_ismapped():
            self.btn_inicio.pack(fill="x", padx=20, pady=(0, 8))

    def _pulsar_inicio(self) -> None:
        if self._partida is None:
            return
        if self._partida.terminada:
            self._preparar_partida_nueva()
            if self._partida is None:
                return
        # Partida nueva: el filtro no debe traer la seña que quedó en la espera.
        if self._pipeline is not None:
            self._pipeline.reiniciar_estabilidad()
        vista = self._partida.iniciar(time.monotonic())
        self._audio.iniciar_reloj()
        self.lbl_sena.configure(text="Tu seña estable: —")
        self._pintar(vista)

    def _guardar_record(self, vista: VistaPractica) -> None:
        if self._record_guardado:
            return
        self._record_guardado = True
        vigente = guardar_record_practica(vista.puntuacion)
        if self._partida is not None:
            self._partida.record = vigente
        self.lbl_record.configure(text=f"Récord: {vigente}")
        if self._on_record is not None:
            self._on_record(vigente)

    def _preparar_partida_nueva(self) -> None:
        """Arma otra partida en espera. El cronómetro sigue parado hasta Inicio."""
        self._audio.detener_reloj()
        self._letras = letras_estaticas_disponibles()
        self._record_guardado = False
        self._record_anunciado = False
        self._record_referencia = cargar_record_practica()
        if not self._letras:
            self._partida = None
            self.marco_juego.pack_forget()
            if not self.marco_vacio.winfo_ismapped():
                self.marco_vacio.pack(fill="both", expand=True)
            self.lbl_record_vacio.configure(text=f"Récord: {cargar_record_practica()}")
            return
        self._partida = PartidaPractica(self._letras, record=self._record_referencia)
        self.marco_vacio.pack_forget()
        if not self.marco_juego.winfo_ismapped():
            self.marco_juego.pack(fill="both", expand=True)
        if self.marco_fin.winfo_ismapped():
            self.marco_fin.pack_forget()

    def _pintar_cronometro(self, restante: float, color: str, *, terminado: bool) -> None:
        duracion = self._partida.duracion_s if self._partida is not None else 5.0
        pil = _dibujar_cronometro(
            restante,
            duracion,
            lado=self._crono_lado,
            color=color,
            pista=tema.COLOR_BORDE,
            terminado=terminado,
        )
        imagen = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
        self._crono_ref = imagen
        self.lbl_crono.configure(image=imagen)


def _vista_inicial(partida: PartidaPractica) -> VistaPractica:
    return VistaPractica(
        letra=partida.letra,
        puntuacion=0,
        record=partida.record,
        restante_s=partida.duracion_s,
        acierto=False,
        terminado=False,
        motivo=None,
        nuevo_record=False,
    )


def _dibujar_cronometro(
    restante: float,
    duracion: float,
    *,
    lado: int,
    color: str,
    pista: str,
    terminado: bool = False,
) -> Image.Image:
    """Aro que se vacía en el sentido del reloj. 1 = tiempo completo."""
    fraccion = 0.0 if duracion <= 0 else max(0.0, min(1.0, restante / duracion))
    if terminado:
        fraccion = 0.0
    imagen = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    draw = ImageDraw.Draw(imagen)
    margen = max(4, int(lado * 0.08))
    caja = (margen, margen, lado - 1 - margen, lado - 1 - margen)
    grosor = max(8, lado // 11)
    draw.arc(caja, 0, 360, fill=hex_a_rgb(pista) + (255,), width=grosor)
    if fraccion >= 0.999:
        draw.ellipse(caja, outline=hex_a_rgb(color) + (255,), width=grosor)
    elif fraccion > 0.001:
        barrido = 360.0 * fraccion
        # Desde las 12, el tramo que queda se dibuja en sentido horario.
        draw.arc(caja, -90 - barrido, -90, fill=hex_a_rgb(color) + (255,), width=grosor)
    return imagen


def _color_tiempo(restante: float, *, terminado: bool) -> str:
    if terminado or restante < 1.0:
        return tema.COLOR_ERROR
    if restante < 2.0:
        return tema.COLOR_AVISO
    return tema.COLOR_TEXTO


class PantallaCaptura(_PantallaConCamara):
    def __init__(
        self,
        master: Any,
        *,
        modo_demo: bool,
        indice_camara: int,
        ajustes: Ajustes,
        on_volver: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            modo_demo=modo_demo,
            indice_camara=indice_camara,
            ajustes=ajustes,
            on_volver=on_volver,
            titulo=textos.titulo_pantalla("captura"),
            subtitulo=textos.SUBTITULO_CAPTURA,
            reconocer=False,
            categoria=CATEGORIA_TODAS,
        )

    def _construir_lateral(self) -> None:
        titulo_vacio, detalle_vacio = textos.texto_vacio_captura()
        self.aviso_vacio = _tarjeta_aviso(self.lateral, titulo_vacio, detalle_vacio)
        self.aviso_vacio.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            self.lateral,
            text="¿Letra o palabra?",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(8, 4))
        self.seg_categoria = SelectorPastillas(
            self.lateral,
            (("Letra", "Letra"), ("Palabra", "Palabra")),
            "Letra",
            self._on_categoria,
            ancho=110,
        )
        self.seg_categoria.pack(anchor="w", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.lateral,
            text="¿Quieta o con movimiento?",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(4, 4))
        self.seg_tipo = SelectorPastillas(
            self.lateral,
            (("Estática", "Estática"), ("Dinámica", "Dinámica")),
            "Estática",
            self._on_tipo,
            ancho=120,
        )
        self.seg_tipo.pack(anchor="w", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.lateral,
            text="Letra o palabra",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(4, 4))
        self.ent_etiqueta = ctk.CTkEntry(
            self.lateral,
            placeholder_text="Ej. A, Ñ o J",
            fg_color=tema.COLOR_CAMPO,
            border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO,
            placeholder_text_color=tema.COLOR_TEXTO_MUDO,
        )
        self.ent_etiqueta.pack(fill="x", padx=20, pady=(0, 10))

        self.btn_guardar = ctk.CTkButton(
            self.lateral,
            text="Guardar seña",
            height=40,
            fg_color=tema.COLOR_ACENTO,
            hover_color=tema.COLOR_ACENTO_HOVER,
            text_color=tema.COLOR_TEXTO_INVERSO,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=12,
            command=self._guardar_o_alternar,
        )
        self.btn_guardar.pack(fill="x", padx=20, pady=(4, 6))

        self.lbl_ayuda = ctk.CTkLabel(
            self.lateral,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        )
        self.lbl_ayuda.pack(anchor="w", padx=20, pady=(0, 8))
        self._on_tipo("Estática")

        self.lbl_mensaje = ctk.CTkLabel(
            self.lateral,
            text="Esperando la cámara…",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO,
            wraplength=310,
            justify="left",
        )
        self.lbl_mensaje.pack(anchor="w", padx=20, pady=(0, 10))

        self.lbl_plantillas = ctk.CTkLabel(
            self.lateral,
            text=textos.texto_conteo_senas(0, 0),
            font=ctk.CTkFont(size=12),
            text_color=tema.COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        )
        self.lbl_plantillas.pack(anchor="w", padx=20, pady=(0, 8))
        self.lbl_estado = ctk.CTkLabel(
            self.lateral,
            text="Manos: 0   ·   Cámara: —",
            font=ctk.CTkFont(size=13),
            text_color=tema.COLOR_TEXTO_MUDO,
            wraplength=300,
            justify="left",
        )
        self.lbl_estado.pack(anchor="w", padx=20, pady=(4, 8))

    def _tipo_dinamico(self) -> bool:
        return (self.seg_tipo.get() or "") == "Dinámica"

    def _categoria_actual(self) -> str:
        return CATEGORIA_PALABRA if (self.seg_categoria.get() or "") == "Palabra" else CATEGORIA_LETRA

    def _on_categoria(self, valor: str) -> None:
        if getattr(self, "ent_etiqueta", None) is None:
            return
        if valor == "Palabra":
            self.ent_etiqueta.configure(placeholder_text="Ej. HOLA o GRACIAS")
        else:
            self.ent_etiqueta.configure(placeholder_text="Ej. A, Ñ o J")
        self._sincronizar_cuerpo()
        self._on_tipo(self.seg_tipo.get() or "Estática")

    def _sincronizar_cuerpo(self) -> None:
        if self._pipeline is None:
            return
        self._pipeline.set_usar_cuerpo(self._categoria_actual() == CATEGORIA_PALABRA)

    def _on_tipo(self, valor: str) -> None:
        if getattr(self, "btn_guardar", None) is None or getattr(self, "lbl_ayuda", None) is None:
            return
        es_palabra = self._categoria_actual() == CATEGORIA_PALABRA
        dinamica = valor == "Dinámica"
        if dinamica:
            self.btn_guardar.configure(
                text="Seña con movimiento",
                fg_color=tema.COLOR_NARANJA,
                hover_color=tema.COLOR_NARANJA_HOVER,
            )
        else:
            self.btn_guardar.configure(
                text="Guardar seña",
                fg_color=tema.COLOR_ACENTO,
                hover_color=tema.COLOR_ACENTO_HOVER,
            )
        self.lbl_ayuda.configure(text=textos.ayuda_captura(palabra=es_palabra, dinamica=dinamica))

    def _guardar_o_alternar(self) -> None:
        if self._tipo_dinamico():
            if self._hold_activo:
                self.soltar_hold()
            else:
                self.iniciar_hold()
            return
        self._guardar_estatica()

    def _al_iniciar_hold(self) -> None:
        if not self._tipo_dinamico():
            self._hold_activo = False
            return
        if self._pipeline is None:
            self._hold_activo = False
            self._avisar(textos.MENSAJE_SIN_CAMARA_ACCION, tema.COLOR_ERROR)
            return
        etiqueta = (self.ent_etiqueta.get() or "").strip()
        if not etiqueta:
            self._hold_activo = False
            self._avisar(
                textos.mensaje_falta_etiqueta(
                    palabra=self._categoria_actual() == CATEGORIA_PALABRA,
                    grabando=True,
                ),
                tema.COLOR_ERROR,
            )
            return
        self._pipeline.iniciar_grabacion()
        self.btn_guardar.configure(text="Grabando… suelta para guardar", fg_color=tema.COLOR_NARANJA_HOVER)

    def _al_soltar_hold(self) -> None:
        self.btn_guardar.configure(text="Seña con movimiento", fg_color=tema.COLOR_NARANJA)
        if self._pipeline is None:
            return
        frames = self._pipeline.detener_grabacion()
        etiqueta = (self.ent_etiqueta.get() or "").strip()
        if not etiqueta:
            self._avisar(textos.mensaje_grabacion_descartada(), tema.COLOR_ERROR)
            return
        try:
            self._pipeline.guardar_plantilla(
                etiqueta,
                tipo="dinamico",
                fotogramas=frames,
                consentimiento=True,
                categoria=self._categoria_actual(),
            )
        except ValueError as exc:
            self._avisar(str(exc), tema.COLOR_ERROR)
            return
        except Exception:  # noqa: BLE001
            self._avisar(textos.mensaje_no_se_pudo_guardar(), tema.COLOR_ERROR)
            return
        self._avisar(
            textos.mensaje_plantilla_guardada(
                etiqueta,
                palabra=self._categoria_actual() == CATEGORIA_PALABRA,
                dinamica=True,
            ),
            tema.COLOR_OK,
        )
        self._actualizar_conteo(self._pipeline.n_estaticas, self._pipeline.n_dinamicas)

    def _guardar_estatica(self) -> None:
        etiqueta = (self.ent_etiqueta.get() or "").strip()
        if not etiqueta:
            self._avisar(
                textos.mensaje_falta_etiqueta(
                    palabra=self._categoria_actual() == CATEGORIA_PALABRA,
                    grabando=False,
                ),
                tema.COLOR_ERROR,
            )
            return
        if self._pipeline is None:
            self._avisar(textos.MENSAJE_SIN_CAMARA_ACCION, tema.COLOR_ERROR)
            return
        try:
            self._pipeline.guardar_plantilla(
                etiqueta,
                consentimiento=True,
                tipo="estatico",
                categoria=self._categoria_actual(),
            )
        except ValueError as exc:
            self._avisar(str(exc), tema.COLOR_ERROR)
            return
        except Exception:  # noqa: BLE001
            self._avisar(textos.mensaje_no_se_pudo_guardar(), tema.COLOR_ERROR)
            return
        self._avisar(
            textos.mensaje_plantilla_guardada(
                etiqueta,
                palabra=self._categoria_actual() == CATEGORIA_PALABRA,
                dinamica=False,
            ),
            tema.COLOR_OK,
        )
        self._actualizar_conteo(self._pipeline.n_estaticas, self._pipeline.n_dinamicas)

    def _al_pipeline_listo(self) -> None:
        self._sincronizar_cuerpo()
        if self._pipeline is not None:
            self._actualizar_conteo(self._pipeline.n_estaticas, self._pipeline.n_dinamicas)

    def _mostrar_error_camara(self) -> None:
        self.lbl_mensaje.configure(text=MENSAJE_CAMARA_AUSENTE, text_color=tema.COLOR_ERROR)
        self.lbl_estado.configure(text=textos.texto_estado_manos(0, "", camara_ausente=True))
        super()._mostrar_error_camara()

    def _on_error_tick(self, exc: Exception) -> None:
        del exc
        self.lbl_mensaje.configure(text=textos.MENSAJE_ERROR_IMAGEN, text_color=tema.COLOR_ERROR)

    def _on_procesado(self, procesado: Any) -> None:
        n = len(procesado.manos)
        self.lbl_estado.configure(text=textos.texto_estado_manos(n, procesado.fuente))
        self._actualizar_conteo(procesado.n_estaticas, procesado.n_dinamicas)
        if time.monotonic() >= self._aviso_hasta:
            if self._hold_activo:
                self.lbl_mensaje.configure(
                    text=textos.mensaje_grabando(),
                    text_color=tema.COLOR_AVISO,
                )
            else:
                color = tema.COLOR_ACENTO if procesado.manos else tema.COLOR_TEXTO_MUDO
                self.lbl_mensaje.configure(text=procesado.resultado.mensaje or "", text_color=color)

    def _actualizar_conteo(self, n_e: int, n_d: int) -> None:
        self.lbl_plantillas.configure(text=textos.texto_conteo_senas(n_e, n_d))
        self._mostrar_aviso_vacio(self.aviso_vacio, n_e + n_d == 0)


class PantallaBiblioteca(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        *,
        on_volver: Callable[[], None],
        on_probar: Callable[[str, str], None],
        ruta_plantillas=RUTA_PLANTILLAS,
    ) -> None:
        super().__init__(master, fg_color=tema.COLOR_FONDO)
        self._on_probar = on_probar
        self._ruta = ruta_plantillas
        _encabezado(
            self,
            textos.titulo_pantalla("biblioteca"),
            textos.SUBTITULO_BIBLIOTECA,
            on_volver,
        )
        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=28, pady=(0, 6))
        ctk.CTkLabel(
            filtros,
            text="Filtrar",
            text_color=tema.COLOR_TEXTO_MUDO,
            font=ctk.CTkFont(size=13),
        ).pack(side="left", padx=(0, 10))
        self.seg_filtro = SelectorPastillas(
            filtros,
            (("Letra", "Letra"), ("Palabra", "Palabra"), ("Todas", "Todas")),
            "Todas",
            lambda _v: self._recargar(),
            ancho=96,
        )
        self.seg_filtro.pack(side="left")
        self.lbl_resumen = ctk.CTkLabel(
            self,
            text="",
            text_color=tema.COLOR_TEXTO_MUDO,
            font=ctk.CTkFont(size=13),
        )
        self.lbl_resumen.pack(anchor="w", padx=28, pady=(0, 6))
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=tema.COLOR_CAMPO,
            corner_radius=18,
            border_width=1,
            border_color=tema.COLOR_BORDE,
        )
        self.scroll.pack(fill="both", expand=True, padx=24, pady=8)
        _pie(self, textos.PIE_VOLVER)
        self._recargar()

    def cerrar_pantalla(self) -> None:
        self.destroy()

    def _filtro_categoria(self) -> str:
        mapa = {"Letra": CATEGORIA_LETRA, "Palabra": CATEGORIA_PALABRA, "Todas": CATEGORIA_TODAS}
        return mapa.get(self.seg_filtro.get() or "Todas", CATEGORIA_TODAS)

    def _recargar(self) -> None:
        for hijo in self.scroll.winfo_children():
            hijo.destroy()
        items, errores = inventario_plantillas(self._ruta)
        visibles = filtrar_inventario(items, self._filtro_categoria())
        n_e = sum(1 for i in visibles if i.muestra.tipo == "estatico")
        n_d = sum(1 for i in visibles if i.muestra.tipo == "dinamico")
        n_letra = sum(1 for i in items if i.muestra.categoria == CATEGORIA_LETRA)
        n_palabra = sum(1 for i in items if i.muestra.categoria == CATEGORIA_PALABRA)
        extra_errores = len(errores)
        self.lbl_resumen.configure(
            text=textos.resumen_biblioteca(
                visibles=len(visibles),
                quietas=n_e,
                con_movimiento=n_d,
                letras=n_letra,
                palabras=n_palabra,
                errores=extra_errores,
                banco_vacio=not items,
            )
        )
        if not visibles:
            titulo, detalle = textos.texto_vacio_biblioteca(self.seg_filtro.get() or "Todas")
            _tarjeta_aviso(self.scroll, titulo, detalle, wrap=680).pack(fill="x", padx=12, pady=16)
            return
        for item in visibles:
            self._fila(item)

    def _fila(self, item) -> None:
        muestra = item.muestra
        tipo = "quieta" if muestra.tipo == "estatico" else "con movimiento"
        cat = "letra" if muestra.categoria == CATEGORIA_LETRA else "palabra"
        n_frames = 0
        if muestra.secuencia is not None:
            n_frames = len(muestra.secuencia.fotogramas)
        detalle = muestra.metadatos.marca_tiempo
        if n_frames:
            detalle += f"  ·  {n_frames} momentos"
        fila = ctk.CTkFrame(
            self.scroll,
            fg_color=tema.COLOR_TARJETA,
            corner_radius=14,
            border_width=1,
            border_color=tema.COLOR_BORDE,
        )
        fila.pack(fill="x", padx=8, pady=5)
        ctk.CTkLabel(
            fila,
            text=muestra.etiqueta,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=tema.COLOR_ACENTO,
            width=140,
        ).pack(side="left", padx=(12, 8), pady=10)
        info = ctk.CTkFrame(fila, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            info,
            text=f"{cat} · {tipo}",
            text_color=tema.COLOR_TEXTO,
            font=ctk.CTkFont(size=14),
        ).pack(anchor="w")
        ctk.CTkLabel(info, text=detalle, text_color=tema.COLOR_TEXTO_MUDO, font=ctk.CTkFont(size=12)).pack(anchor="w")
        ctk.CTkButton(
            fila,
            text="Probar",
            width=80,
            fg_color=tema.COLOR_ACENTO,
            hover_color=tema.COLOR_ACENTO_HOVER,
            text_color=tema.COLOR_TEXTO_INVERSO,
            corner_radius=10,
            command=lambda m=muestra: self._on_probar(m.etiqueta, m.tipo, m.categoria),
        ).pack(side="right", padx=(4, 12), pady=10)
        ctk.CTkButton(
            fila,
            text="Eliminar",
            width=90,
            fg_color=tema.COLOR_ERROR,
            hover_color=tema.COLOR_ERROR_HOVER,
            text_color=tema.COLOR_TEXTO_INVERSO,
            corner_radius=10,
            command=lambda p=item.ruta, e=muestra.etiqueta: self._eliminar(p, e),
        ).pack(side="right", padx=4, pady=10)

    def _eliminar(self, ruta, etiqueta: str) -> None:
        if not messagebox.askyesno(
            NOMBRE_PRODUCTO,
            f"¿Quieres borrar la seña «{etiqueta}»?\nEsta acción no se puede deshacer.",
        ):
            return
        eliminar_plantilla(ruta)
        self._recargar()


class PantallaConfiguracion(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        *,
        ajustes: Ajustes,
        on_volver: Callable[[], None],
        on_guardar: Callable[[Ajustes], None],
        on_cambiar_tema: Callable[..., None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=tema.COLOR_FONDO)
        self._on_guardar = on_guardar
        self._on_cambiar_tema = on_cambiar_tema
        self._base = ajustes
        _encabezado(
            self,
            textos.titulo_pantalla("configuracion"),
            textos.SUBTITULO_CONFIG,
            on_volver,
        )
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        cuerpo = ctk.CTkFrame(
            scroll,
            fg_color=tema.COLOR_TARJETA,
            corner_radius=20,
            border_width=1,
            border_color=tema.COLOR_BORDE,
        )
        cuerpo.pack(fill="x", padx=8, pady=8)

        bloque_tema = ctk.CTkFrame(cuerpo, fg_color="transparent")
        bloque_tema.pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkLabel(
            bloque_tema,
            text="Apariencia",
            text_color=tema.COLOR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            bloque_tema,
            text="Elige modo claro o modo oscuro. El cambio se ve al momento y se recuerda la próxima vez.",
            text_color=tema.COLOR_TEXTO_MUDO,
            font=ctk.CTkFont(size=13),
            wraplength=680,
            justify="left",
        ).pack(anchor="w", pady=(2, 8))
        selector_apariencia(bloque_tema, ajustes.tema, self._al_cambiar_tema).pack(anchor="w", pady=(0, 4))

        lectura = ctk.CTkFrame(
            scroll,
            fg_color=tema.COLOR_TARJETA,
            corner_radius=20,
            border_width=1,
            border_color=tema.COLOR_BORDE,
        )
        lectura.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkLabel(
            lectura,
            text="Lectura de la seña",
            text_color=tema.COLOR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(
            lectura,
            text="Si la demo se siente muy estricta o muy suelta, mueve estos controles.",
            text_color=tema.COLOR_TEXTO_MUDO,
            font=ctk.CTkFont(size=13),
            wraplength=680,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 4))

        self._umbral = _fila_slider(
            lectura,
            textos.ETIQUETA_CONFIANZA,
            0.20,
            0.95,
            ajustes.umbral_confianza,
            "{:.2f}",
            textos.AYUDA_CONFIANZA,
        )
        self._histeresis = _fila_slider(
            lectura,
            textos.ETIQUETA_MANTENER,
            0.10,
            0.90,
            ajustes.umbral_histeresis,
            "{:.2f}",
            textos.AYUDA_MANTENER,
        )
        self._consec = _fila_slider(
            lectura,
            textos.ETIQUETA_CONFIRMAR,
            2,
            20,
            float(ajustes.fotogramas_consecutivos),
            "{:.0f}",
            textos.AYUDA_CONFIRMAR,
        )
        self._sens = _fila_slider(
            lectura,
            textos.ETIQUETA_SENSIBILIDAD,
            0.0,
            1.0,
            ajustes.sensibilidad_movimiento,
            "{:.2f}",
            textos.AYUDA_SENSIBILIDAD,
        )
        self._ventana = _fila_slider(
            lectura,
            textos.ETIQUETA_VENTANA,
            0.40,
            0.80,
            ajustes.ventana_movimiento_s,
            "{:.2f}",
            textos.AYUDA_VENTANA,
        )

        ctk.CTkLabel(
            lectura,
            text=textos.ETIQUETA_METRICA,
            text_color=tema.COLOR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(12, 4))
        self.seg_metrica = SelectorPastillas(
            lectura,
            (("Por forma", "euclidiana"), ("Por dirección", "coseno")),
            ajustes.metrica if ajustes.metrica in {"euclidiana", "coseno"} else "euclidiana",
            ancho=140,
        )
        self.seg_metrica.pack(anchor="w", padx=20, pady=(0, 4))
        ctk.CTkLabel(
            lectura,
            text=textos.AYUDA_METRICA,
            text_color=tema.COLOR_TEXTO_MUDO,
            font=ctk.CTkFont(size=12),
            wraplength=680,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 16))

        self.lbl_estado = ctk.CTkLabel(
            self,
            text="",
            text_color=tema.COLOR_OK,
            font=ctk.CTkFont(size=13),
            wraplength=720,
            justify="left",
        )
        self.lbl_estado.pack(anchor="w", padx=28, pady=(2, 4))

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(fill="x", padx=28, pady=(0, 4))
        ctk.CTkButton(
            botones,
            text="Guardar ajustes",
            height=40,
            fg_color=tema.COLOR_ACENTO,
            hover_color=tema.COLOR_ACENTO_HOVER,
            text_color=tema.COLOR_TEXTO_INVERSO,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=12,
            command=self._guardar,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            botones,
            text="Volver a lo recomendado",
            height=40,
            fg_color=tema.COLOR_CAMPO,
            hover_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO,
            corner_radius=12,
            border_width=1,
            border_color=tema.COLOR_BORDE,
            command=self._restaurar,
        ).pack(side="left")

        _pie(self, textos.PIE_VOLVER)

    def cerrar_pantalla(self) -> None:
        self.destroy()

    def _leer(self) -> Ajustes:
        return Ajustes(
            umbral_confianza=self._umbral.get(),
            umbral_histeresis=self._histeresis.get(),
            fotogramas_consecutivos=int(round(self._consec.get())),
            votos_m=self._base.votos_m,
            ventana_k=self._base.ventana_k,
            sensibilidad_movimiento=self._sens.get(),
            ventana_movimiento_s=self._ventana.get(),
            umbral_movimiento=self._base.umbral_movimiento,
            metrica=self.seg_metrica.get() or "euclidiana",
            tema=self._base.tema,
            record_practica=self._base.record_practica,
        ).normalizado()

    def _al_cambiar_tema(self, modo: str) -> None:
        if self._on_cambiar_tema is None:
            return
        vista = replace(self._leer(), tema=modo).normalizado()
        self._on_cambiar_tema(modo, vista)

    def _guardar(self) -> None:
        aj = self._leer()
        guardar_ajustes(aj)
        self._on_guardar(aj)
        self.lbl_estado.configure(
            text=textos.MENSAJE_AJUSTES_GUARDADOS,
            text_color=tema.COLOR_OK,
        )

    def _restaurar(self) -> None:
        aj = Ajustes().normalizado()
        self._umbral.set(aj.umbral_confianza)
        self._histeresis.set(aj.umbral_histeresis)
        self._consec.set(float(aj.fotogramas_consecutivos))
        self._sens.set(aj.sensibilidad_movimiento)
        self._ventana.set(aj.ventana_movimiento_s)
        self.seg_metrica.set(aj.metrica)
        self.lbl_estado.configure(text=textos.MENSAJE_AJUSTES_RESTAURADOS, text_color=tema.COLOR_AVISO)


class PantallaAcercaDe(ctk.CTkFrame):
    def __init__(self, master: Any, *, on_volver: Callable[[], None]) -> None:
        super().__init__(master, fg_color=tema.COLOR_FONDO)
        _encabezado(self, textos.titulo_pantalla("acerca"), textos.SUBTITULO_ACERCA, on_volver)
        caja = ctk.CTkTextbox(
            self,
            fg_color=tema.COLOR_TARJETA,
            text_color=tema.COLOR_TEXTO,
            border_color=tema.COLOR_BORDE,
            font=ctk.CTkFont(size=15),
            wrap="word",
        )
        caja.pack(fill="both", expand=True, padx=24, pady=8)
        caja.insert("1.0", TEXTO_ACERCA)
        caja.configure(state="disabled")
        _pie(self, textos.PIE_VOLVER)

    def cerrar_pantalla(self) -> None:
        self.destroy()


def _texto_modo(modo: str, en_movimiento: bool) -> str:
    return textos.texto_modo(modo, en_movimiento)


class _FilaSlider:
    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        etiqueta: str,
        minimo: float,
        maximo: float,
        valor: float,
        formato: str,
        ayuda: str = "",
    ) -> None:
        self._formato = formato
        marco = ctk.CTkFrame(parent, fg_color="transparent")
        marco.pack(fill="x", padx=20, pady=8)
        cabeza = ctk.CTkFrame(marco, fg_color="transparent")
        cabeza.pack(fill="x")
        ctk.CTkLabel(cabeza, text=etiqueta, text_color=tema.COLOR_TEXTO, font=ctk.CTkFont(size=13, weight="bold")).pack(
            side="left"
        )
        self.lbl = ctk.CTkLabel(cabeza, text=formato.format(valor), text_color=tema.COLOR_ACENTO)
        self.lbl.pack(side="right")
        if ayuda:
            ctk.CTkLabel(
                marco,
                text=ayuda,
                text_color=tema.COLOR_TEXTO_MUDO,
                font=ctk.CTkFont(size=12),
                wraplength=680,
                justify="left",
            ).pack(anchor="w", pady=(2, 0))
        self.slider = ctk.CTkSlider(
            marco,
            from_=minimo,
            to=maximo,
            number_of_steps=80,
            progress_color=tema.COLOR_ACENTO,
            button_color=tema.COLOR_NARANJA,
            button_hover_color=tema.COLOR_NARANJA_HOVER,
            command=self._on,
        )
        self.slider.set(valor)
        self.slider.pack(fill="x", pady=(4, 0))

    def _on(self, valor: float) -> None:
        self.lbl.configure(text=self._formato.format(float(valor)))

    def get(self) -> float:
        return float(self.slider.get())

    def set(self, valor: float) -> None:
        self.slider.set(valor)
        self._on(valor)


def _fila_slider(
    parent: ctk.CTkBaseClass,
    etiqueta: str,
    minimo: float,
    maximo: float,
    valor: float,
    formato: str,
    ayuda: str = "",
) -> _FilaSlider:
    return _FilaSlider(parent, etiqueta, minimo, maximo, valor, formato, ayuda)
