"""Ventana de escritorio (CustomTkinter) para el prototipo INNOVA 2026."""

from __future__ import annotations

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
    SUBTITULO,
    TITULO_VENTANA,
)
from innova.overlay import frame_mensaje
from innova.pipeline import PipelineVision, crear_pipeline

_INTERVALO_MS = max(15, int(1000 / FPS_OBJETIVO))


class VentanaInnova(ctk.CTk):
    def __init__(self, *, modo_demo: bool = False, indice_camara: int = 0) -> None:
        super().__init__()
        self._modo_demo = modo_demo
        self._indice_camara = indice_camara
        self._pipeline: Optional[PipelineVision] = None
        self._vivo = True
        self._img_ref: Optional[ctk.CTkImage] = None
        self._error_camara = ""

        self.title(TITULO_VENTANA)
        self.geometry("1120x720")
        self.minsize(960, 640)
        self.configure(fg_color=COLOR_FONDO)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.bind_all("<Escape>", lambda _e: self._cerrar())
        self.bind_all("q", lambda _e: self._cerrar())
        self.bind_all("Q", lambda _e: self._cerrar())

        self._construir_layout()
        self._iniciar_pipeline()
        self.after(_INTERVALO_MS, self._tick)

    def _construir_layout(self) -> None:
        encabezado = ctk.CTkFrame(self, fg_color="transparent")
        encabezado.pack(fill="x", padx=24, pady=(18, 8))

        ctk.CTkLabel(
            encabezado,
            text="INNOVA 2026",
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
            text="Seña actual",
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

        self.lbl_mensaje = ctk.CTkLabel(
            lateral,
            text="Esperando cámara…",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO,
            wraplength=300,
            justify="left",
        )
        self.lbl_mensaje.pack(anchor="w", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            lateral,
            text="Transcripción reciente",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXTO_MUDO,
        ).pack(anchor="w", padx=20, pady=(8, 4))

        self.txt_transcripcion = ctk.CTkTextbox(
            lateral,
            height=220,
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
        self.btn_reintentar.pack(padx=20, pady=(4, 20), fill="x")

        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", padx=24, pady=(4, 14))
        ctk.CTkLabel(
            pie,
            text="Esc o Q para salir    ·    Fase 1: detección de manos (el modelo LSM se conecta en la fase 2)",
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
            self.btn_reintentar.configure(state="disabled")
        except CamaraNoDisponibleError as exc:
            self._error_camara = str(exc)
            self.btn_reintentar.configure(state="normal")
            self.lbl_sena.configure(text="—")
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
                    self.lbl_mensaje.configure(
                        text=procesado.resultado.mensaje or "",
                        text_color=COLOR_AVISO if procesado.manos else COLOR_TEXTO_MUDO,
                    )
                    n = len(procesado.manos)
                    self.lbl_estado.configure(
                        text=f"Manos: {n}   ·   {procesado.fuente}"
                    )
                    self._escribir_transcripcion(procesado.transcripcion)
        self.after(_INTERVALO_MS, self._tick)

    def _escribir_transcripcion(self, lineas: list[str]) -> None:
        texto = "\n".join(lineas) if lineas else "Aún no hay predicciones."
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

    def _cerrar(self) -> None:
        self._vivo = False
        if self._pipeline is not None:
            self._pipeline.cerrar()
            self._pipeline = None
        self.destroy()


def ejecutar_app(*, modo_demo: bool = False, indice_camara: int = 0) -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    ventana = VentanaInnova(modo_demo=modo_demo, indice_camara=indice_camara)
    ventana.mainloop()
