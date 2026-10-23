"""Pantalla Historial de un alumno: resumen, selector de curso y participaciones editables."""

from __future__ import annotations

from tkinter import messagebox, ttk

import customtkinter as ctk

from core.errores import ErrorDominio
from core.models import Alumno, Curso, LineaExamen, LineaHistorial, TipoInscripcion

from . import tema
from .dialogos_historial import DialogoCalificacion, DialogoEditarAlumno, DialogoParticipacion
from .formato import formatear_decimas, formatear_fecha, titulo_legible
from .tabla import ESTILO, configurar_estilo

COLUMNAS = (
    ("fecha", "Fecha", 110, "center"),
    ("decimas", "Décimas", 90, "e"),
    ("efecto", "Efecto real", 100, "e"),
    ("total", "Total", 90, "e"),
    ("nota", "Nota", 360, "w"),
)
TAREAS = "tareas"  # iid de la fila de tareas en la tabla de calificaciones
PROYECTO = "proyecto"  # iid de la fila del proyecto final
COLUMNAS_EXAMENES = (
    ("examen", "Concepto", 360, "w"),
    ("puntos", "Calificación", 120, "e"),
    ("fecha", "Fecha", 110, "center"),
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
        self._lineas_examen: dict[int, LineaExamen] = {}
        self._tareas = None  # CalificacionTareas del alumno en el curso, o None
        self._proyecto = None  # CalificacionProyecto del alumno en el curso, o None
        self._colores = configurar_estilo()

        self._construir_encabezado()
        self._construir_tarjetas()
        self._construir_selector()
        self._construir_tabla()
        self._construir_acciones()
        self._construir_examenes()
        # Lo de abajo se empaqueta primero (de abajo hacia arriba) y la tabla de participaciones
        # al final: así, en una ventana baja, es la tabla la que cede espacio y no los botones.
        self._fila_examenes.pack(side="bottom", fill="x", padx=24, pady=(0, 18))
        self._marco_examenes.pack(side="bottom", fill="x", padx=24, pady=(0, 8))
        self._cab_examenes.pack(side="bottom", fill="x", padx=24, pady=(4, 6))
        self._fila_acciones.pack(side="bottom", fill="x", padx=24, pady=(0, 10))
        self._marco_tabla.pack(fill="both", expand=True, padx=24, pady=(0, 8))
        self.recargar()

    # ====================== construcción ======================
    def _construir_encabezado(self) -> None:
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.pack(fill="x", padx=24, pady=(16, 0))
        ctk.CTkButton(
            cab, text="←  Curso", width=90, height=28, fg_color="transparent",
            text_color=tema.COLOR_ACENTO_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
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
            text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
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
            text_color=tema.COLOR_TEXTO,
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
        self._marco_tabla = marco
        self._tabla = ttk.Treeview(
            marco, columns=[c[0] for c in COLUMNAS], show="headings", style=ESTILO,
            selectmode="browse", height=5,  # pide poco alto para que quepa la sección Exámenes
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
        self._fila_acciones = fila
        ctk.CTkButton(
            fila, text="＋  Agregar participación", height=36, command=self.agregar_participacion,
            fg_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_ACENTO_HOVER,
        ).pack(side="left")
        self._boton_editar = ctk.CTkButton(
            fila, text="✎  Editar", width=100, height=36, command=self.editar_participacion,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
        )
        self._boton_editar.pack(side="left", padx=8)
        self._boton_borrar = ctk.CTkButton(
            fila, text="🗑  Eliminar", width=110, height=36, command=self.eliminar_participacion,
            fg_color=tema.COLOR_PELIGRO, hover_color=tema.COLOR_PELIGRO_HOVER,
        )
        self._boton_borrar.pack(side="left")
        self._actualizar_botones()

    def _construir_examenes(self) -> None:
        """Sección «Exámenes»: una fila por examen del curso, con su calificación."""
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        self._cab_examenes = cabecera
        self._titulo_calificaciones = ctk.CTkLabel(
            cabecera, text="Exámenes, tareas y proyecto", font=tema.fuente(15, "bold"))
        self._titulo_calificaciones.pack(side="left")
        self._aviso_examenes = ctk.CTkLabel(cabecera, text="", text_color=tema.COLOR_TEXTO_SUAVE)
        self._aviso_examenes.pack(side="left", padx=12)

        marco = ctk.CTkFrame(self, corner_radius=12, fg_color=tema.COLOR_TARJETA,
                             border_width=1, border_color=tema.COLOR_BORDE)
        self._marco_examenes = marco
        self._tabla_examenes = ttk.Treeview(
            marco, columns=[c[0] for c in COLUMNAS_EXAMENES], show="headings", style=ESTILO,
            selectmode="browse", height=3,
        )
        for clave, titulo, ancho, alineacion in COLUMNAS_EXAMENES:
            self._tabla_examenes.heading(clave, text=titulo, anchor=alineacion)
            self._tabla_examenes.column(clave, width=ancho, anchor=alineacion,
                                        stretch=(clave == "examen"), minwidth=60)
        barra = ctk.CTkScrollbar(marco, command=self._tabla_examenes.yview, height=40)  # alto mínimo pedido
        self._tabla_examenes.configure(yscrollcommand=barra.set)
        self._tabla_examenes.pack(side="left", fill="x", expand=True, padx=(8, 0), pady=8)
        barra.pack(side="right", fill="y", padx=(0, 4), pady=8)
        self._tabla_examenes.tag_configure("sin", foreground=self._colores["suave"])
        self._tabla_examenes.bind("<<TreeviewSelect>>", lambda _e: self._actualizar_botones_examenes())
        self._tabla_examenes.bind("<Double-1>", lambda _e: self.editar_calificacion())
        self._tabla_examenes.bind("<Delete>", lambda _e: self.eliminar_calificacion())

        fila = ctk.CTkFrame(self, fg_color="transparent")
        self._fila_examenes = fila
        self._boton_calificar = ctk.CTkButton(
            fila, text="✎  Calificar / editar", width=160, height=36, command=self.editar_calificacion,
            fg_color=tema.COLOR_EXAMEN, hover_color=tema.COLOR_EXAMEN_HOVER,
        )
        self._boton_calificar.pack(side="left")
        self._boton_quitar = ctk.CTkButton(
            fila, text="🗑  Quitar calificación", width=170, height=36, command=self.eliminar_calificacion,
            fg_color=tema.COLOR_PELIGRO, hover_color=tema.COLOR_PELIGRO_HOVER,
        )
        self._boton_quitar.pack(side="left", padx=8)
        self._actualizar_botones_examenes()

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
        self._recargar_examenes()

    def _recargar_examenes(self, resaltar: int | str | None = None) -> None:
        """Tabla de calificaciones: «Tareas», «Proyecto final» y luego un renglón por examen."""
        lineas = self._servicio.historial_examenes(self._curso_id, self._alumno_id)
        self._lineas_examen = {l.examen.id: l for l in lineas}
        self._tareas = self._servicio.tareas_de(self._curso_id, self._alumno_id)
        self._proyecto = self._servicio.proyecto_de(self._curso_id, self._alumno_id)
        self._tabla_examenes.delete(*self._tabla_examenes.get_children())
        self._tabla_examenes.insert(
            "", "end", iid=TAREAS, tags=() if self._tareas else ("sin",),
            values=("Tareas", formatear_decimas(self._tareas.puntos if self._tareas else 0.0),
                    formatear_fecha(self._tareas.fecha) if self._tareas else "—"),
        )
        self._tabla_examenes.insert(
            "", "end", iid=PROYECTO, tags=() if self._proyecto else ("sin",),
            values=(self._nombre_proyecto(), formatear_decimas(self._proyecto.puntos if self._proyecto else 0.0),
                    formatear_fecha(self._proyecto.fecha) if self._proyecto else "—"),
        )
        for l in lineas:
            c = l.calificacion
            self._tabla_examenes.insert(
                "", "end", iid=str(l.examen.id), tags=() if c else ("sin",),
                values=(l.examen.nombre, formatear_decimas(l.puntos),
                        formatear_fecha(c.fecha) if c else "—"),
            )
        self._aviso_examenes.configure(
            text="" if lineas else "Este curso no tiene exámenes. Créalos desde la pantalla del curso."
        )
        if resaltar is not None and self._tabla_examenes.exists(str(resaltar)):
            self._tabla_examenes.selection_set(str(resaltar))
            self._tabla_examenes.see(str(resaltar))
        self._actualizar_botones_examenes()

    def _nombre_proyecto(self) -> str:
        """«Proyecto final», con «· Equipo N» si el alumno tiene equipo."""
        equipo = self._servicio.equipo_de(self._curso_id, self._alumno_id)
        return "Proyecto final" + (f" · Equipo {equipo}" if equipo is not None else "")

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

    # ====================== exámenes ======================
    def _fila_calificacion(self):
        """(iid, nombre, calificación o None) del renglón elegido; None si no hay selección.

        El iid es `TAREAS` o `PROYECTO` para esas filas, o el id del examen (como texto).
        """
        seleccion = self._tabla_examenes.selection()
        if not seleccion:
            return None
        iid = seleccion[0]
        if iid == TAREAS:
            return iid, "Tareas", self._tareas
        if iid == PROYECTO:
            return iid, "Proyecto final", self._proyecto
        linea = self._lineas_examen.get(int(iid))
        return (iid, linea.examen.nombre, linea.calificacion) if linea else None

    def _actualizar_botones_examenes(self) -> None:
        fila = self._fila_calificacion()
        self._boton_calificar.configure(state="normal" if fila else "disabled")
        self._boton_quitar.configure(state="normal" if fila and fila[2] else "disabled")

    def editar_calificacion(self) -> None:
        fila = self._fila_calificacion()
        if fila is None:
            return
        iid, nombre, actual = fila

        def guardar(d: dict):
            if iid == TAREAS:
                return self._servicio.establecer_tareas(
                    self._curso_id, self._alumno_id, d["puntos"], d["fecha"]
                )
            if iid == PROYECTO:
                return self._servicio.establecer_proyecto(
                    self._curso_id, self._alumno_id, d["puntos"], d["fecha"]
                )
            return self._servicio.establecer_calificacion(
                self._curso_id, int(iid), self._alumno_id, d["puntos"], d["fecha"]
            )

        if DialogoCalificacion(self, nombre, guardar, actual).mostrar():
            self._recargar_examenes(resaltar=iid)

    def eliminar_calificacion(self) -> None:
        fila = self._fila_calificacion()
        if fila is None or fila[2] is None:
            return
        iid, nombre, actual = fila
        vuelve = {TAREAS: "Las tareas volverán", PROYECTO: "El proyecto volverá"}.get(iid, "El examen volverá")
        if not messagebox.askyesno(
            "Quitar calificación",
            f"¿Quitar la calificación de {formatear_decimas(actual.puntos)} en «{nombre}»?"
            f"\n\n{vuelve} a valer 0.",
            parent=self,
        ):
            return
        try:
            if iid == TAREAS:
                self._servicio.eliminar_tareas(self._curso_id, self._alumno_id)
            elif iid == PROYECTO:
                self._servicio.eliminar_proyecto(self._curso_id, self._alumno_id)
            else:
                self._servicio.eliminar_calificacion(int(iid), self._alumno_id)
        except ErrorDominio as error:
            messagebox.showerror("No se pudo quitar", str(error), parent=self)
        self._recargar_examenes(resaltar=iid)

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
