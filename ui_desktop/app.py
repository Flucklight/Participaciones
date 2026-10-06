"""Ventana principal: panel lateral izquierdo y área central."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from core.database import RUTA_POR_DEFECTO, conectar, respaldar
from core.repository import Repositorio
from core.services import ServicioParticipaciones

from . import tema
from .icono import aplicar_icono
from .vista_configuracion import VistaConfiguracion
from .vista_curso import VistaCurso
from .vista_historial import VistaHistorial
from .vista_cursos import VistaCursos

SECCIONES = (("cursos", "📚   Cursos"), ("configuracion", "⚙   Configuración"))


class App(ctk.CTk):
    def __init__(self, ruta_db: str | Path = RUTA_POR_DEFECTO) -> None:
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.ruta_db = Path(ruta_db)
        self.carpeta_respaldos = self.ruta_db.parent / "backups"
        self.conexion = conectar(self.ruta_db)
        self.servicio = ServicioParticipaciones(Repositorio(self.conexion))

        self.title("Participaciones")
        aplicar_icono(self)
        self.geometry("1150x720")
        self.minsize(900, 560)
        self.configure(fg_color=tema.COLOR_FONDO)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

        self._botones: dict[str, ctk.CTkButton] = {}
        self._vista: ctk.CTkFrame | None = None
        self._construir_panel()
        self._area = ctk.CTkFrame(self, fg_color="transparent")
        self._area.pack(side="left", fill="both", expand=True)
        self.mostrar("cursos")

    def _construir_panel(self) -> None:
        panel = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color=tema.COLOR_PANEL)
        panel.pack(side="left", fill="y")
        panel.pack_propagate(False)
        ctk.CTkLabel(panel, text="Participaciones", font=tema.fuente(18, "bold"),
                     anchor="w").pack(fill="x", padx=20, pady=(26, 22))
        for clave, etiqueta in SECCIONES:
            boton = ctk.CTkButton(
                panel, text=etiqueta, anchor="w", height=40, corner_radius=8,
                font=tema.fuente(14), fg_color="transparent", text_color=("gray15", "gray90"),
                hover_color=tema.COLOR_NAV_ACTIVO, command=lambda c=clave: self.mostrar(c),
            )
            boton.pack(fill="x", padx=12, pady=2)
            self._botones[clave] = boton

    def mostrar(self, seccion: str, **kwargs) -> None:
        """Muestra una sección en el área central y marca su botón del panel."""
        if self._vista is not None:
            self._vista.destroy()
        constructores = {
            "cursos": lambda: VistaCursos(self._area, self),
            "configuracion": lambda: VistaConfiguracion(self._area, self),
            "curso": lambda: VistaCurso(self._area, self, kwargs["curso_id"]),
            "historial": lambda: VistaHistorial(
                self._area, self, kwargs["curso_id"], kwargs["alumno_id"]
            ),
        }
        self._vista = constructores[seccion]()
        self._vista.pack(fill="both", expand=True)
        activa = "cursos" if seccion in ("curso", "historial") else seccion
        for clave, boton in self._botones.items():
            boton.configure(fg_color=tema.COLOR_NAV_ACTIVO if clave == activa else "transparent")

    def abrir_curso(self, curso_id: int) -> None:
        self.mostrar("curso", curso_id=curso_id)

    def abrir_historial(self, curso_id: int, alumno_id: int) -> None:
        self.mostrar("historial", curso_id=curso_id, alumno_id=alumno_id)

    def _cerrar(self) -> None:
        try:
            respaldar(self.conexion, self.carpeta_respaldos)
        finally:
            self.conexion.close()
            self.destroy()
