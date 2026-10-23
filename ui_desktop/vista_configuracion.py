"""Pantalla Configuración: apariencia, ubicación de datos y respaldos."""

from __future__ import annotations

import os
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.database import respaldar
from core.errores import ErrorDominio
from core.version import VERSION

from . import tema
from .dialogos_base import DialogoFusion, DialogoImportarBase

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
                      text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO
                      ).pack(side="left", padx=8)
        fila_base = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        fila_base.pack(anchor="w", pady=(0, 14))
        ctk.CTkButton(fila_base, text="Exportar base…", command=self.exportar_base,
                      fg_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_ACENTO_HOVER
                      ).pack(side="left")
        ctk.CTkButton(fila_base, text="Importar base…", command=self.importar_base,
                      fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
                      text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO
                      ).pack(side="left", padx=8)
        self._boton_deshacer = ctk.CTkButton(
            fila_base, text="Deshacer importación", command=self.deshacer_importacion,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_PELIGRO,
            text_color=tema.COLOR_PELIGRO, hover_color=tema.COLOR_NAV_ACTIVO)
        if app.servicio.hay_importacion_por_deshacer:
            self._boton_deshacer.pack(side="left")
        self._mensaje = ctk.CTkLabel(self.contenedor, text="", anchor="w", justify="left",
                                     text_color=tema.COLOR_TEXTO_SUAVE, wraplength=640)
        self._mensaje.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            self.contenedor, text_color=tema.COLOR_TEXTO_SUAVE, anchor="w", justify="left",
            text="Se crea un respaldo automático al cerrar la aplicación (se conservan los 10 más recientes).",
        ).pack(fill="x")

        self._seccion("Acerca de")
        ctk.CTkLabel(self.contenedor, text=f"Participaciones  ·  versión {VERSION}", anchor="w"
                     ).pack(fill="x")
        ctk.CTkLabel(self.contenedor, text="Gestor local de participaciones por semestre, materia y grupo.",
                     anchor="w", text_color=tema.COLOR_TEXTO_SUAVE).pack(fill="x")

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

    # ---- exportar e importar la base (R19) ----------------------------------
    def exportar_base(self) -> None:
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Guardar copia de la base", defaultextension=".db",
            initialfile=f"participaciones_export_{datetime.now():%Y%m%d_%H%M%S}.db",
            filetypes=[("Base de datos", "*.db")],
        )
        if not ruta:
            return
        try:
            destino = self._app.servicio.exportar_base(ruta)
        except ErrorDominio as error:
            messagebox.showerror("No se pudo exportar", str(error), parent=self)
            return
        self._mensaje.configure(text=f"Base exportada en:\n{destino}")

    def importar_base(self) -> None:
        servicio = self._app.servicio
        ruta = filedialog.askopenfilename(
            parent=self, title="Selecciona la base a importar",
            filetypes=[("Base de datos", "*.db"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        try:
            archivo = servicio.resumen_base_archivo(ruta)
        except ErrorDominio as error:
            messagebox.showerror("No se pudo importar", str(error), parent=self)
            return
        modo = DialogoImportarBase(self, os.path.basename(ruta), servicio.resumen_base_local(), archivo).mostrar()
        if modo == "fusionar":
            self._fusionar(ruta)
            return
        if modo != "reemplazar":
            return
        try:
            servicio.reemplazar_base(ruta, self._app.carpeta_respaldos)
        except ErrorDominio as error:
            messagebox.showerror("No se pudo importar", str(error), parent=self)
            return
        self._boton_deshacer.pack(side="left")
        self._mensaje.configure(
            text="Base reemplazada. El respaldo de lo anterior se guardó; puedes deshacer la importación.")

    def _fusionar(self, ruta: str) -> None:
        servicio = self._app.servicio
        try:
            opciones = DialogoFusion(
                self, os.path.basename(ruta), lambda unir: servicio.previsualizar_fusion(ruta, unir)
            ).mostrar()
        except ErrorDominio as error:
            messagebox.showerror("No se pudo importar", str(error), parent=self)
            return
        if not opciones:
            return
        try:
            resultado = servicio.fusionar_base(
                ruta, self._app.carpeta_respaldos, opciones["unir"], opciones["usar_importado"],
                opciones["mantener_ambas"],
            )
        except ErrorDominio as error:
            messagebox.showerror("No se pudo importar", str(error), parent=self)
            return
        partes = ", ".join(f"{n} {nombre}" for nombre, n in resultado.aplicados.items()) or "nada nuevo"
        self._boton_deshacer.pack(side="left")
        self._mensaje.configure(text=f"Base fusionada: {partes}. Puedes deshacer la importación.")

    def deshacer_importacion(self) -> None:
        try:
            self._app.servicio.deshacer_importacion()
        except ErrorDominio as error:
            messagebox.showerror("No se pudo deshacer", str(error), parent=self)
            return
        self._boton_deshacer.pack_forget()
        self._mensaje.configure(text="Importación deshecha: la base volvió a como estaba.")
