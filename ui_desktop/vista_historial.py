"""Pantalla Historial de un alumno: resumen, selector de curso y participaciones editables."""

from __future__ import annotations

from tkinter import messagebox, ttk

import customtkinter as ctk

from core.errores import ErrorDominio
from core.models import Alumno, Curso, LineaHistorial, TipoInscripcion

from . import tema
from .dialogos_historial import DialogoEditarAlumno, DialogoParticipacion
from .formato import formatear_decimas, formatear_fecha, titulo_legible
from .tabla import ESTILO, configurar_estilo

COLUMNAS = (
    ("fecha", "Fecha", 110, "center"),
    ("decimas", "Décimas", 90, "e"),
    ("efecto", "Efecto real", 100, "e"),
    ("total", "Total", 90, "e"),
    ("nota", "Nota", 360, "w"),
)


class VistaHistorial(ctk.CTkFrame):
    def __init__(self, master, app, curso_id: int, alumno_id: int) -> None:
        super().__init__(master, fg_color="transparent")
        self._app = app
        self._servicio = app.servicio
        self._alumno_id = alumno_id
        self._cursos: list[Curso] = self._servicio.cursos_de_alumno(alumno_id)
        self._curso_id = curso_id if any(c.id == curso_id for c in self._cursos) else self._cursos[0].id
        self._lineas: dict[int, LineaHistorial] = {}
        self._colores = configurar_estilo()

        self._construir_encabezado()
        self._construir_tarjetas()
        self._construir_selector()
        self._construir_tabla()
        self._construir_acciones()
        self.recargar()

    # ====================== construcción ======================
    def _construir_encabezado(self) -> None:
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.pack(fill="x", padx=24, pady=(16, 0))
        ctk.CTkButton(
            cab, text="←  Curso", width=90, height=28, fg_color="transparent",
            text_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_NAV_ACTIVO,
            command=lambda: self._app.abrir_curso(self._curso_id),
        ).pack(anchor="w")
        fila = ctk.CTkFrame(cab, fg_color="transparent")
        fila.pack(fill="x", pady=(2, 0))
        bloque = ctk.CTkFrame(fila, fg_color="transparent")
        bloque.pack(side="left")
        self._titulo = ctk.CTkLabel(bloque, text="", anchor="w", font=tema.fuente(22, "bold"))
        self._titulo.pack(anchor="w")
        self._subtitulo = ctk.CTkLabel(bloque, text="", anchor="w", text_color=tema.COLOR_TEXTO_SUAVE)
        self._subtitulo.pack(anchor="w")

        acciones = ctk.CTkFrame(fila, fg_color="transparent")
        acciones.pack(side="right", anchor="s")
        self._boton_regular = ctk.CTkButton(
            acciones, text="Convertir en regular", height=34, command=self.convertir_en_regular,
            fg_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_ACENTO_HOVER,
        )
        ctk.CTkButton(
            acciones, text="✎  Editar alumno", height=34, command=self.editar_alumno,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
            text_color=("gray20", "gray90"), hover_color=tema.COLOR_NAV_ACTIVO,
        ).pack(side="right")

    def _construir_tarjetas(self) -> None:
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=24, pady=(16, 0))
        self._valores: dict[str, ctk.CTkLabel] = {}
        for clave, etiqueta in (("total", "Total de décimas"), ("registros", "Participaciones"),
                                ("ultima", "Última participación")):
            tarjeta = ctk.CTkFrame(fila, corner_radius=12, fg_color=tema.COLOR_TARJETA,
                                   border_width=1, border_color=tema.COLOR_BORDE)
            tarjeta.pack(side="left", fill="x", expand=True, padx=(0, 12))
            ctk.CTkLabel(tarjeta, text=etiqueta, anchor="w", font=tema.fuente(12),
                         text_color=tema.COLOR_TEXTO_SUAVE).pack(fill="x", padx=16, pady=(10, 0))
            valor = ctk.CTkLabel(tarjeta, text="", anchor="w", font=tema.fuente(24, "bold"))
            valor.pack(fill="x", padx=16, pady=(0, 10))
            self._valores[clave] = valor

    def _construir_selector(self) -> None:
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=24, pady=(14, 6))
        ctk.CTkLabel(fila, text="Curso:", text_color=tema.COLOR_TEXTO_SUAVE).pack(side="left")
        self._etiquetas = {self._etiqueta(c): c.id for c in self._cursos}
        self._selector = ctk.CTkOptionMenu(
            fila, values=list(self._etiquetas), width=380, command=self._cambiar_curso,
            fg_color=tema.COLOR_TARJETA, button_color=tema.COLOR_BORDE,
            text_color=("gray10", "gray95"),
        )
        self._selector.set(next(e for e, i in self._etiquetas.items() if i == self._curso_id))
        self._selector.pack(side="left", padx=10)
        self._aviso = ctk.CTkLabel(fila, text="", text_color=tema.COLOR_TEXTO_SUAVE)
        self._aviso.pack(side="right")

    @staticmethod
    def _etiqueta(curso: Curso) -> str:
        archivado = "  (archivado)" if curso.archivado else ""
        return f"{titulo_legible(curso.materia)} · {curso.grupo} · {curso.ciclo}{archivado}"

    def _construir_tabla(self) -> None:
        marco = ctk.CTkFrame(self, corner_radius=12, fg_color=tema.COLOR_TARJETA,
                             border_width=1, border_color=tema.COLOR_BORDE)
        marco.pack(fill="both", expand=True, padx=24, pady=(0, 8))
        self._tabla = ttk.Treeview(
            marco, columns=[c[0] for c in COLUMNAS], show="headings", style=ESTILO,
            selectmode="browse",
        )
        for clave, titulo, ancho, alineacion in COLUMNAS:
            self._tabla.heading(clave, text=titulo, anchor=alineacion)
            self._tabla.column(clave, width=ancho, anchor=alineacion,
                               stretch=(clave == "nota"), minwidth=60)
        barra = ctk.CTkScrollbar(marco, command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=barra.set)
        self._tabla.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        barra.pack(side="right", fill="y", padx=(0, 4), pady=8)
        self._tabla.tag_configure("piso", foreground=self._colores["aviso"])
        self._tabla.tag_configure("reciente", background=self._colores["reciente"])
        self._tabla.bind("<<TreeviewSelect>>", lambda _e: self._actualizar_botones())
        self._tabla.bind("<Double-1>", lambda _e: self.editar_participacion())
        self._tabla.bind("<Delete>", lambda _e: self.eliminar_participacion())

    def _construir_acciones(self) -> None:
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=24, pady=(0, 18))
        ctk.CTkButton(
            fila, text="＋  Agregar participación", height=36, command=self.agregar_participacion,
            fg_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_ACENTO_HOVER,
        ).pack(side="left")
        self._boton_editar = ctk.CTkButton(
            fila, text="✎  Editar", width=100, height=36, command=self.editar_participacion,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
            text_color=("gray20", "gray90"), hover_color=tema.COLOR_NAV_ACTIVO,
        )
        self._boton_editar.pack(side="left", padx=8)
        self._boton_borrar = ctk.CTkButton(
            fila, text="🗑  Eliminar", width=110, height=36, command=self.eliminar_participacion,
            fg_color=tema.COLOR_PELIGRO, hover_color=tema.COLOR_PELIGRO_HOVER,
        )
        self._boton_borrar.pack(side="left")
        self._actualizar_botones()

    # ====================== datos ======================
    @property
    def alumno(self) -> Alumno:
        return self._servicio.obtener_alumno(self._alumno_id)

    def recargar(self, resaltar: int | None = None) -> None:
        alumno = self.alumno
        tipo = self._servicio.tipo_inscripcion(self._curso_id, self._alumno_id)
        self._titulo.configure(text=alumno.nombre_completo)
        etiqueta_tipo = "Oyente" if tipo == TipoInscripcion.OYENTE else "Regular"
        self._subtitulo.configure(
            text=f"Cuenta {alumno.num_cuenta or 'sin asignar'}  ·  {etiqueta_tipo}"
        )
        if tipo == TipoInscripcion.OYENTE:
            self._boton_regular.pack(side="right", padx=(0, 8))
        else:
            self._boton_regular.pack_forget()

        lineas = self._servicio.historial_detallado(self._curso_id, self._alumno_id)
        self._lineas = {l.participacion.id: l for l in lineas}
        self._tabla.delete(*self._tabla.get_children())
        for l in lineas:
            p = l.participacion
            self._tabla.insert(
                "", "end", iid=str(p.id), tags=("piso",) if l.toco_el_piso else (),
                values=(
                    formatear_fecha(p.fecha),
                    formatear_decimas(p.decimas, True),
                    formatear_decimas(l.aplicado, True) + ("  ⚑" if l.toco_el_piso else ""),
                    formatear_decimas(l.acumulado),
                    p.nota,
                ),
            )
        self._valores["total"].configure(text=formatear_decimas(lineas[0].acumulado) if lineas else "0")
        self._valores["registros"].configure(text=str(len(lineas)))
        self._valores["ultima"].configure(
            text=formatear_fecha(max(l.participacion.fecha for l in lineas)) if lineas else "—"
        )
        hay_piso = any(l.toco_el_piso for l in lineas)
        self._aviso.configure(text="⚑ = se aplicó el mínimo de 0" if hay_piso else "")
        if resaltar is not None and self._tabla.exists(str(resaltar)):
            self._tabla.selection_set(str(resaltar))
            self._tabla.see(str(resaltar))
        self._actualizar_botones()

    def _cambiar_curso(self, etiqueta: str) -> None:
        self._curso_id = self._etiquetas[etiqueta]
        self.recargar()

    def _seleccionada(self) -> int | None:
        seleccion = self._tabla.selection()
        return int(seleccion[0]) if seleccion else None

    def _actualizar_botones(self) -> None:
        estado = "normal" if self._seleccionada() is not None else "disabled"
        self._boton_editar.configure(state=estado)
        self._boton_borrar.configure(state=estado)

    # ====================== participaciones ======================
    def agregar_participacion(self) -> None:
        def guardar(d: dict):
            return self._servicio.agregar_participacion(
                self._curso_id, self._alumno_id, d["decimas"], d["fecha"], d["nota"]
            )

        creada = DialogoParticipacion(self, guardar).mostrar()
        if creada:
            self.recargar(resaltar=creada.id)

    def editar_participacion(self) -> None:
        participacion_id = self._seleccionada()
        if participacion_id is None:
            return
        actual = self._lineas[participacion_id].participacion

        def guardar(d: dict):
            return self._servicio.editar_participacion(
                participacion_id, d["decimas"], d["fecha"], d["nota"]
            )

        if DialogoParticipacion(self, guardar, actual).mostrar():
            self.recargar(resaltar=participacion_id)

    def eliminar_participacion(self) -> None:
        participacion_id = self._seleccionada()
        if participacion_id is None:
            return
        p = self._lineas[participacion_id].participacion
        if not messagebox.askyesno(
            "Eliminar participación",
            f"¿Eliminar la participación de {formatear_decimas(p.decimas, True)} décimas "
            f"del {formatear_fecha(p.fecha)}?\n\nEl total se recalculará.",
            parent=self,
        ):
            return
        try:
            self._servicio.deshacer(participacion_id)
        except ErrorDominio as error:
            messagebox.showerror("No se pudo eliminar", str(error), parent=self)
        self.recargar()

    # ====================== alumno ======================
    def editar_alumno(self) -> None:
        def guardar(nombre: str, cuenta: str) -> Alumno:
            return self._servicio.editar_alumno(self._alumno_id, nombre, cuenta)

        if DialogoEditarAlumno(self, self.alumno, guardar).mostrar():
            self.recargar()

    def convertir_en_regular(self) -> None:
        sin_cuenta = self.alumno.num_cuenta is None
        mensaje = ("Se conservará todo su historial.\n\nOjo: aún no tiene número de cuenta; "
                   "puedes asignarlo con «Editar alumno»." if sin_cuenta
                   else "Se conservará todo su historial.")
        if messagebox.askyesno("Convertir en regular", mensaje, parent=self):
            self._servicio.cambiar_tipo(self._curso_id, self._alumno_id, TipoInscripcion.REGULAR)
            self.recargar()
