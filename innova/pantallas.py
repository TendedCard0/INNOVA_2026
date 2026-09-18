"""Pantallas CustomTkinter del menú de Mamatlatolli."""

from __future__ import annotations

import time
from tkinter import messagebox
from typing import Any, Callable, Optional

import customtkinter as ctk
import cv2
from PIL import Image

from innova.ajustes import Ajustes, guardar_ajustes
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
from innova.menu import OPCIONES_MENU, TEXTO_ACERCA
from innova.overlay import frame_mensaje
from innova.pipeline import PipelineVision, crear_pipeline
from innova.plantillas import eliminar_plantilla, inventario_plantillas
from innova.tema import (
    BGR_INDIGO,
    COLOR_ACENTO,
    COLOR_ACENTO_HOVER,
    COLOR_AVISO,
    COLOR_BORDE,
    COLOR_CAMPO,
    COLOR_ERROR,
    COLOR_ERROR_HOVER,
    COLOR_FONDO,
    COLOR_NARANJA,
    COLOR_NARANJA_HOVER,
    COLOR_NARANJA_SUAVE,
    COLOR_TARJETA,
    COLOR_TARJETA_HOVER,
    COLOR_TARJETA_PRESION,
    COLOR_TEXTO,
    COLOR_TEXTO_INVERSO,
    COLOR_TEXTO_MUDO,
    TRIDADA,
    acento_de_indice,
    icono_menu,
    imagen_logo,
    nombres_iconos_menu,
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
            fg_color=COLOR_ACENTO,
            hover_color=COLOR_ACENTO_HOVER,
            text_color=COLOR_TEXTO_INVERSO,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=on_volver,
        ).pack(side="left", padx=(0, 16))
    textos = ctk.CTkFrame(barra, fg_color="transparent")
    textos.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(
        textos,
        text=titulo,
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=COLOR_TEXTO,
    ).pack(anchor="w")
    ctk.CTkLabel(
        textos,
        text=subtitulo,
        font=ctk.CTkFont(size=13),
        text_color=COLOR_TEXTO_MUDO,
    ).pack(anchor="w")
    return barra


def _pie(parent: ctk.CTkBaseClass, texto: str) -> None:
    pie = ctk.CTkFrame(parent, fg_color="transparent")
    pie.pack(fill="x", padx=24, pady=(4, 14))
    ctk.CTkLabel(
        pie,
        text=texto,
        font=ctk.CTkFont(size=12),
        text_color=COLOR_TEXTO_MUDO,
        wraplength=1000,
        justify="left",
    ).pack(anchor="w")


def _recorrer_widgets(widget: Any, fn: Callable[[Any], None]) -> None:
    fn(widget)
    for hijo in widget.winfo_children():
        _recorrer_widgets(hijo, fn)


class MarcaMamatlatolli(ctk.CTkFrame):
    """Logo real (`assets/logo.png`) o marco placeholder + wordmark."""

    def __init__(self, master: Any) -> None:
        super().__init__(master, fg_color="transparent")
        pil, _es_archivo = imagen_logo(104)
        self._logo_ctk = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
        ctk.CTkLabel(self, image=self._logo_ctk, text="").pack(pady=(4, 0))
        ctk.CTkLabel(
            self,
            text=NOMBRE_PRODUCTO,
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=COLOR_TEXTO,
        ).pack(pady=(12, 0))
        ctk.CTkLabel(
            self,
            text=SUBTITULO,
            font=ctk.CTkFont(size=14),
            text_color=COLOR_TEXTO_MUDO,
        ).pack(pady=(2, 10))
        tira = ctk.CTkFrame(self, fg_color="transparent")
        tira.pack()
        for color in TRIDADA:
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
            fg_color=COLOR_TARJETA,
            corner_radius=22,
            border_width=1,
            border_color=COLOR_BORDE,
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
            text_color=COLOR_TEXTO,
            anchor="w",
            justify="left",
        ).pack(anchor="w")
        ctk.CTkLabel(
            textos,
            text=descripcion,
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
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
        self.configure(fg_color=COLOR_TARJETA, border_color=COLOR_BORDE, border_width=1)

    def _al_entrar(self, _evento=None) -> None:
        self.configure(
            fg_color=COLOR_TARJETA_HOVER,
            border_color=self._acento,
            border_width=2,
        )

    def _al_salir(self, _evento=None) -> None:
        if not self._puntero_dentro():
            self._reposo()

    def _al_presionar(self, _evento=None) -> None:
        self.configure(
            fg_color=COLOR_TARJETA_PRESION,
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
    ) -> None:
        super().__init__(master, fg_color=COLOR_FONDO)
        self._tarjetas: list[TarjetaMenu] = []

        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x", padx=28, pady=(22, 8))
        MarcaMamatlatolli(cabecera).pack(anchor="center")

        if demo_cli:
            aviso = ctk.CTkFrame(self, fg_color=COLOR_NARANJA_SUAVE, corner_radius=14)
            aviso.pack(fill="x", padx=36, pady=(4, 8))
            ctk.CTkLabel(
                aviso,
                text="Arranque con --demo: «Iniciar reconocimiento» también usará video sintético.",
                text_color=COLOR_NARANJA_HOVER,
                font=ctk.CTkFont(size=13),
                wraplength=720,
                justify="center",
            ).pack(padx=16, pady=10)

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=28, pady=(4, 8))
        cuerpo.grid_columnconfigure(0, weight=1, uniform="menu")
        cuerpo.grid_columnconfigure(1, weight=1, uniform="menu")

        for indice, (destino, etiqueta, descripcion) in enumerate(OPCIONES_MENU):
            fila, col = divmod(indice, 2)
            cuerpo.grid_rowconfigure(fila, weight=1)
            tarjeta = TarjetaMenu(
                cuerpo,
                destino=destino,
                etiqueta=etiqueta,
                descripcion=descripcion,
                indice=indice,
                on_ir=on_ir,
            )
            tarjeta.grid(row=fila, column=col, sticky="nsew", padx=10, pady=10)
            self._tarjetas.append(tarjeta)

        _pie(self, "Esc o Q para salir    ·    Fase 2b: menú, captura dinámica y DTW")


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
    ) -> None:
        super().__init__(master, fg_color=COLOR_FONDO)
        self._modo_demo = modo_demo
        self._indice_camara = indice_camara
        self._ajustes = ajustes
        self._on_volver = on_volver
        self._reconocer = reconocer
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
            fg_color=COLOR_TARJETA,
            corner_radius=20,
            border_width=1,
            border_color=COLOR_BORDE,
        )
        panel_video.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.lbl_video = ctk.CTkLabel(panel_video, text="")
        self.lbl_video.pack(padx=12, pady=12, expand=True)

        self.lateral = ctk.CTkFrame(
            cuerpo,
            fg_color=COLOR_TARJETA,
            corner_radius=20,
            border_width=1,
            border_color=COLOR_BORDE,
            width=350,
        )
        self.lateral.pack(side="right", fill="y")
        self.lateral.pack_propagate(False)

        self._construir_lateral()

        self.btn_reintentar = ctk.CTkButton(
            self.lateral,
            text="Reintentar cámara",
            fg_color=COLOR_ACENTO,
            hover_color=COLOR_ACENTO_HOVER,
            text_color=COLOR_TEXTO_INVERSO,
            corner_radius=12,
            command=self._iniciar_pipeline,
        )

        _pie(
            self,
            "← Menú    ·    Esc o Q salen    ·    Space: seña con movimiento",
        )

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
                [
                    "No se encontró una cámara",
                    "Conecta una cámara y pulsa «Reintentar cámara».",
                    "O usa «Modo demostración» en el menú.",
                ],
                ANCHO_VIDEO,
                ALTO_VIDEO,
                    color_titulo_bgr=BGR_INDIGO,
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
    ) -> None:
        self._aviso_inicial = aviso_inicial
        titulo = "Modo demostración" if modo_demo else "Reconocimiento"
        sub = "Video sintético · sin cámara" if modo_demo else "Estático (pose) y dinámico (DTW)"
        super().__init__(
            master,
            modo_demo=modo_demo,
            indice_camara=indice_camara,
            ajustes=ajustes,
            on_volver=on_volver,
            titulo=f"{NOMBRE_PRODUCTO} · {titulo}",
            subtitulo=sub,
            reconocer=True,
        )
        if aviso_inicial:
            self._avisar(aviso_inicial, COLOR_AVISO, 4.0)

    def _construir_lateral(self) -> None:
        ctk.CTkLabel(
            self.lateral,
            text="Seña estable",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(18, 4))
        self.lbl_sena = ctk.CTkLabel(
            self.lateral,
            text="—",
            font=ctk.CTkFont(size=40, weight="bold"),
            text_color=COLOR_ACENTO,
            wraplength=300,
        )
        self.lbl_sena.pack(anchor="w", padx=20, pady=(0, 6))
        self.lbl_cruda = ctk.CTkLabel(
            self.lateral,
            text="Estimación instantánea: —",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        )
        self.lbl_cruda.pack(anchor="w", padx=20, pady=(0, 4))
        self.lbl_modo = ctk.CTkLabel(
            self.lateral,
            text="Modo: estático automático",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO,
            wraplength=310,
            justify="left",
        )
        self.lbl_modo.pack(anchor="w", padx=20, pady=(0, 8))
        self.lbl_mensaje = ctk.CTkLabel(
            self.lateral,
            text="Esperando cámara…",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO,
            wraplength=310,
            justify="left",
        )
        self.lbl_mensaje.pack(anchor="w", padx=20, pady=(0, 10))

        self.btn_movimiento = ctk.CTkButton(
            self.lateral,
            text="Seña con movimiento",
            fg_color=COLOR_NARANJA,
            hover_color=COLOR_NARANJA_HOVER,
            text_color=COLOR_TEXTO_INVERSO,
            corner_radius=12,
            command=self._alternar_hold,
        )
        self.btn_movimiento.pack(fill="x", padx=20, pady=(4, 4))
        ctk.CTkLabel(
            self.lateral,
            text="Clic para grabar/soltar, o mantén Space.",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 8))

        self.lbl_plantillas = ctk.CTkLabel(
            self.lateral,
            text="Plantillas: 0 estáticas · 0 dinámicas",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        )
        self.lbl_plantillas.pack(anchor="w", padx=20, pady=(0, 8))

        ctk.CTkLabel(
            self.lateral,
            text="Transcripción reciente",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(4, 4))
        self.txt_transcripcion = ctk.CTkTextbox(
            self.lateral,
            height=140,
            fg_color=COLOR_CAMPO,
            text_color=COLOR_TEXTO,
            border_color=COLOR_BORDE,
            font=ctk.CTkFont(size=14),
            wrap="word",
            state="disabled",
        )
        self.txt_transcripcion.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.lbl_estado = ctk.CTkLabel(
            self.lateral,
            text="Manos: 0   ·   Cámara: —",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
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
        self.btn_movimiento.configure(text="Grabando… (clic o suelta Space)", fg_color=COLOR_NARANJA_HOVER)

    def _al_soltar_hold(self) -> None:
        if self._pipeline is not None:
            self._pipeline.set_forzar_dinamico(False)
        self.btn_movimiento.configure(text="Seña con movimiento", fg_color=COLOR_NARANJA)

    def _al_pipeline_listo(self) -> None:
        if self._pipeline is not None:
            self._actualizar_conteo(self._pipeline.n_estaticas, self._pipeline.n_dinamicas)

    def _mostrar_error_camara(self) -> None:
        self.lbl_sena.configure(text="—")
        self.lbl_cruda.configure(text="Estimación instantánea: —")
        self.lbl_mensaje.configure(text=MENSAJE_CAMARA_AUSENTE, text_color=COLOR_ERROR)
        self.lbl_estado.configure(text="Manos: 0   ·   Cámara: no disponible")
        super()._mostrar_error_camara()

    def _on_error_tick(self, exc: Exception) -> None:
        self.lbl_mensaje.configure(text=f"Error al procesar: {exc}", text_color=COLOR_ERROR)

    def _on_procesado(self, procesado: Any) -> None:
        self.lbl_sena.configure(text=procesado.resultado.etiqueta)
        cruda = procesado.resultado.etiqueta_cruda or "—"
        conf = procesado.resultado.confianza_cruda
        self.lbl_cruda.configure(text=f"Estimación instantánea: {cruda}   ({conf:.0%})")
        self.lbl_modo.configure(text=_texto_modo(procesado.resultado.modo, procesado.resultado.en_movimiento))
        if time.monotonic() >= self._aviso_hasta:
            color_msg = COLOR_AVISO if procesado.manos else COLOR_TEXTO_MUDO
            if procesado.resultado.etiqueta not in {"—", "detectando…"}:
                color_msg = COLOR_ACENTO
            if procesado.resultado.modo == "grabando":
                color_msg = COLOR_AVISO
            self.lbl_mensaje.configure(text=procesado.resultado.mensaje or "", text_color=color_msg)
        n = len(procesado.manos)
        self.lbl_estado.configure(text=f"Manos: {n}   ·   {procesado.fuente}")
        self._actualizar_conteo(procesado.n_estaticas, procesado.n_dinamicas)
        self._escribir_transcripcion(procesado.transcripcion)

    def _actualizar_conteo(self, n_e: int, n_d: int) -> None:
        self.lbl_plantillas.configure(text=f"Plantillas: {n_e} estáticas · {n_d} dinámicas")

    def _escribir_transcripcion(self, lineas: list[str]) -> None:
        texto = "\n".join(lineas) if lineas else "Aún no hay letras estables."
        caja = self.txt_transcripcion
        caja.configure(state="normal")
        actual = caja.get("1.0", "end-1c")
        if actual != texto:
            caja.delete("1.0", "end")
            caja.insert("1.0", texto)
            caja.see("end")
        caja.configure(state="disabled")


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
            titulo=f"{NOMBRE_PRODUCTO} · Capturar plantillas",
            subtitulo="Organiza el banco de señas (estática o con movimiento)",
            reconocer=False,
        )

    def _construir_lateral(self) -> None:
        ctk.CTkLabel(
            self.lateral,
            text="Tipo de seña",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(18, 4))
        self.seg_tipo = ctk.CTkSegmentedButton(
            self.lateral,
            values=["Estática", "Dinámica"],
            command=self._on_tipo,
            selected_color=COLOR_ACENTO,
            selected_hover_color=COLOR_ACENTO_HOVER,
        )
        self.seg_tipo.set("Estática")
        self.seg_tipo.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.lateral,
            text="Etiqueta (letra o glosa)",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(4, 4))
        self.ent_etiqueta = ctk.CTkEntry(
            self.lateral,
            placeholder_text="Ej. A, Ñ, J, HOLA",
            fg_color=COLOR_CAMPO,
            border_color=COLOR_BORDE,
            text_color=COLOR_TEXTO,
        )
        self.ent_etiqueta.pack(fill="x", padx=20, pady=(0, 10))

        self.btn_guardar = ctk.CTkButton(
            self.lateral,
            text="Guardar pose actual",
            fg_color=COLOR_ACENTO,
            hover_color=COLOR_ACENTO_HOVER,
            text_color=COLOR_TEXTO_INVERSO,
            corner_radius=12,
            command=self._guardar_o_alternar,
        )
        self.btn_guardar.pack(fill="x", padx=20, pady=(4, 6))

        self.lbl_ayuda = ctk.CTkLabel(
            self.lateral,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        )
        self.lbl_ayuda.pack(anchor="w", padx=20, pady=(0, 8))
        self._on_tipo("Estática")

        self.lbl_mensaje = ctk.CTkLabel(
            self.lateral,
            text="Esperando cámara…",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO,
            wraplength=310,
            justify="left",
        )
        self.lbl_mensaje.pack(anchor="w", padx=20, pady=(0, 10))

        self.lbl_plantillas = ctk.CTkLabel(
            self.lateral,
            text="Plantillas: 0 estáticas · 0 dinámicas",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        )
        self.lbl_plantillas.pack(anchor="w", padx=20, pady=(0, 8))
        self.lbl_estado = ctk.CTkLabel(
            self.lateral,
            text="Manos: 0   ·   Cámara: —",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
            wraplength=300,
            justify="left",
        )
        self.lbl_estado.pack(anchor="w", padx=20, pady=(4, 8))

    def _tipo_dinamico(self) -> bool:
        return (self.seg_tipo.get() or "") == "Dinámica"

    def _on_tipo(self, valor: str) -> None:
        if valor == "Dinámica":
            self.btn_guardar.configure(
                text="Seña con movimiento",
                fg_color=COLOR_NARANJA,
                hover_color=COLOR_NARANJA_HOVER,
            )
            self.lbl_ayuda.configure(
                text="Escribe la letra (J, Ñ, Z…). Clic o Space: graba mientras te mueves; al soltar se guarda. pose y rostro quedan en null."
            )
        else:
            self.btn_guardar.configure(
                text="Guardar pose actual",
                fg_color=COLOR_ACENTO,
                hover_color=COLOR_ACENTO_HOVER,
            )
            self.lbl_ayuda.configure(
                text="Coloca la seña quieta, escribe la letra y pulsa Guardar. Varias tomas por letra mejoran el matching."
            )

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
            self._avisar("No hay cámara ni modo demostración activo.", COLOR_ERROR)
            return
        etiqueta = (self.ent_etiqueta.get() or "").strip()
        if not etiqueta:
            self._hold_activo = False
            self._avisar("Escribe la letra antes de grabar la trayectoria.", COLOR_ERROR)
            return
        self._pipeline.iniciar_grabacion()
        self.btn_guardar.configure(text="Grabando… suelta para guardar", fg_color=COLOR_NARANJA_HOVER)

    def _al_soltar_hold(self) -> None:
        self.btn_guardar.configure(text="Seña con movimiento", fg_color=COLOR_NARANJA)
        if self._pipeline is None:
            return
        frames = self._pipeline.detener_grabacion()
        etiqueta = (self.ent_etiqueta.get() or "").strip()
        if not etiqueta:
            self._avisar("Grabación descartada: faltaba la etiqueta.", COLOR_ERROR)
            return
        try:
            ruta = self._pipeline.guardar_plantilla(
                etiqueta,
                tipo="dinamico",
                fotogramas=frames,
                consentimiento=True,
            )
        except ValueError as exc:
            self._avisar(str(exc), COLOR_ERROR)
            return
        except Exception as exc:  # noqa: BLE001
            self._avisar(f"No se pudo guardar: {exc}", COLOR_ERROR)
            return
        self._avisar(f"Dinámica «{etiqueta.upper()}» guardada ({ruta.name}).", COLOR_ACENTO)
        self._actualizar_conteo(self._pipeline.n_estaticas, self._pipeline.n_dinamicas)

    def _guardar_estatica(self) -> None:
        etiqueta = (self.ent_etiqueta.get() or "").strip()
        if not etiqueta:
            self._avisar("Escribe la letra o palabra de la seña antes de guardar.", COLOR_ERROR)
            return
        if self._pipeline is None:
            self._avisar("No hay cámara ni modo demostración activo.", COLOR_ERROR)
            return
        try:
            ruta = self._pipeline.guardar_plantilla(etiqueta, consentimiento=True, tipo="estatico")
        except ValueError as exc:
            self._avisar(str(exc), COLOR_ERROR)
            return
        except Exception as exc:  # noqa: BLE001
            self._avisar(f"No se pudo guardar: {exc}", COLOR_ERROR)
            return
        self._avisar(f"Estática «{etiqueta.upper()}» guardada ({ruta.name}).", COLOR_ACENTO)
        self._actualizar_conteo(self._pipeline.n_estaticas, self._pipeline.n_dinamicas)

    def _al_pipeline_listo(self) -> None:
        if self._pipeline is not None:
            self._actualizar_conteo(self._pipeline.n_estaticas, self._pipeline.n_dinamicas)

    def _mostrar_error_camara(self) -> None:
        self.lbl_mensaje.configure(text=MENSAJE_CAMARA_AUSENTE, text_color=COLOR_ERROR)
        self.lbl_estado.configure(text="Manos: 0   ·   Cámara: no disponible")
        super()._mostrar_error_camara()

    def _on_error_tick(self, exc: Exception) -> None:
        self.lbl_mensaje.configure(text=f"Error al procesar: {exc}", text_color=COLOR_ERROR)

    def _on_procesado(self, procesado: Any) -> None:
        n = len(procesado.manos)
        self.lbl_estado.configure(text=f"Manos: {n}   ·   {procesado.fuente}")
        self._actualizar_conteo(procesado.n_estaticas, procesado.n_dinamicas)
        if time.monotonic() >= self._aviso_hasta:
            if self._hold_activo:
                n_f = self._pipeline.n_fotogramas_grabacion if self._pipeline else 0
                self.lbl_mensaje.configure(
                    text=f"Grabando trayectoria… {n_f} fotogramas",
                    text_color=COLOR_AVISO,
                )
            else:
                color = COLOR_ACENTO if procesado.manos else COLOR_TEXTO_MUDO
                self.lbl_mensaje.configure(text=procesado.resultado.mensaje or "", text_color=color)

    def _actualizar_conteo(self, n_e: int, n_d: int) -> None:
        self.lbl_plantillas.configure(text=f"Plantillas: {n_e} estáticas · {n_d} dinámicas")


class PantallaBiblioteca(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        *,
        on_volver: Callable[[], None],
        on_probar: Callable[[str, str], None],
        ruta_plantillas=RUTA_PLANTILLAS,
    ) -> None:
        super().__init__(master, fg_color=COLOR_FONDO)
        self._on_probar = on_probar
        self._ruta = ruta_plantillas
        _encabezado(
            self,
            f"{NOMBRE_PRODUCTO} · Biblioteca de señas",
            "Plantillas estáticas y dinámicas guardadas en este equipo",
            on_volver,
        )
        self.lbl_resumen = ctk.CTkLabel(
            self,
            text="",
            text_color=COLOR_TEXTO_MUDO,
            font=ctk.CTkFont(size=13),
        )
        self.lbl_resumen.pack(anchor="w", padx=28, pady=(0, 6))
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=COLOR_CAMPO,
            corner_radius=18,
            border_width=1,
            border_color=COLOR_BORDE,
        )
        self.scroll.pack(fill="both", expand=True, padx=24, pady=8)
        _pie(self, "← Menú    ·    Esc o Q salen    ·    Esto organiza el banco; el uso diario es «Iniciar reconocimiento»")
        self._recargar()

    def cerrar_pantalla(self) -> None:
        self.destroy()

    def _recargar(self) -> None:
        for hijo in self.scroll.winfo_children():
            hijo.destroy()
        items, errores = inventario_plantillas(self._ruta)
        n_e = sum(1 for i in items if i.muestra.tipo == "estatico")
        n_d = sum(1 for i in items if i.muestra.tipo == "dinamico")
        extra = f"  ·  {len(errores)} archivo(s) ilegible(s)" if errores else ""
        self.lbl_resumen.configure(
            text=f"{len(items)} plantilla(s): {n_e} estáticas · {n_d} dinámicas{extra}"
        )
        if not items:
            ctk.CTkLabel(
                self.scroll,
                text="Aún no hay plantillas. Ábrelo en «Capturar plantillas».",
                text_color=COLOR_TEXTO_MUDO,
                font=ctk.CTkFont(size=14),
            ).pack(anchor="w", padx=12, pady=16)
            return
        for item in items:
            self._fila(item)

    def _fila(self, item) -> None:
        muestra = item.muestra
        tipo = "estática" if muestra.tipo == "estatico" else "dinámica"
        n_frames = 0
        if muestra.secuencia is not None:
            n_frames = len(muestra.secuencia.fotogramas)
        detalle = muestra.metadatos.marca_tiempo
        if n_frames:
            detalle += f"  ·  {n_frames} fotogramas"
        fila = ctk.CTkFrame(
            self.scroll,
            fg_color=COLOR_TARJETA,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDE,
        )
        fila.pack(fill="x", padx=8, pady=5)
        ctk.CTkLabel(
            fila,
            text=muestra.etiqueta,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLOR_ACENTO,
            width=80,
        ).pack(side="left", padx=(12, 8), pady=10)
        info = ctk.CTkFrame(fila, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(info, text=tipo, text_color=COLOR_TEXTO, font=ctk.CTkFont(size=14)).pack(anchor="w")
        ctk.CTkLabel(info, text=detalle, text_color=COLOR_TEXTO_MUDO, font=ctk.CTkFont(size=12)).pack(anchor="w")
        ctk.CTkButton(
            fila,
            text="Probar",
            width=80,
            fg_color=COLOR_ACENTO,
            hover_color=COLOR_ACENTO_HOVER,
            text_color=COLOR_TEXTO_INVERSO,
            corner_radius=10,
            command=lambda m=muestra: self._on_probar(m.etiqueta, m.tipo),
        ).pack(side="right", padx=(4, 12), pady=10)
        ctk.CTkButton(
            fila,
            text="Eliminar",
            width=90,
            fg_color=COLOR_ERROR,
            hover_color=COLOR_ERROR_HOVER,
            text_color=COLOR_TEXTO_INVERSO,
            corner_radius=10,
            command=lambda p=item.ruta, e=muestra.etiqueta: self._eliminar(p, e),
        ).pack(side="right", padx=4, pady=10)

    def _eliminar(self, ruta, etiqueta: str) -> None:
        if not messagebox.askyesno(
            NOMBRE_PRODUCTO,
            f"¿Eliminar la plantilla «{etiqueta}»?\n{ruta.name}",
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
    ) -> None:
        super().__init__(master, fg_color=COLOR_FONDO)
        self._on_guardar = on_guardar
        self._base = ajustes
        _encabezado(
            self,
            f"{NOMBRE_PRODUCTO} · Configuración",
            "Se guardan en datos/config.json y se aplican al reconocer",
            on_volver,
        )
        cuerpo = ctk.CTkFrame(
            self,
            fg_color=COLOR_TARJETA,
            corner_radius=20,
            border_width=1,
            border_color=COLOR_BORDE,
        )
        cuerpo.pack(fill="both", expand=True, padx=24, pady=8)

        self._umbral = _fila_slider(
            cuerpo, "Umbral de confianza", 0.20, 0.95, ajustes.umbral_confianza, "{:.2f}"
        )
        self._histeresis = _fila_slider(
            cuerpo, "Histéresis (mantener seña)", 0.10, 0.90, ajustes.umbral_histeresis, "{:.2f}"
        )
        self._consec = _fila_slider(
            cuerpo, "Fotogramas consecutivos", 2, 20, float(ajustes.fotogramas_consecutivos), "{:.0f}"
        )
        self._sens = _fila_slider(
            cuerpo,
            "Sensibilidad al movimiento (auto-DTW)",
            0.0,
            1.0,
            ajustes.sensibilidad_movimiento,
            "{:.2f}",
        )
        self._ventana = _fila_slider(
            cuerpo, "Ventana de movimiento (s)", 0.40, 0.80, ajustes.ventana_movimiento_s, "{:.2f}"
        )

        ctk.CTkLabel(
            cuerpo,
            text="Métrica de distancia",
            text_color=COLOR_TEXTO_MUDO,
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", padx=20, pady=(12, 4))
        self.seg_metrica = ctk.CTkSegmentedButton(
            cuerpo,
            values=["euclidiana", "coseno"],
            selected_color=COLOR_ACENTO,
            selected_hover_color=COLOR_ACENTO_HOVER,
        )
        self.seg_metrica.set(ajustes.metrica)
        self.seg_metrica.pack(anchor="w", padx=20, pady=(0, 12))

        self.lbl_estado = ctk.CTkLabel(cuerpo, text="", text_color=COLOR_ACENTO)
        self.lbl_estado.pack(anchor="w", padx=20, pady=(4, 8))

        botones = ctk.CTkFrame(cuerpo, fg_color="transparent")
        botones.pack(fill="x", padx=20, pady=(8, 16))
        ctk.CTkButton(
            botones,
            text="Guardar ajustes",
            fg_color=COLOR_ACENTO,
            hover_color=COLOR_ACENTO_HOVER,
            text_color=COLOR_TEXTO_INVERSO,
            corner_radius=12,
            command=self._guardar,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            botones,
            text="Restaurar valores por omisión",
            fg_color=COLOR_CAMPO,
            hover_color=COLOR_BORDE,
            text_color=COLOR_TEXTO,
            corner_radius=12,
            command=self._restaurar,
        ).pack(side="left")

        _pie(self, "← Menú    ·    Esc o Q salen    ·    Más sensible = más fácil pasar a DTW automático")

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
        ).normalizado()

    def _guardar(self) -> None:
        aj = self._leer()
        guardar_ajustes(aj)
        self._on_guardar(aj)
        self.lbl_estado.configure(
            text="Ajustes guardados. Se aplican al volver a «Iniciar reconocimiento».",
            text_color=COLOR_ACENTO,
        )

    def _restaurar(self) -> None:
        aj = Ajustes().normalizado()
        self._umbral.set(aj.umbral_confianza)
        self._histeresis.set(aj.umbral_histeresis)
        self._consec.set(float(aj.fotogramas_consecutivos))
        self._sens.set(aj.sensibilidad_movimiento)
        self._ventana.set(aj.ventana_movimiento_s)
        self.seg_metrica.set(aj.metrica)
        self.lbl_estado.configure(text="Valores por omisión cargados (pulsa Guardar para persistir).", text_color=COLOR_AVISO)


class PantallaAcercaDe(ctk.CTkFrame):
    def __init__(self, master: Any, *, on_volver: Callable[[], None]) -> None:
        super().__init__(master, fg_color=COLOR_FONDO)
        _encabezado(self, f"Acerca de {NOMBRE_PRODUCTO}", SUBTITULO, on_volver)
        caja = ctk.CTkTextbox(
            self,
            fg_color=COLOR_TARJETA,
            text_color=COLOR_TEXTO,
            border_color=COLOR_BORDE,
            font=ctk.CTkFont(size=15),
            wrap="word",
        )
        caja.pack(fill="both", expand=True, padx=24, pady=8)
        caja.insert("1.0", TEXTO_ACERCA)
        caja.configure(state="disabled")
        _pie(self, "← Menú    ·    Esc o Q salen")

    def cerrar_pantalla(self) -> None:
        self.destroy()


def _texto_modo(modo: str, en_movimiento: bool) -> str:
    if modo == "grabando":
        return "Modo: grabando seña con movimiento"
    if modo == "dinamico":
        return "Modo: dinámico (DTW)"
    extra = " · la mano se mueve" if en_movimiento else " · mano estable"
    return f"Modo: estático automático{extra}"


class _FilaSlider:
    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        etiqueta: str,
        minimo: float,
        maximo: float,
        valor: float,
        formato: str,
    ) -> None:
        self._formato = formato
        marco = ctk.CTkFrame(parent, fg_color="transparent")
        marco.pack(fill="x", padx=20, pady=8)
        cabeza = ctk.CTkFrame(marco, fg_color="transparent")
        cabeza.pack(fill="x")
        ctk.CTkLabel(cabeza, text=etiqueta, text_color=COLOR_TEXTO, font=ctk.CTkFont(size=13)).pack(
            side="left"
        )
        self.lbl = ctk.CTkLabel(cabeza, text=formato.format(valor), text_color=COLOR_ACENTO)
        self.lbl.pack(side="right")
        self.slider = ctk.CTkSlider(
            marco,
            from_=minimo,
            to=maximo,
            number_of_steps=80,
            progress_color=COLOR_ACENTO,
            button_color=COLOR_NARANJA,
            button_hover_color=COLOR_NARANJA_HOVER,
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
) -> _FilaSlider:
    return _FilaSlider(parent, etiqueta, minimo, maximo, valor, formato)
