"""Ventana de escritorio (CustomTkinter) de Mamatlatolli."""

from __future__ import annotations

import time
from typing import Optional

import customtkinter as ctk
import cv2
from PIL import Image

from innova.camara import CamaraNoDisponibleError
from innova.config import (
    ALTO_VIDEO,
    ANCHO_VIDEO,
    COLOR_ACENTO,
    COLOR_AVISO,
    COLOR_ERROR,
    COLOR_FONDO,
    COLOR_PANEL,
    COLOR_TEXTO,
    COLOR_TEXTO_MUDO,
    FPS_OBJETIVO,
    MENSAJE_CAMARA_AUSENTE,
    NOMBRE_PRODUCTO,
    SUBTITULO,
    TITULO_VENTANA,
)
from innova.overlay import frame_mensaje
from innova.pipeline import PipelineVision, crear_pipeline

_INTERVALO_MS = max(15, int(1000 / FPS_OBJETIVO))


class VentanaMamatlatolli(ctk.CTk):
    def __init__(self, *, modo_demo: bool = False, indice_camara: int = 0) -> None:
        super().__init__()
        self._modo_demo = modo_demo
        self._indice_camara = indice_camara
        self._pipeline: Optional[PipelineVision] = None
        self._vivo = True
        self._img_ref: Optional[ctk.CTkImage] = None
        self._error_camara = ""
        self._aviso_hasta = 0.0

        self.title(TITULO_VENTANA)
        self.geometry("1120x740")
        self.minsize(960, 660)
        self.configure(fg_color=COLOR_FONDO)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.bind_all("<Escape>", lambda _e: self._cerrar())
        self.bind_all("q", self._salir_si_no_escribe)
        self.bind_all("Q", self._salir_si_no_escribe)

        self._construir_layout()
        self._iniciar_pipeline()
        self.after(_INTERVALO_MS, self._tick)

    def _construir_layout(self) -> None:
        encabezado = ctk.CTkFrame(self, fg_color="transparent")
        encabezado.pack(fill="x", padx=24, pady=(18, 8))

        ctk.CTkLabel(
            encabezado,
            text=NOMBRE_PRODUCTO,
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=COLOR_ACENTO,
        ).pack(anchor="w")
        ctk.CTkLabel(
            encabezado,
            text=SUBTITULO,
            font=ctk.CTkFont(size=14),
            text_color=COLOR_TEXTO_MUDO,
        ).pack(anchor="w")

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=24, pady=8)

        panel_video = ctk.CTkFrame(cuerpo, fg_color=COLOR_PANEL, corner_radius=16)
        panel_video.pack(side="left", fill="both", expand=True, padx=(0, 12))

        self.lbl_video = ctk.CTkLabel(panel_video, text="")
        self.lbl_video.pack(padx=12, pady=12, expand=True)

        lateral = ctk.CTkFrame(cuerpo, fg_color=COLOR_PANEL, corner_radius=16, width=340)
        lateral.pack(side="right", fill="y")
        lateral.pack_propagate(False)

        ctk.CTkLabel(
            lateral,
            text="Seña estable",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(20, 4))

        self.lbl_sena = ctk.CTkLabel(
            lateral,
            text="—",
            font=ctk.CTkFont(size=40, weight="bold"),
            text_color=COLOR_ACENTO,
            wraplength=300,
        )
        self.lbl_sena.pack(anchor="w", padx=20, pady=(0, 6))

        self.lbl_cruda = ctk.CTkLabel(
            lateral,
            text="Estimación instantánea: —",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        )
        self.lbl_cruda.pack(anchor="w", padx=20, pady=(0, 6))

        self.lbl_mensaje = ctk.CTkLabel(
            lateral,
            text="Esperando cámara…",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO,
            wraplength=310,
            justify="left",
        )
        self.lbl_mensaje.pack(anchor="w", padx=20, pady=(0, 12))

        ctk.CTkLabel(
            lateral,
            text="Capturar plantilla",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(4, 4))

        fila_captura = ctk.CTkFrame(lateral, fg_color="transparent")
        fila_captura.pack(fill="x", padx=16, pady=(0, 4))
        self.ent_etiqueta = ctk.CTkEntry(
            fila_captura,
            placeholder_text="Letra (ej. A)",
            width=140,
        )
        self.ent_etiqueta.pack(side="left", padx=(4, 8))
        self.btn_guardar = ctk.CTkButton(
            fila_captura,
            text="Guardar",
            width=120,
            fg_color="#1B4A48",
            hover_color="#2EC4B6",
            command=self._guardar_plantilla,
        )
        self.btn_guardar.pack(side="left")

        self.lbl_plantillas = ctk.CTkLabel(
            lateral,
            text="Plantillas cargadas: 0",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXTO_MUDO,
            wraplength=310,
            justify="left",
        )
        self.lbl_plantillas.pack(anchor="w", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            lateral,
            text="Transcripción reciente",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(4, 4))

        self.txt_transcripcion = ctk.CTkTextbox(
            lateral,
            height=160,
            fg_color="#10151C",
            text_color=COLOR_TEXTO,
            font=ctk.CTkFont(size=14),
            wrap="word",
            state="disabled",
        )
        self.txt_transcripcion.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.lbl_estado = ctk.CTkLabel(
            lateral,
            text="Manos: 0   ·   Cámara: —",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
            wraplength=300,
            justify="left",
        )
        self.lbl_estado.pack(anchor="w", padx=20, pady=(4, 8))

        self.btn_reintentar = ctk.CTkButton(
            lateral,
            text="Reintentar cámara",
            fg_color="#1B4A48",
            hover_color="#2EC4B6",
            command=self._iniciar_pipeline,
        )

        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", padx=24, pady=(4, 14))
        ctk.CTkLabel(
            pie,
            text="Esc o Q para salir    ·    Fase 2a: plantillas estáticas y filtro de estabilidad",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXTO_MUDO,
        ).pack(anchor="w")

    def _iniciar_pipeline(self) -> None:
        if self._pipeline is not None:
            self._pipeline.cerrar()
            self._pipeline = None

        self._error_camara = ""
        try:
            self._pipeline = crear_pipeline(
                modo_demo=self._modo_demo,
                indice_camara=self._indice_camara,
            )
            self.btn_reintentar.pack_forget()
            self._actualizar_conteo_plantillas(self._pipeline.n_plantillas)
        except CamaraNoDisponibleError as exc:
            self._error_camara = str(exc)
            self.btn_reintentar.pack(padx=20, pady=(4, 20), fill="x")
            self.lbl_sena.configure(text="—")
            self.lbl_cruda.configure(text="Estimación instantánea: —")
            self.lbl_mensaje.configure(
                text=MENSAJE_CAMARA_AUSENTE,
                text_color=COLOR_ERROR,
            )
            self.lbl_estado.configure(text="Manos: 0   ·   Cámara: no disponible")
            self._mostrar_bgr(
                frame_mensaje(
                    [
                        "No se encontró una cámara",
                        "Conecta una cámara y pulsa «Reintentar cámara».",
                        "O inicia con:  python app.py --demo",
                    ],
                    ANCHO_VIDEO,
                    ALTO_VIDEO,
                    color_titulo_bgr=(76, 93, 232),
                )
            )

    def _tick(self) -> None:
        if not self._vivo:
            return
        if self._pipeline is not None:
            try:
                procesado = self._pipeline.procesar()
            except Exception as exc:  # noqa: BLE001 — se muestra en la UI
                self.lbl_mensaje.configure(text=f"Error al procesar: {exc}", text_color=COLOR_ERROR)
            else:
                if procesado is not None:
                    self._mostrar_bgr(procesado.imagen)
                    self.lbl_sena.configure(text=procesado.resultado.etiqueta)
                    cruda = procesado.resultado.etiqueta_cruda or "—"
                    conf = procesado.resultado.confianza_cruda
                    self.lbl_cruda.configure(
                        text=f"Estimación instantánea: {cruda}   ({conf:.0%})"
                    )
                    if time.monotonic() >= self._aviso_hasta:
                        color_msg = COLOR_AVISO if procesado.manos else COLOR_TEXTO_MUDO
                        if procesado.resultado.etiqueta not in {"—", "detectando…"}:
                            color_msg = COLOR_ACENTO
                        self.lbl_mensaje.configure(
                            text=procesado.resultado.mensaje or "",
                            text_color=color_msg,
                        )
                    n = len(procesado.manos)
                    self.lbl_estado.configure(
                        text=f"Manos: {n}   ·   {procesado.fuente}"
                    )
                    self._actualizar_conteo_plantillas(procesado.n_plantillas)
                    self._escribir_transcripcion(procesado.transcripcion)
        self.after(_INTERVALO_MS, self._tick)

    def _guardar_plantilla(self) -> None:
        etiqueta = (self.ent_etiqueta.get() or "").strip()
        if not etiqueta:
            self._avisar("Escribe la letra o palabra de la seña antes de guardar.", COLOR_ERROR)
            return
        if self._pipeline is None:
            self._avisar("No hay cámara ni modo demostración activo.", COLOR_ERROR)
            return
        try:
            ruta = self._pipeline.guardar_plantilla(etiqueta, consentimiento=True)
        except ValueError as exc:
            self._avisar(str(exc), COLOR_ERROR)
            return
        except Exception as exc:  # noqa: BLE001
            self._avisar(f"No se pudo guardar: {exc}", COLOR_ERROR)
            return
        self._avisar(f"Plantilla «{etiqueta.upper()}» guardada ({ruta.name}).", COLOR_ACENTO)
        self._actualizar_conteo_plantillas(self._pipeline.n_plantillas)

    def _avisar(self, texto: str, color: str, segundos: float = 2.8) -> None:
        self._aviso_hasta = time.monotonic() + segundos
        self.lbl_mensaje.configure(text=texto, text_color=color)

    def _actualizar_conteo_plantillas(self, n: int) -> None:
        self.lbl_plantillas.configure(text=f"Plantillas cargadas: {n}")

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

    def _mostrar_bgr(self, frame_bgr) -> None:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        imagen = ctk.CTkImage(light_image=pil, dark_image=pil, size=(ANCHO_VIDEO, ALTO_VIDEO))
        self._img_ref = imagen
        self.lbl_video.configure(image=imagen)

    def _salir_si_no_escribe(self, _evento=None) -> None:
        widget = self.focus_get()
        if widget is not None and widget is self.ent_etiqueta:
            return
        clase = "" if widget is None else widget.winfo_class()
        if clase in {"Entry", "Text", "TEntry"}:
            return
        self._cerrar()

    def _cerrar(self) -> None:
        self._vivo = False
        if self._pipeline is not None:
            self._pipeline.cerrar()
            self._pipeline = None
        self.destroy()


# Alias por si algún script de la fase 1 importaba el nombre anterior.
VentanaInnova = VentanaMamatlatolli


def ejecutar_app(*, modo_demo: bool = False, indice_camara: int = 0) -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    ventana = VentanaMamatlatolli(modo_demo=modo_demo, indice_camara=indice_camara)
    ventana.mainloop()
