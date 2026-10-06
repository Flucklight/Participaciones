"""Pantalla Configuración: apariencia, ubicación de datos y respaldos."""

from __future__ import annotations

import os
from tkinter import messagebox

import customtkinter as ctk

from core.database import respaldar

from . import tema

_MODOS = {"Sistema": "system", "Claro": "light", "Oscuro": "dark"}


class VistaConfiguracion(ctk.CTkFrame):
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self._app = app
        ctk.CTkLabel(self, text="Configuración", font=tema.fuente(26, "bold"), anchor="w").pack(
            fill="x", padx=24, pady=(22, 12)
        )

        self._seccion("Apariencia")
        modo = ctk.CTkSegmentedButton(
            self.contenedor, values=list(_MODOS), command=self._cambiar_modo
        )
        modo.set("Sistema")
        modo.pack(anchor="w", pady=(0, 6))

        self._seccion("Datos")
        ctk.CTkLabel(self.contenedor, text=f"Base de datos:\n{app.ruta_db}", justify="left",
                     anchor="w", text_color=tema.COLOR_TEXTO_SUAVE, wraplength=640).pack(fill="x")
        ctk.CTkLabel(self.contenedor, text=f"Respaldos:\n{app.carpeta_respaldos}", justify="left",
                     anchor="w", text_color=tema.COLOR_TEXTO_SUAVE, wraplength=640
                     ).pack(fill="x", pady=(8, 0))
        fila = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        fila.pack(anchor="w", pady=14)
        ctk.CTkButton(fila, text="Crear respaldo ahora", command=self._respaldar,
                      fg_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_ACENTO_HOVER
                      ).pack(side="left")
        ctk.CTkButton(fila, text="Abrir carpeta de datos", command=self._abrir_carpeta,
                      fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
                      text_color=("gray20", "gray90"), hover_color=tema.COLOR_NAV_ACTIVO
                      ).pack(side="left", padx=8)
        ctk.CTkLabel(
            self.contenedor, text_color=tema.COLOR_TEXTO_SUAVE, anchor="w", justify="left",
            text="Se crea un respaldo automático al cerrar la aplicación (se conservan los 10 más recientes).",
        ).pack(fill="x")

    @property
    def contenedor(self) -> ctk.CTkFrame:
        return self._contenedor

    def _seccion(self, titulo: str) -> None:
        marco = ctk.CTkFrame(self, corner_radius=12, fg_color=tema.COLOR_TARJETA,
                             border_width=1, border_color=tema.COLOR_BORDE)
        marco.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(marco, text=titulo, font=tema.fuente(15, "bold"), anchor="w").pack(
            fill="x", padx=18, pady=(14, 8)
        )
        self._contenedor = ctk.CTkFrame(marco, fg_color="transparent")
        self._contenedor.pack(fill="x", padx=18, pady=(0, 14))

    def _cambiar_modo(self, etiqueta: str) -> None:
        ctk.set_appearance_mode(_MODOS[etiqueta])

    def _respaldar(self) -> None:
        destino = respaldar(self._app.conexion, self._app.carpeta_respaldos)
        messagebox.showinfo("Respaldo creado", f"Se guardó en:\n{destino}", parent=self)

    def _abrir_carpeta(self) -> None:
        self._app.carpeta_respaldos.parent.mkdir(parents=True, exist_ok=True)
        os.startfile(self._app.carpeta_respaldos.parent)
