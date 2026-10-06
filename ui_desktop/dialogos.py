"""Diálogos modales reutilizables."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from core.errores import ErrorDominio
from core.models import Curso, ListaInscripcion, VistaPreviaImportacion

from . import tema
from .icono import aplicar_icono


class Dialogo(ctk.CTkToplevel):
    """Ventana modal centrada sobre su ventana madre. `mostrar()` devuelve `resultado`."""

    def __init__(self, master, titulo: str, ancho: int = 440) -> None:
        super().__init__(master)
        self._ancho = ancho
        self.title(titulo)
        aplicar_icono(self)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.resultado = None
        self.protocol("WM_DELETE_WINDOW", self.cancelar)
        self.bind("<Escape>", lambda _e: self.cancelar())
        self.cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        self.cuerpo.pack(fill="both", expand=True, padx=22, pady=20)

    def cerrar(self, resultado=None) -> None:
        self.resultado = resultado
        self.grab_release()
        self.destroy()

    def cancelar(self) -> None:
        self.cerrar(None)

    def mostrar(self):
        self.update_idletasks()
        madre = self.master.winfo_toplevel()
        alto = self.winfo_reqheight()
        x = madre.winfo_rootx() + (madre.winfo_width() - self._ancho) // 2
        y = madre.winfo_rooty() + (madre.winfo_height() - alto) // 3
        self.geometry(f"{self._ancho}x{alto}+{max(x, 0)}+{max(y, 0)}")
        self.after(80, self._tomar_foco)
        self.wait_window(self)
        return self.resultado

    def _tomar_foco(self) -> None:
        if self.winfo_exists():
            self.grab_set()
            self.focus_force()
            self.al_mostrar()

    def al_mostrar(self) -> None:
        """Gancho para dar foco a un campo; lo sobrescriben las subclases."""

    def botones(self, texto_ok: str, comando, peligro: bool = False) -> ctk.CTkButton:
        fila = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        fila.pack(fill="x", pady=(18, 0))
        ctk.CTkButton(
            fila, text="Cancelar", width=100, fg_color="transparent", border_width=1,
            border_color=tema.COLOR_BORDE, text_color=("gray20", "gray90"),
            hover_color=tema.COLOR_NAV_ACTIVO, command=self.cancelar,
        ).pack(side="right", padx=(8, 0))
        boton = ctk.CTkButton(
            fila, text=texto_ok, width=110, command=comando,
            fg_color=tema.COLOR_PELIGRO if peligro else tema.COLOR_ACENTO,
            hover_color=tema.COLOR_PELIGRO_HOVER if peligro else tema.COLOR_ACENTO_HOVER,
        )
        boton.pack(side="right")
        return boton


class DialogoCurso(Dialogo):
    """Crear o editar un curso. `guardar(datos)` puede lanzar ErrorDominio."""

    def __init__(self, master, guardar: Callable[[dict], Curso], curso: Curso | None = None) -> None:
        super().__init__(master, "Editar curso" if curso else "Crear curso")
        self._guardar = guardar
        ctk.CTkLabel(
            self.cuerpo, text="Editar curso" if curso else "Nuevo curso",
            font=tema.fuente(18, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        self._campos: dict[str, ctk.CTkEntry] = {}
        for clave, etiqueta, ejemplo in (
            ("materia", "Materia", "Ej. Diseño y Análisis de Algoritmos"),
            ("grupo", "Grupo", "Ej. 1510"),
            ("ciclo", "Semestre / ciclo escolar", "Ej. 2027-I"),
            ("carrera", "Carrera (opcional)", "Ej. Ingeniería en Computación"),
        ):
            ctk.CTkLabel(self.cuerpo, text=etiqueta, anchor="w", font=tema.fuente(12),
                         text_color=tema.COLOR_TEXTO_SUAVE).pack(fill="x", pady=(8, 2))
            entrada = ctk.CTkEntry(self.cuerpo, placeholder_text=ejemplo, height=34)
            entrada.pack(fill="x")
            entrada.bind("<Return>", lambda _e: self._aceptar())
            self._campos[clave] = entrada
            if curso:
                entrada.insert(0, getattr(curso, clave))

        self._error = ctk.CTkLabel(self.cuerpo, text="", text_color=tema.COLOR_PELIGRO,
                                   wraplength=390, justify="left", anchor="w")
        self._error.pack(fill="x", pady=(10, 0))
        self.botones("Guardar", self._aceptar)

    def al_mostrar(self) -> None:
        self._campos["materia"].focus_set()

    def _aceptar(self) -> None:
        datos = {k: e.get() for k, e in self._campos.items()}
        try:
            curso = self._guardar(datos)
        except ErrorDominio as error:
            self._error.configure(text=str(error))
            return
        self.cerrar(curso)


class DialogoEliminarCurso(Dialogo):
    """Confirmación de eliminación definitiva; exige escribir ELIMINAR si hay datos."""

    PALABRA = "ELIMINAR"

    def __init__(self, master, curso: Curso, alumnos: int, participaciones: int) -> None:
        super().__init__(master, "Eliminar curso")
        self._exige_palabra = participaciones > 0
        ctk.CTkLabel(self.cuerpo, text="Eliminar curso", font=tema.fuente(18, "bold"),
                     text_color=tema.COLOR_PELIGRO).pack(anchor="w")
        ctk.CTkLabel(
            self.cuerpo, text=curso.titulo, wraplength=390, justify="left", anchor="w",
            font=tema.fuente(13, "bold"),
        ).pack(fill="x", pady=(10, 4))
        ctk.CTkLabel(
            self.cuerpo, wraplength=390, justify="left", anchor="w",
            text=(f"Se eliminarán {alumnos} inscripciones y {participaciones} participaciones "
                  "de este curso. Esta acción no se puede deshacer.\n\n"
                  "Los alumnos se conservan en el sistema. Si solo quieres ocultarlo, "
                  "usa Archivar."),
        ).pack(fill="x")
        self._entrada = None
        if self._exige_palabra:
            ctk.CTkLabel(self.cuerpo, text=f"Escribe {self.PALABRA} para confirmar:",
                         anchor="w", font=tema.fuente(12),
                         text_color=tema.COLOR_TEXTO_SUAVE).pack(fill="x", pady=(14, 2))
            self._entrada = ctk.CTkEntry(self.cuerpo, height=34)
            self._entrada.pack(fill="x")
            self._entrada.bind("<KeyRelease>", lambda _e: self._revisar())
        self._ok = self.botones("Eliminar", lambda: self.cerrar(True), peligro=True)
        self._revisar()

    def al_mostrar(self) -> None:
        if self._entrada:
            self._entrada.focus_set()

    def _revisar(self) -> None:
        habilitado = (not self._exige_palabra) or (
            self._entrada.get().strip().upper() == self.PALABRA
        )
        self._ok.configure(state="normal" if habilitado else "disabled")


class DialogoImportacion(Dialogo):
    """Resumen previo a importar; permite confirmar vínculos con oyentes sin cuenta.

    Devuelve un dict {num_cuenta: id_oyente} (puede ir vacío) o None si se cancela.
    """

    def __init__(self, master, lista: ListaInscripcion, vista: VistaPreviaImportacion) -> None:
        super().__init__(master, "Importar lista", ancho=560)
        self._vista = vista
        self._marcas: list[tuple[ctk.CTkCheckBox, str, int]] = []

        ctk.CTkLabel(self.cuerpo, text="Importar lista de inscripción",
                     font=tema.fuente(18, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            self.cuerpo, text=f"{lista.materia}\nGrupo {lista.grupo} · {lista.ciclo}",
            justify="left", anchor="w", font=tema.fuente(13, "bold"), wraplength=500,
        ).pack(fill="x", pady=(10, 6))

        accion = "Se agregarán alumnos al curso existente." if vista.curso_existente \
            else "Se creará un curso nuevo."
        ctk.CTkLabel(
            self.cuerpo, justify="left", anchor="w", wraplength=500,
            text=(f"{accion}\n• {len(lista.alumnos)} alumnos en la lista\n"
                  f"• {vista.alumnos_nuevos} alumnos nuevos en el sistema\n"
                  f"• {vista.alumnos_existentes} ya existían (se reutilizan)"),
        ).pack(fill="x")

        if vista.coincidencias_oyentes:
            ctk.CTkLabel(
                self.cuerpo, anchor="w", justify="left", wraplength=500,
                font=tema.fuente(13, "bold"), text_color=tema.COLOR_ACENTO,
                text="Estos alumnos coinciden por nombre con oyentes sin número de cuenta. "
                     "Marca los que sean la misma persona para conservar su historial:",
            ).pack(fill="x", pady=(14, 4))
            zona = ctk.CTkScrollableFrame(self.cuerpo, height=min(150, 36 * len(vista.coincidencias_oyentes)))
            zona.pack(fill="x")
            for c in vista.coincidencias_oyentes:
                marca = ctk.CTkCheckBox(
                    zona, text=f"{c.fila.nombre_completo}  ·  cuenta {c.fila.num_cuenta}",
                    checkbox_width=20, checkbox_height=20,
                )
                marca.pack(anchor="w", pady=3)
                self._marcas.append((marca, c.fila.num_cuenta, c.oyente.id))

        self.botones("Importar", self._aceptar)

    def _aceptar(self) -> None:
        vinculos: dict[str, int] = {}
        for marca, cuenta, oyente_id in self._marcas:
            if marca.get() and cuenta not in vinculos and oyente_id not in vinculos.values():
                vinculos[cuenta] = oyente_id
        self.cerrar(vinculos)
