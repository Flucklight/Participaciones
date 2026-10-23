"""Pantalla Curso: registro rápido de décimas y tabla de alumnos."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from core.errores import ErrorDominio
from core.models import (
    Alumno,
    Calificacion,
    CalificacionTareas,
    EstadoRegistro,
    Examen,
    ResultadoCalificacion,
    ResultadoRegistro,
    ResultadoTareas,
    ResumenAlumno,
    TipoInscripcion,
)
from core.normalizacion import normalizar
from exporters.curso import exportar_curso, nombre_sugerido
from importers.calificaciones_plataforma import leer_calificaciones

from . import tema
from .dialogos_curso import DialogoAlumnoNuevo, DialogoElegirAlumno, DialogoExamen, DialogoExportar
from .dialogos_tareas import DialogoImportarTareas
from .formato import formatear_decimas, leer_decimas, titulo_legible
from .tabla import ESTILO, configurar_estilo

MAX_SUGERENCIAS = 6
ATAJOS_DECIMAS = (5, 10, 25)
MS_RESALTADO = 2500
MODOS = {"Participación": "participacion", "Examen": "examen", "Tareas": "tareas"}
# Por modo: (texto del botón, ancho, placeholder del campo, color, color al pasar el ratón, ayuda)
AJUSTES_MODO = {
    "participacion": (
        "Guardar", 100, "Décimas", tema.COLOR_ACENTO, tema.COLOR_ACENTO_HOVER,
        "Escribe cuenta o nombre (o haz clic en un alumno de la tabla), las décimas y presiona "
        "Enter. Los negativos restan; el total no baja de 0.",
    ),
    "examen": (
        "Registrar examen", 140, "Calificación", tema.COLOR_EXAMEN, tema.COLOR_EXAMEN_HOVER,
        "Elige el examen, escribe cuenta o nombre y la calificación, y presiona Enter.",
    ),
    "tareas": (
        "Registrar tareas", 140, "Calificación de tareas", tema.COLOR_TAREAS, tema.COLOR_TAREAS_HOVER,
        "Escribe cuenta o nombre y la calificación de tareas (el promedio de la otra plataforma) "
        "y presiona Enter.",
    ),
}
SIN_EXAMENES = "(sin exámenes)"

COLUMNAS = (
    ("numero", "No.", 55, "center"),
    ("cuenta", "Cuenta", 120, "center"),
    ("nombre", "Nombre", 320, "w"),
    ("total", "Décimas", 100, "e"),
    ("tareas", "Tareas", 90, "e"),
    ("ultima", "Última", 110, "center"),
)


class VistaCurso(ctk.CTkFrame):
    def __init__(self, master, app, curso_id: int) -> None:
        super().__init__(master, fg_color="transparent")
        self._app = app
        self._servicio = app.servicio
        self.curso = next(
            c for c in self._servicio.listar_cursos(incluir_archivados=True) if c.id == curso_id
        )
        self._filas: list[ResumenAlumno] = []
        self._numeros: dict[int, int] = {}
        self._tipos: dict[int, TipoInscripcion] = {}
        self._elegido: Alumno | None = None
        self._sugerencias: list[Alumno] = []
        self._indice_sug = -1
        self._ultimo_registro: int | None = None
        self._orden = ("nombre", False)
        self._tarea_resaltado = None
        self._modo = "participacion"
        self._examenes: list[Examen] = []
        self._firma_examenes: list[tuple[int, str]] = []
        self._columnas: tuple = COLUMNAS
        self._examen_actual: Examen | None = None
        self._pendiente: tuple[Alumno, float] | None = None  # reemplazo por confirmar
        # Última calificación guardada: (examen_id, alumno_id, calificación previa) para deshacer.
        self._ultima_calificacion: tuple[int, int, Calificacion | None] | None = None
        # Última calificación de tareas guardada: (alumno_id, calificación previa) para deshacer.
        self._ultima_tareas: tuple[int, CalificacionTareas | None] | None = None
        # Última importación de tareas: {alumno_id: calificación previa} para deshacerla completa.
        self._ultima_importacion: dict[int, CalificacionTareas | None] | None = None

        self._construir_encabezado()
        self._construir_registro()
        self._construir_franja()
        self._construir_filtros()
        self._construir_tabla()
        self.recargar()
        self.after(150, self._entrada_alumno.focus_set)

    # ====================== construcción ======================
    def _construir_encabezado(self) -> None:
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.pack(fill="x", padx=24, pady=(16, 0))
        ctk.CTkButton(
            cab, text="←  Cursos", width=90, height=28, fg_color="transparent",
            text_color=tema.COLOR_ACENTO_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
            command=lambda: self._app.mostrar("cursos"),
        ).pack(anchor="w", padx=(0, 0))
        titulo = ctk.CTkFrame(cab, fg_color="transparent")
        titulo.pack(fill="x", pady=(2, 0))
        bloque = ctk.CTkFrame(titulo, fg_color="transparent")
        bloque.pack(side="left")
        ctk.CTkLabel(bloque, text=titulo_legible(self.curso.materia), anchor="w",
                     font=tema.fuente(22, "bold")).pack(anchor="w")
        ctk.CTkLabel(bloque, text=f"Grupo {self.curso.grupo}  ·  Semestre {self.curso.ciclo}",
                     anchor="w", text_color=tema.COLOR_TEXTO_SUAVE).pack(anchor="w")
        for texto, comando in (
            ("⬇  Exportar", self.exportar),
            ("＋  Agregar alumno", self.agregar_alumno),
            ("⬆  Importar tareas", self.importar_tareas),
        ):
            ctk.CTkButton(
                titulo, text=texto, height=34, command=comando,
                fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
                text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
            ).pack(side="right", anchor="s", padx=(8, 0))

    def _construir_registro(self) -> None:
        marco = ctk.CTkFrame(self, corner_radius=12, fg_color=tema.COLOR_TARJETA,
                             border_width=1, border_color=tema.COLOR_BORDE)
        marco.pack(fill="x", padx=24, pady=(14, 0))
        cabecera = ctk.CTkFrame(marco, fg_color="transparent")
        cabecera.pack(fill="x", padx=16, pady=(10, 0))
        ctk.CTkLabel(cabecera, text="Registro rápido", font=tema.fuente(13, "bold"), anchor="w"
                     ).pack(side="left")
        self._selector_modo = ctk.CTkSegmentedButton(
            cabecera, values=list(MODOS), command=self._cambiar_modo, height=30,
            selected_color=tema.COLOR_ACENTO, selected_hover_color=tema.COLOR_ACENTO_HOVER,
        )
        self._selector_modo.set("Participación")
        self._selector_modo.pack(side="right")

        # Solo visible en modo Examen: elegir el examen o crear uno nuevo.
        self._fila_examen = ctk.CTkFrame(marco, fg_color="transparent")
        ctk.CTkLabel(self._fila_examen, text="Examen", font=tema.fuente(12),
                     text_color=tema.COLOR_TEXTO_SUAVE).pack(side="left", padx=(0, 8))
        self._menu_examen = ctk.CTkOptionMenu(
            self._fila_examen, values=[SIN_EXAMENES], command=self._elegir_examen, height=32,
            width=220, fg_color=tema.COLOR_EXAMEN, button_color=tema.COLOR_EXAMEN_HOVER,
            button_hover_color=tema.COLOR_EXAMEN_HOVER,
        )
        self._menu_examen.pack(side="left")
        ctk.CTkButton(
            self._fila_examen, text="＋  Nuevo", width=90, height=32, command=self.nuevo_examen,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
        ).pack(side="left", padx=(8, 0))
        self._boton_menu_examen = ctk.CTkButton(
            self._fila_examen, text="⋯", width=36, height=32, command=self._menu_examen_abrir,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
        )
        self._boton_menu_examen.pack(side="left", padx=(8, 0))

        fila = ctk.CTkFrame(marco, fg_color="transparent")
        fila.pack(fill="x", padx=16, pady=(6, 12))
        fila.grid_columnconfigure(0, weight=1)
        self._fila_registro = fila

        self._entrada_alumno = ctk.CTkEntry(
            fila, height=38, placeholder_text="Número de cuenta o nombre del alumno…"
        )
        self._entrada_alumno.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._entrada_alumno.bind("<KeyRelease>", self._al_escribir_alumno)
        self._entrada_alumno.bind("<Down>", lambda _e: self._mover_sugerencia(1))
        self._entrada_alumno.bind("<Up>", lambda _e: self._mover_sugerencia(-1))
        self._entrada_alumno.bind("<Return>", self._enter_alumno)
        self._entrada_alumno.bind("<Escape>", lambda _e: self._ocultar_sugerencias())
        self._entrada_alumno.bind("<F2>", self._alternar_modo)

        self._entrada_decimas = ctk.CTkEntry(fila, height=38, width=110, placeholder_text="Décimas")
        self._entrada_decimas.grid(row=0, column=1, padx=(0, 6))
        self._entrada_decimas.bind("<Return>", lambda _e: self.guardar())
        self._entrada_decimas.bind("<F2>", self._alternar_modo)

        self._atajos: list[ctk.CTkButton] = []
        for i, valor in enumerate(ATAJOS_DECIMAS):
            boton = ctk.CTkButton(
                fila, text=f"+{valor}", width=44, height=38, fg_color="transparent",
                border_width=1, border_color=tema.COLOR_BORDE, text_color=tema.COLOR_TEXTO,
                hover_color=tema.COLOR_NAV_ACTIVO,
                command=lambda v=valor: self._poner_decimas(v),
            )
            boton.grid(row=0, column=2 + i, padx=3)
            self._atajos.append(boton)
        self._boton_guardar = ctk.CTkButton(
            fila, text="Guardar", width=100, height=38, command=self.guardar,
            fg_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_ACENTO_HOVER,
        )
        self._boton_guardar.grid(row=0, column=2 + len(ATAJOS_DECIMAS), padx=(10, 0))

        # Sugerencias en línea (debajo de la fila), ocultas hasta que haya coincidencias.
        self._caja_sugerencias = ctk.CTkFrame(marco, fg_color="transparent")
        self._botones_sug: list[ctk.CTkButton] = []

    def _construir_franja(self) -> None:
        self._franja = ctk.CTkFrame(self, corner_radius=10, height=44, fg_color=tema.COLOR_TARJETA,
                                    border_width=1, border_color=tema.COLOR_BORDE)
        self._franja.pack(fill="x", padx=24, pady=(10, 0))
        self._franja.pack_propagate(False)
        self._mensaje = ctk.CTkLabel(self._franja, anchor="w", font=tema.fuente(13))
        self._mensaje.pack(side="left", fill="x", expand=True, padx=14)
        self._boton_deshacer = ctk.CTkButton(
            self._franja, text="Deshacer", width=90, height=28, command=self.deshacer,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
        )
        self._boton_cancelar = ctk.CTkButton(
            self._franja, text="Cancelar", width=90, height=28, command=self.cancelar_reemplazo,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
        )
        self._boton_confirmar = ctk.CTkButton(
            self._franja, text="Reemplazar", width=100, height=28, command=self.confirmar_reemplazo,
            fg_color=tema.COLOR_EXAMEN, hover_color=tema.COLOR_EXAMEN_HOVER,
        )
        self._info(
            "Escribe cuenta o nombre (o haz clic en un alumno de la tabla), las décimas y presiona "
            "Enter. Los negativos restan; el total no baja de 0."
        )

    def _construir_filtros(self) -> None:
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=24, pady=(14, 6))
        self._buscar = ctk.CTkEntry(fila, placeholder_text="🔍  Filtrar la tabla…", width=240, height=32)
        self._buscar.pack(side="left")
        self._buscar.bind("<KeyRelease>", lambda _e: self._dibujar_tabla())
        self._ver_oyentes = ctk.CTkCheckBox(
            fila, text="Mostrar oyentes", command=self._dibujar_tabla,
            checkbox_width=20, checkbox_height=20,
        )
        self._ver_oyentes.select()
        self._ver_oyentes.pack(side="left", padx=16)
        self._resumen = ctk.CTkLabel(fila, text="", text_color=tema.COLOR_TEXTO_SUAVE)
        self._resumen.pack(side="right")

    def _construir_tabla(self) -> None:
        colores = configurar_estilo()

        marco = ctk.CTkFrame(self, corner_radius=12, fg_color=tema.COLOR_TARJETA,
                             border_width=1, border_color=tema.COLOR_BORDE)
        marco.pack(fill="both", expand=True, padx=24, pady=(0, 18))
        self._tabla = ttk.Treeview(
            marco, columns=[c[0] for c in COLUMNAS], show="headings", style=ESTILO,
            selectmode="browse",
        )
        self._columnas = COLUMNAS
        self._aplicar_columnas()
        self._tabla.bind("<ButtonRelease-1>", self._al_clic_tabla)
        self._tabla.bind("<Double-1>", self._al_doble_clic)
        self._tabla.bind("<F2>", self._alternar_modo)
        barra = ctk.CTkScrollbar(marco, command=self._tabla.yview)
        # Con varios exámenes las columnas pueden no caber: la tabla se desplaza horizontalmente.
        barra_h = ctk.CTkScrollbar(marco, orientation="horizontal", command=self._tabla.xview)
        self._tabla.configure(yscrollcommand=barra.set, xscrollcommand=barra_h.set)
        barra_h.pack(side="bottom", fill="x", padx=8, pady=(0, 4))
        self._tabla.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        barra.pack(side="right", fill="y", padx=(0, 4), pady=8)
        self._tabla.tag_configure("oyente", foreground=colores["suave"])
        self._tabla.tag_configure("reciente", background=colores["reciente"])

    # ====================== datos / tabla ======================
    def _aplicar_columnas(self) -> None:
        """Columnas fijas más una por examen («Examen - <nombre>»), antes de «Última»."""
        examenes = tuple(
            (f"examen_{e.id}", f"Examen - {e.nombre}", max(120, 7 * (len(e.nombre) + 9) + 40), "e")
            for e in self._examenes
        )
        self._columnas = COLUMNAS[:-1] + examenes + COLUMNAS[-1:]
        self._tabla.configure(columns=[c[0] for c in self._columnas])
        for clave, titulo, ancho, alineacion in self._columnas:
            self._tabla.heading(clave, text=titulo, anchor=alineacion,
                                command=lambda c=clave: self._ordenar_por(c))
            self._tabla.column(clave, width=ancho, anchor=alineacion,
                               stretch=(clave == "nombre"),
                               minwidth=240 if clave == "nombre" else ancho if clave.startswith("examen_") else 50)
        if self._orden[0] not in {c[0] for c in self._columnas}:  # p. ej. se eliminó ese examen
            self._orden = ("nombre", False)

    def recargar(self) -> None:
        self._filas = self._servicio.resumen_curso(self.curso.id)
        self._examenes = self._servicio.listar_examenes(self.curso.id)
        firma = [(e.id, e.nombre) for e in self._examenes]
        if firma != self._firma_examenes:
            self._firma_examenes = firma
            self._aplicar_columnas()
        self._numeros = {f.alumno.id: n for n, f in enumerate(self._filas, start=1)}
        self._tipos = {f.alumno.id: f.tipo for f in self._filas}
        self._dibujar_tabla()

    def _filtradas(self) -> list[ResumenAlumno]:
        filas = self._filas
        if not self._ver_oyentes.get():
            filas = [f for f in filas if f.tipo == TipoInscripcion.REGULAR]
        tokens = normalizar(self._buscar.get()).split()
        if tokens:
            filas = [
                f for f in filas
                if all(t in normalizar(f"{f.alumno.nombre_completo} {f.alumno.num_cuenta or ''}")
                       for t in tokens)
            ]
        clave, descendente = self._orden
        llaves = {
            "numero": lambda f: self._numeros[f.alumno.id],
            "cuenta": lambda f: (f.alumno.num_cuenta is None, f.alumno.num_cuenta or ""),
            "nombre": lambda f: normalizar(f.alumno.nombre_completo),
            "total": lambda f: f.total,
            "tareas": lambda f: f.tareas,
            "ultima": lambda f: (f.ultima_fecha is None, f.ultima_fecha or 0),
        }
        if clave.startswith("examen_"):
            examen_id = int(clave.removeprefix("examen_"))
            llave = lambda f: f.calificaciones.get(examen_id, 0.0)  # noqa: E731
        else:
            llave = llaves[clave]
        return sorted(filas, key=llave, reverse=descendente)

    def _dibujar_tabla(self) -> None:
        self._tabla.delete(*self._tabla.get_children())
        for f in self._filtradas():
            self._tabla.insert(
                "", "end", iid=str(f.alumno.id),
                values=(
                    self._numeros[f.alumno.id],
                    f.alumno.num_cuenta or "—",
                    f.alumno.nombre_completo + ("   (oyente)" if f.tipo == TipoInscripcion.OYENTE else ""),
                    formatear_decimas(f.total),
                    formatear_decimas(f.tareas),
                    *(formatear_decimas(f.calificaciones.get(e.id, 0.0)) for e in self._examenes),
                    f.ultima_fecha.strftime("%d/%m/%Y") if f.ultima_fecha else "—",
                ),
                tags=("oyente",) if f.tipo == TipoInscripcion.OYENTE else (),
            )
        for clave, titulo, *_ in self._columnas:
            flecha = ""
            if clave == self._orden[0]:
                flecha = "  ▼" if self._orden[1] else "  ▲"
            self._tabla.heading(clave, text=titulo + flecha)
        self._actualizar_resumen()

    def _actualizar_resumen(self) -> None:
        regulares = [f for f in self._filas if f.tipo == TipoInscripcion.REGULAR]
        oyentes = len(self._filas) - len(regulares)
        promedio = sum(f.total for f in regulares) / len(regulares) if regulares else 0
        sin = sum(1 for f in regulares if f.n_participaciones == 0)
        partes = [f"{len(regulares)} alumnos"]
        if oyentes:
            partes.append(f"{oyentes} oyente" + ("s" if oyentes != 1 else ""))
        partes += [f"promedio {formatear_decimas(promedio)}", f"{sin} sin participaciones"]
        self._resumen.configure(text="  ·  ".join(partes))

    def _al_clic_tabla(self, evento) -> None:
        """Un clic en una fila pone al alumno en el campo de registro y pasa a las décimas."""
        iid = self._tabla.identify_row(evento.y)
        if not iid or self._tabla.identify_region(evento.x, evento.y) == "heading":
            return
        fila = next((f for f in self._filas if str(f.alumno.id) == iid), None)
        if fila:
            self._elegir(fila.alumno)

    def _al_doble_clic(self, evento) -> None:
        """Doble clic en una fila abre el historial de ese alumno."""
        iid = self._tabla.identify_row(evento.y)
        if iid and self._tabla.identify_region(evento.x, evento.y) != "heading":
            self._app.abrir_historial(self.curso.id, int(iid))

    def _ordenar_por(self, clave: str) -> None:
        descendente = (not self._orden[1]) if self._orden[0] == clave else (clave in ("total", "tareas", "ultima") or clave.startswith("examen_"))
        self._orden = (clave, descendente)
        self._dibujar_tabla()

    def _resaltar(self, alumno_id: int) -> None:
        iid = str(alumno_id)
        if not self._tabla.exists(iid):
            return
        self._tabla.see(iid)
        self._tabla.selection_set(iid)
        etiquetas = tuple(self._tabla.item(iid, "tags"))
        self._tabla.item(iid, tags=etiquetas + ("reciente",))
        if self._tarea_resaltado:
            self.after_cancel(self._tarea_resaltado)
        self._tarea_resaltado = self.after(MS_RESALTADO, lambda: self._quitar_resaltado(iid))

    def _quitar_resaltado(self, iid: str) -> None:
        self._tarea_resaltado = None
        if self.winfo_exists() and self._tabla.exists(iid):
            self._tabla.item(iid, tags=tuple(t for t in self._tabla.item(iid, "tags") if t != "reciente"))
            self._tabla.selection_remove(iid)

    # ====================== franja de mensajes ======================
    def _ocultar_acciones(self) -> None:
        for boton in (self._boton_deshacer, self._boton_confirmar, self._boton_cancelar):
            boton.pack_forget()

    def _info(self, texto: str) -> None:
        self._mensaje.configure(text=texto, text_color=tema.COLOR_TEXTO_SUAVE)
        self._ocultar_acciones()

    def _error(self, texto: str) -> None:
        self._mensaje.configure(text="⚠  " + texto, text_color=tema.COLOR_PELIGRO)
        self._ocultar_acciones()

    def _exito(self, texto: str, deshacible: bool) -> None:
        self._mensaje.configure(text="✓  " + texto, text_color=tema.COLOR_EXITO)
        self._ocultar_acciones()
        if deshacible:
            self._boton_deshacer.pack(side="right", padx=10)
        else:
            self._boton_deshacer.pack_forget()

    # ====================== autocompletado ======================
    def _al_escribir_alumno(self, evento) -> None:
        if evento.keysym in ("Up", "Down", "Return", "Escape", "Tab", "Shift_L", "Shift_R",
                             "Control_L", "Control_R"):
            return
        texto = self._entrada_alumno.get()
        if self._elegido and texto != self._elegido.nombre_completo:
            self._elegido = None
        if self._elegido or not texto.strip():
            self._ocultar_sugerencias()
            return
        self._sugerencias = self._servicio.buscar_alumnos_en_curso(self.curso.id, texto)[:MAX_SUGERENCIAS]
        self._indice_sug = -1
        self._pintar_sugerencias()

    def _pintar_sugerencias(self) -> None:
        for boton in self._botones_sug:
            boton.destroy()
        self._botones_sug.clear()
        if not self._sugerencias:
            self._caja_sugerencias.pack_forget()
            return
        self._caja_sugerencias.pack(fill="x", padx=16, pady=(0, 10))
        for i, alumno in enumerate(self._sugerencias):
            sufijo = "   (oyente)" if self._tipos.get(alumno.id) == TipoInscripcion.OYENTE else ""
            boton = ctk.CTkButton(
                self._caja_sugerencias, anchor="w", height=30, corner_radius=6,
                text=f"{alumno.nombre_completo}{sufijo}    ·    {alumno.num_cuenta or 'sin cuenta'}",
                fg_color=tema.COLOR_NAV_ACTIVO if i == self._indice_sug else "transparent",
                text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
                command=lambda a=alumno: self._elegir(a),
            )
            boton.pack(fill="x", pady=1)
            self._botones_sug.append(boton)

    def _ocultar_sugerencias(self) -> None:
        self._sugerencias = []
        self._indice_sug = -1
        self._pintar_sugerencias()

    def _mover_sugerencia(self, paso: int) -> str:
        if self._sugerencias:
            self._indice_sug = (self._indice_sug + paso) % len(self._sugerencias)
            self._pintar_sugerencias()
        return "break"

    def _elegir(self, alumno: Alumno) -> None:
        self._elegido = alumno
        self._entrada_alumno.delete(0, "end")
        self._entrada_alumno.insert(0, alumno.nombre_completo)
        self._ocultar_sugerencias()
        if self._modo in ("examen", "tareas"):
            self._cargar_calificacion_actual(alumno)
        self._entrada_decimas.focus_set()
        self._entrada_decimas.select_range(0, "end")

    def _cargar_calificacion_actual(self, alumno: Alumno) -> None:
        """En modo Examen o Tareas, elegir a un alumno trae su calificación para corregirla."""
        self._entrada_decimas.delete(0, "end")
        if self._modo == "tareas":
            actual = self._servicio.tareas_de(self.curso.id, alumno.id)
        elif self._examen_actual is None:
            return
        else:
            actual = self._servicio.calificacion_de(self._examen_actual.id, alumno.id)
        if actual:
            self._entrada_decimas.insert(0, formatear_decimas(actual.puntos))

    def _enter_alumno(self, _evento=None) -> str:
        if self._sugerencias:
            if self._indice_sug >= 0:
                self._elegir(self._sugerencias[self._indice_sug])
                return "break"
            if len(self._sugerencias) == 1:
                self._elegir(self._sugerencias[0])
                return "break"
        self._ocultar_sugerencias()
        self._entrada_decimas.focus_set()
        return "break"

    def _poner_decimas(self, valor: float) -> None:
        self._entrada_decimas.delete(0, "end")
        self._entrada_decimas.insert(0, str(valor))
        self._entrada_decimas.focus_set()

    # ====================== registro ======================
    def guardar(self) -> None:
        if self._modo == "examen":
            self._guardar_examen()
            return
        if self._modo == "tareas":
            self._guardar_tareas()
            return
        consulta = self._entrada_alumno.get().strip()
        if not consulta:
            self._error("Escribe un número de cuenta o un nombre.")
            self._entrada_alumno.focus_set()
            return
        try:
            decimas = leer_decimas(self._entrada_decimas.get())
        except ValueError:
            self._error("Las décimas deben ser un número (por ejemplo 10, 2.5 o -5).")
            self._entrada_decimas.focus_set()
            return

        try:
            if self._elegido:
                resultado = self._servicio.registrar_para_alumno(
                    self.curso.id, self._elegido.id, decimas
                )
            else:
                resultado = self._servicio.registrar(self.curso.id, consulta, decimas)
        except ErrorDominio as error:
            self._error(str(error))
            return

        if resultado.estado == EstadoRegistro.GUARDADO:
            self._registrado(resultado)
        elif resultado.estado == EstadoRegistro.AMBIGUO:
            alumno = DialogoElegirAlumno(self, consulta, resultado.candidatos, self._tipos).mostrar()
            if alumno:
                self._elegido = alumno
                self.guardar()
            else:
                self._info("Registro cancelado: había varias coincidencias.")
        else:
            self._ofrecer_alta(consulta, decimas, resultado)

    def _ofrecer_alta(self, consulta: str, decimas: float, resultado: ResultadoRegistro) -> None:
        def crear_y_registrar(datos: dict) -> ResultadoRegistro:
            if datos["alumno_id"]:
                self._servicio.inscribir_alumno_existente(self.curso.id, datos["alumno_id"], datos["tipo"])
                alumno_id = datos["alumno_id"]
            else:
                alumno_id = self._servicio.crear_alumno_en_curso(
                    self.curso.id, datos["nombre"], datos["tipo"], datos["cuenta"]
                ).id
            return self._servicio.registrar_para_alumno(self.curso.id, alumno_id, decimas)

        creado = DialogoAlumnoNuevo(
            self, crear_y_registrar, consulta, formatear_decimas(decimas, True), resultado.candidatos
        ).mostrar()
        if creado:
            self._registrado(creado, alumno_nuevo=True)
        else:
            self._info(f"Registro cancelado: «{consulta}» no está en este curso.")
            self._entrada_alumno.focus_set()

    def _registrado(self, resultado: ResultadoRegistro, alumno_nuevo: bool = False) -> None:
        self._ultimo_registro = resultado.participacion.id
        self._ultima_calificacion = None
        self._ultima_tareas = None
        self._ultima_importacion = None
        nuevo = "  (alumno agregado)" if alumno_nuevo else ""
        aplicadas = resultado.decimas_aplicadas
        if aplicadas is not None and abs(aplicadas - resultado.decimas) > 1e-9:
            efecto = (f"{formatear_decimas(resultado.decimas, True)} solicitadas, "
                      f"se aplicaron {formatear_decimas(aplicadas, True)} (mínimo 0)")
        else:
            efecto = f"{formatear_decimas(resultado.decimas, True)} décimas"
        self._exito(
            f"{resultado.alumno.nombre_completo}  ·  {efecto}  →  "
            f"total {formatear_decimas(resultado.total)}{nuevo}",
            deshacible=True,
        )
        self._elegido = None
        self._entrada_alumno.delete(0, "end")
        self._entrada_decimas.delete(0, "end")
        self._ocultar_sugerencias()
        self.recargar()
        self._resaltar(resultado.alumno.id)
        self._entrada_alumno.focus_set()

    def deshacer(self) -> None:
        if self._ultima_importacion is not None:
            self._deshacer_importacion()
            return
        if self._ultima_tareas is not None:
            self._deshacer_tareas()
            return
        if self._ultima_calificacion is not None:
            self._deshacer_calificacion()
            return
        if self._ultimo_registro is None:
            return
        try:
            quitada = self._servicio.deshacer(self._ultimo_registro)
        except ErrorDominio as error:
            self._error(str(error))
            return
        finally:
            self._ultimo_registro = None
        alumno = next((f.alumno for f in self._filas if f.alumno.id == quitada.alumno_id), None)
        self.recargar()
        self._info(
            f"Se deshizo el registro de {formatear_decimas(quitada.decimas, True)} décimas"
            + (f" de {alumno.nombre_completo}." if alumno else ".")
        )
        self._entrada_alumno.focus_set()

    # ====================== modos Examen y Tareas ======================
    def _cambiar_modo(self, valor: str) -> None:
        self._modo = MODOS[valor]
        self._pendiente = None
        texto, ancho, placeholder, color, hover, ayuda = AJUSTES_MODO[self._modo]
        if self._modo == "examen":
            self._fila_examen.pack(fill="x", padx=16, pady=(6, 0), before=self._fila_registro)
            self._cargar_examenes()
        else:
            self._fila_examen.pack_forget()
        for boton in self._atajos:  # +5, +10 y +25 solo sirven para décimas
            boton.grid() if self._modo == "participacion" else boton.grid_remove()
        self._entrada_decimas.delete(0, "end")
        self._entrada_decimas.configure(placeholder_text=placeholder)
        self._selector_modo.configure(selected_color=color, selected_hover_color=hover)
        self._boton_guardar.configure(text=texto, width=ancho, fg_color=color, hover_color=hover)
        self._info(ayuda)
        self._entrada_alumno.focus_set()

    def _cargar_examenes(self, seleccionar: int | None = None) -> None:
        self._examenes = self._servicio.listar_examenes(self.curso.id)
        previo = seleccionar or (self._examen_actual.id if self._examen_actual else None)
        self._examen_actual = (
            next((e for e in self._examenes if e.id == previo), None)
            or (self._examenes[-1] if self._examenes else None)
        )
        nombres = [e.nombre for e in self._examenes] or [SIN_EXAMENES]
        self._menu_examen.configure(values=nombres)
        self._menu_examen.set(self._examen_actual.nombre if self._examen_actual else SIN_EXAMENES)

    def _elegir_examen(self, nombre: str) -> None:
        self._examen_actual = next((e for e in self._examenes if e.nombre == nombre), None)
        self._pendiente = None
        self._entrada_alumno.focus_set()

    def nuevo_examen(self) -> None:
        examen = DialogoExamen(
            self, lambda nombre: self._servicio.crear_examen(self.curso.id, nombre)
        ).mostrar()
        if examen:
            self._cargar_examenes(examen.id)
            self.recargar()  # la tabla gana su columna
            self._info(f"Examen «{examen.nombre}» creado.")
        self._entrada_alumno.focus_set()

    def _menu_examen_abrir(self) -> None:
        """«⋯»: renombrar o eliminar el examen elegido."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Renombrar…", command=self.renombrar_examen)
        menu.add_command(label="Eliminar…", command=self.eliminar_examen)
        boton = self._boton_menu_examen
        try:
            menu.tk_popup(boton.winfo_rootx(), boton.winfo_rooty() + boton.winfo_height())
        finally:
            menu.grab_release()

    def renombrar_examen(self) -> None:
        examen = self._examen_actual
        if examen is None:
            self._error("No hay un examen elegido. Crea uno con «＋ Nuevo».")
            return
        nuevo = DialogoExamen(
            self, lambda nombre: self._servicio.renombrar_examen(examen.id, nombre), examen
        ).mostrar()
        if nuevo:
            self._cargar_examenes(nuevo.id)
            self.recargar()  # el encabezado de la columna cambia de nombre
            self._info(f"Examen renombrado a «{nuevo.nombre}».")
        self._entrada_alumno.focus_set()

    def eliminar_examen(self) -> None:
        examen = self._examen_actual
        if examen is None:
            self._error("No hay un examen elegido para eliminar.")
            return
        perdidas = self._servicio.resumen_eliminacion_examen(examen.id)
        if perdidas:
            detalle = (f"Se perderá {perdidas} calificación de alumnos." if perdidas == 1
                       else f"Se perderán {perdidas} calificaciones de alumnos.")
        else:
            detalle = "El examen no tiene calificaciones capturadas."
        if not messagebox.askyesno(
            "Eliminar examen",
            f"¿Eliminar el examen «{examen.nombre}»?\n\n{detalle}\nEsta acción no se puede deshacer.",
            parent=self,
        ):
            return
        try:
            self._servicio.eliminar_examen(examen.id)
        except ErrorDominio as error:
            self._error(str(error))
            return
        self._pendiente = None
        if self._ultima_calificacion and self._ultima_calificacion[0] == examen.id:
            self._ultima_calificacion = None
        self._examen_actual = None
        self._cargar_examenes()
        self.recargar()  # desaparece su columna
        self._exito(f"Examen «{examen.nombre}» eliminado.", deshacible=False)
        self._entrada_alumno.focus_set()

    def _guardar_examen(self) -> None:
        if self._examen_actual is None:
            self._error("Primero crea un examen con «＋ Nuevo».")
            return
        consulta = self._entrada_alumno.get().strip()
        if not consulta:
            self._error("Escribe un número de cuenta o un nombre.")
            self._entrada_alumno.focus_set()
            return
        try:
            puntos = leer_decimas(self._entrada_decimas.get())
        except ValueError:
            self._error("La calificación debe ser un número (por ejemplo 8.5 o 42).")
            self._entrada_decimas.focus_set()
            return

        examen = self._examen_actual
        try:
            if self._elegido:
                resultado = self._servicio.registrar_calificacion_para_alumno(
                    self.curso.id, examen.id, self._elegido.id, puntos
                )
            else:
                resultado = self._servicio.registrar_calificacion(
                    self.curso.id, examen.id, consulta, puntos
                )
        except ErrorDominio as error:
            self._error(str(error))
            return

        if resultado.estado == EstadoRegistro.GUARDADO:
            self._calificado(resultado)
        elif resultado.estado == EstadoRegistro.CONFIRMAR_REEMPLAZO:
            self._pedir_reemplazo(resultado)
        elif resultado.estado == EstadoRegistro.AMBIGUO:
            alumno = DialogoElegirAlumno(self, consulta, resultado.candidatos, self._tipos).mostrar()
            if alumno:
                self._elegido = alumno
                self._guardar_examen()
            else:
                self._info("Registro cancelado: había varias coincidencias.")
        else:
            self._ofrecer_alta_examen(consulta, puntos, examen, resultado)

    def _ofrecer_alta_examen(
        self, consulta: str, puntos: float, examen: Examen, resultado: ResultadoCalificacion
    ) -> None:
        def crear_y_calificar(datos: dict) -> ResultadoCalificacion:
            if datos["alumno_id"]:
                self._servicio.inscribir_alumno_existente(self.curso.id, datos["alumno_id"], datos["tipo"])
                alumno_id = datos["alumno_id"]
            else:
                alumno_id = self._servicio.crear_alumno_en_curso(
                    self.curso.id, datos["nombre"], datos["tipo"], datos["cuenta"]
                ).id
            return self._servicio.registrar_calificacion_para_alumno(
                self.curso.id, examen.id, alumno_id, puntos
            )

        creado = DialogoAlumnoNuevo(
            self, crear_y_calificar, consulta, None, resultado.candidatos,
            resumen_registro=f"{examen.nombre}: {formatear_decimas(puntos)}",
        ).mostrar()
        if creado:
            self._calificado(creado, alumno_nuevo=True)
        else:
            self._info(f"Registro cancelado: «{consulta}» no está en este curso.")
            self._entrada_alumno.focus_set()

    def _pedir_reemplazo(self, resultado: ResultadoCalificacion) -> None:
        """Ya había una calificación: avisa y espera confirmación (nada se guardó aún)."""
        self._advertir_reemplazo(
            resultado.alumno, resultado.puntos,
            f"Ya tiene {formatear_decimas(resultado.calificacion_anterior.puntos)} en "
            f"{resultado.examen.nombre}; se cambiará a {formatear_decimas(resultado.puntos)}.",
        )

    def _advertir_reemplazo(self, alumno: Alumno, puntos: float, texto: str) -> None:
        self._pendiente = (alumno, puntos)
        self._mensaje.configure(text=f"⚠  {alumno.nombre_completo}  ·  {texto}",
                                text_color=tema.COLOR_AVISO)
        self._ocultar_acciones()
        _t, _a, _p, color, hover, _h = AJUSTES_MODO[self._modo]  # el botón lleva el color del modo
        self._boton_confirmar.configure(fg_color=color, hover_color=hover)
        self._boton_confirmar.pack(side="right", padx=(0, 10))
        self._boton_cancelar.pack(side="right", padx=(0, 6))

    def confirmar_reemplazo(self) -> None:
        if self._pendiente is None:
            return
        if self._modo == "tareas":
            self._confirmar_reemplazo_tareas()
            return
        if self._examen_actual is None:
            return
        alumno, puntos = self._pendiente
        self._pendiente = None
        try:
            resultado = self._servicio.registrar_calificacion_para_alumno(
                self.curso.id, self._examen_actual.id, alumno.id, puntos, reemplazar=True
            )
        except ErrorDominio as error:
            self._error(str(error))
            return
        self._calificado(resultado)

    def cancelar_reemplazo(self) -> None:
        self._pendiente = None
        self._info("Reemplazo cancelado: la calificación anterior se conserva.")
        self._entrada_alumno.focus_set()

    def _calificado(self, resultado: ResultadoCalificacion, alumno_nuevo: bool = False) -> None:
        nuevo = "  (alumno agregado)" if alumno_nuevo else ""
        antes = (f"  (antes {formatear_decimas(resultado.calificacion_anterior.puntos)})"
                 if resultado.calificacion_anterior else "")
        self._exito(
            f"{resultado.alumno.nombre_completo}  ·  {resultado.examen.nombre}: "
            f"{formatear_decimas(resultado.puntos)}{antes}{nuevo}",
            deshacible=True,
        )
        self._ultimo_registro = None
        self._ultima_tareas = None
        self._ultima_importacion = None
        self._ultima_calificacion = (
            resultado.examen.id, resultado.alumno.id, resultado.calificacion_anterior
        )
        self._pendiente = None
        self._elegido = None
        self._entrada_alumno.delete(0, "end")
        self._entrada_decimas.delete(0, "end")
        self._ocultar_sugerencias()
        self.recargar()
        self._resaltar(resultado.alumno.id)
        self._entrada_alumno.focus_set()

    def _deshacer_calificacion(self) -> None:
        examen_id, alumno_id, anterior = self._ultima_calificacion
        self._ultima_calificacion = None
        try:
            self._servicio.deshacer_calificacion(examen_id, alumno_id, anterior)
        except ErrorDominio as error:
            self._error(str(error))
            return
        alumno = next((f.alumno for f in self._filas if f.alumno.id == alumno_id), None)
        examen = next((e for e in self._examenes if e.id == examen_id), None)
        self.recargar()
        self._info(
            "Se deshizo la calificación"
            + (f" de {alumno.nombre_completo}" if alumno else "")
            + (f" en {examen.nombre}." if examen else ".")
        )
        self._entrada_alumno.focus_set()

    def _alternar_modo(self, _evento=None) -> str:
        """F2: recorre los modos (Participación → Examen → Tareas) sin soltar el teclado."""
        nombres = list(MODOS)
        actual = next(n for n, m in MODOS.items() if m == self._modo)
        valor = nombres[(nombres.index(actual) + 1) % len(nombres)]
        self._selector_modo.set(valor)
        self._cambiar_modo(valor)
        return "break"

    # ====================== calificación de tareas ======================
    def _guardar_tareas(self) -> None:
        consulta = self._entrada_alumno.get().strip()
        if not consulta:
            self._error("Escribe un número de cuenta o un nombre.")
            self._entrada_alumno.focus_set()
            return
        try:
            puntos = leer_decimas(self._entrada_decimas.get())
        except ValueError:
            self._error("La calificación de tareas debe ser un número (por ejemplo 8.5 o 85).")
            self._entrada_decimas.focus_set()
            return

        try:
            if self._elegido:
                resultado = self._servicio.registrar_tareas_para_alumno(
                    self.curso.id, self._elegido.id, puntos
                )
            else:
                resultado = self._servicio.registrar_tareas(self.curso.id, consulta, puntos)
        except ErrorDominio as error:
            self._error(str(error))
            return

        if resultado.estado == EstadoRegistro.GUARDADO:
            self._tareas_guardadas(resultado)
        elif resultado.estado == EstadoRegistro.CONFIRMAR_REEMPLAZO:
            self._advertir_reemplazo(
                resultado.alumno, resultado.puntos,
                f"Ya tiene {formatear_decimas(resultado.anterior.puntos)} en tareas; "
                f"se cambiará a {formatear_decimas(resultado.puntos)}.",
            )
        elif resultado.estado == EstadoRegistro.AMBIGUO:
            alumno = DialogoElegirAlumno(self, consulta, resultado.candidatos, self._tipos).mostrar()
            if alumno:
                self._elegido = alumno
                self._guardar_tareas()
            else:
                self._info("Registro cancelado: había varias coincidencias.")
        else:
            self._ofrecer_alta_tareas(consulta, puntos, resultado)

    def _ofrecer_alta_tareas(self, consulta: str, puntos: float, resultado: ResultadoTareas) -> None:
        def crear_y_calificar(datos: dict) -> ResultadoTareas:
            if datos["alumno_id"]:
                self._servicio.inscribir_alumno_existente(self.curso.id, datos["alumno_id"], datos["tipo"])
                alumno_id = datos["alumno_id"]
            else:
                alumno_id = self._servicio.crear_alumno_en_curso(
                    self.curso.id, datos["nombre"], datos["tipo"], datos["cuenta"]
                ).id
            return self._servicio.registrar_tareas_para_alumno(self.curso.id, alumno_id, puntos)

        creado = DialogoAlumnoNuevo(
            self, crear_y_calificar, consulta, None, resultado.candidatos,
            resumen_registro=f"tareas: {formatear_decimas(puntos)}",
        ).mostrar()
        if creado:
            self._tareas_guardadas(creado, alumno_nuevo=True)
        else:
            self._info(f"Registro cancelado: «{consulta}» no está en este curso.")
            self._entrada_alumno.focus_set()

    def _confirmar_reemplazo_tareas(self) -> None:
        alumno, puntos = self._pendiente
        self._pendiente = None
        try:
            resultado = self._servicio.registrar_tareas_para_alumno(
                self.curso.id, alumno.id, puntos, reemplazar=True
            )
        except ErrorDominio as error:
            self._error(str(error))
            return
        self._tareas_guardadas(resultado)

    def _tareas_guardadas(self, resultado: ResultadoTareas, alumno_nuevo: bool = False) -> None:
        nuevo = "  (alumno agregado)" if alumno_nuevo else ""
        antes = (f"  (antes {formatear_decimas(resultado.anterior.puntos)})"
                 if resultado.anterior else "")
        self._exito(
            f"{resultado.alumno.nombre_completo}  ·  Tareas: "
            f"{formatear_decimas(resultado.puntos)}{antes}{nuevo}",
            deshacible=True,
        )
        self._ultimo_registro = None
        self._ultima_calificacion = None
        self._ultima_importacion = None
        self._ultima_tareas = (resultado.alumno.id, resultado.anterior)
        self._pendiente = None
        self._elegido = None
        self._entrada_alumno.delete(0, "end")
        self._entrada_decimas.delete(0, "end")
        self._ocultar_sugerencias()
        self.recargar()
        self._resaltar(resultado.alumno.id)
        self._entrada_alumno.focus_set()

    def _deshacer_tareas(self) -> None:
        alumno_id, anterior = self._ultima_tareas
        self._ultima_tareas = None
        try:
            self._servicio.deshacer_tareas(self.curso.id, alumno_id, anterior)
        except ErrorDominio as error:
            self._error(str(error))
            return
        alumno = next((f.alumno for f in self._filas if f.alumno.id == alumno_id), None)
        self.recargar()
        self._info(
            "Se deshizo la calificación de tareas" + (f" de {alumno.nombre_completo}." if alumno else ".")
        )
        self._entrada_alumno.focus_set()

    def _deshacer_importacion(self) -> None:
        anteriores = self._ultima_importacion
        self._ultima_importacion = None
        try:
            self._servicio.deshacer_importacion_tareas(self.curso.id, anteriores)
        except ErrorDominio as error:
            self._error(str(error))
            return
        self.recargar()
        self._info(f"Se deshizo la importación: {len(anteriores)} calificaciones de tareas restauradas.")
        self._entrada_alumno.focus_set()

    # ====================== alumnos ======================
    def agregar_alumno(self) -> None:
        def crear(datos: dict) -> Alumno:
            alumno = self._servicio.crear_alumno_en_curso(
                self.curso.id, datos["nombre"], datos["tipo"], datos["cuenta"]
            )
            return alumno

        alumno = DialogoAlumnoNuevo(self, crear).mostrar()
        if alumno:
            self.recargar()
            self._resaltar(alumno.id)
            self._exito(f"{alumno.nombre_completo} agregado al curso.", deshacible=False)

    # ====================== importar tareas ======================
    def importar_tareas(self) -> None:
        """Lee el archivo de otra plataforma, muestra la vista previa y, si se confirma, lo aplica."""
        ruta = filedialog.askopenfilename(
            parent=self, title="Selecciona el archivo de calificaciones",
            filetypes=[("Excel o CSV", "*.xlsx *.csv"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        try:
            archivo = leer_calificaciones(ruta)
        except ErrorDominio as error:
            messagebox.showerror("No se pudo leer el archivo", str(error), parent=self)
            self._error(str(error))
            return
        opciones = DialogoImportarTareas(
            self, self.curso, Path(ruta).name, archivo,
            lambda clave: self._servicio.previsualizar_importacion_tareas(self.curso.id, archivo, clave),
        ).mostrar()
        if not opciones:
            return
        try:
            resultado = self._servicio.importar_tareas(
                self.curso.id, archivo, opciones["clave"], opciones["confirmadas"]
            )
        except ErrorDominio as error:
            messagebox.showerror("No se pudo importar", str(error), parent=self)
            self._error(str(error))
            return
        self._pendiente = None
        self._ultimo_registro = self._ultima_calificacion = self._ultima_tareas = None  # lo anterior ya no se deshace
        self._ultima_importacion = resultado.anteriores or None
        self.recargar()
        self._exito(
            f"Tareas importadas: {resultado.actualizadas} actualizadas, "
            f"{resultado.omitidas} omitidas.",
            deshacible=bool(resultado.anteriores),
        )
        self._entrada_alumno.focus_set()

    # ====================== exportar ======================
    def exportar(self) -> None:
        oyentes = sum(1 for f in self._filas if f.tipo == TipoInscripcion.OYENTE)
        opciones = DialogoExportar(self, len(self._filas) - oyentes, oyentes).mostrar()
        if not opciones:
            return
        extension = opciones["formato"]
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Guardar exportación", defaultextension=f".{extension}",
            initialfile=nombre_sugerido(self.curso, extension),
            filetypes=[("Excel", "*.xlsx")] if extension == "xlsx" else [("CSV", "*.csv")],
        )
        if not ruta:
            return
        try:
            resultado = exportar_curso(
                self._servicio, self.curso.id, ruta,
                incluir_oyentes=opciones["oyentes"], incluir_detalle=opciones["detalle"],
            )
        except ErrorDominio as error:
            messagebox.showerror("No se pudo exportar", str(error), parent=self)
            self._error(str(error))
            return
        self._exito(
            f"Exportado: {resultado.alumnos} alumnos y {resultado.participaciones} participaciones "
            f"→ {resultado.ruta.name}",
            deshacible=False,
        )
