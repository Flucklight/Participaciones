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
    EstadoEquipo,
    EstadoRegistro,
    Examen,
    ResultadoCalificacion,
    ResultadoProyecto,
    ResultadoRegistro,
    ResultadoTareas,
    ResumenAlumno,
    TipoInscripcion,
)
from core.normalizacion import normalizar
from exporters.curso import exportar_curso, nombre_sugerido
from importers.calificaciones_plataforma import leer_calificaciones

from . import tema
from .agrupar import agrupar_por_equipo, es_encabezado, iid_encabezado
from .dialogos_curso import DialogoAlumnoNuevo, DialogoElegirAlumno, DialogoExamen, DialogoExportar
from .dialogos_tareas import DialogoImportarTareas
from .formato import formatear_decimas, leer_decimas, titulo_legible
from .tabla import ESTILO, configurar_estilo

MAX_SUGERENCIAS = 6
ATAJOS_DECIMAS = (5, 10, 25)
MS_RESALTADO = 2500
MODOS = {"Participación": "participacion", "Examen": "examen", "Tareas": "tareas", "Proyecto": "proyecto"}
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
    # Evaluar (con «Formar equipos» apagado) y, con él encendido, armar los equipos del proyecto.
    "proyecto": (
        "Registrar proyecto", 150, "Calificación del proyecto", tema.COLOR_PROYECTO, tema.COLOR_PROYECTO_HOVER,
        "Escribe cuenta o nombre (o «equipo N» para todo el equipo) y la calificación del proyecto, y "
        "presiona Enter. «Formar equipos» arma los equipos.",
    ),
}
SIN_EXAMENES = "(sin exámenes)"

COLUMNAS = (
    ("numero", "No.", 55, "center"),
    ("cuenta", "Cuenta", 120, "center"),
    ("nombre", "Nombre", 320, "w"),
    ("total", "Décimas", 100, "e"),
    ("tareas", "Tareas", 90, "e"),
    ("proyecto", "Proyecto", 100, "e"),
    ("ultima", "Última", 110, "center"),
)
COLUMNA_EQUIPO = ("equipo", "Equipo", 100, "center")  # solo en el modo Proyecto


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
        # Último cambio de equipos: ("formado", número) o ("separado", {alumno_id: equipo}) para deshacer.
        self._ultima_equipo: tuple[str, object] | None = None
        # Última calificación de proyecto: (equipo o None, {alumno_id: calificación previa}) para deshacer.
        self._ultimo_proyecto: tuple[int | None, dict] | None = None

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
        # Solo en modo Proyecto (ocupa el lugar de +5/+10/+25): cambia el destino al equipo del alumno.
        self._boton_usar_equipo = ctk.CTkButton(
            fila, text="Usar equipo", width=130, height=38, command=self.usar_equipo, state="disabled",
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
        )
        self._boton_usar_equipo.grid(row=0, column=2, columnspan=len(ATAJOS_DECIMAS), padx=3)
        self._boton_usar_equipo.grid_remove()

        # Solo visible en modo Proyecto: herramientas de equipo (la tabla es el selector de alumnos).
        self._formando = False
        self._fila_equipos = ctk.CTkFrame(marco, fg_color="transparent")
        fila_formar = ctk.CTkFrame(self._fila_equipos, fg_color="transparent")
        fila_formar.pack(anchor="w")
        self._boton_formar = ctk.CTkButton(
            fila_formar, text="Formar equipos", width=150, height=34, command=self.alternar_formar,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
        )
        self._boton_formar.pack(side="left")
        self._etiqueta_seleccion = ctk.CTkLabel(fila_formar, text="", text_color=tema.COLOR_TEXTO_SUAVE)
        self._etiqueta_seleccion.pack(side="left", padx=14)
        # Solo formando: justo debajo del botón «Formar equipos», alineadas a la izquierda.
        self._acciones_equipo = ctk.CTkFrame(self._fila_equipos, fg_color="transparent")
        self._boton_crear_equipo = ctk.CTkButton(
            self._acciones_equipo, text="Crear equipo", width=210, height=34, command=self.crear_equipo,
            fg_color=tema.COLOR_PROYECTO, hover_color=tema.COLOR_PROYECTO_HOVER, state="disabled",
        )
        self._boton_crear_equipo.pack(side="left")
        self._boton_sacar_equipo = ctk.CTkButton(
            self._acciones_equipo, text="Sacar de equipo", width=170, height=34,
            command=self.sacar_de_equipo, state="disabled",
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
        )
        self._boton_sacar_equipo.pack(side="left", padx=(8, 0))

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
        self._tabla.bind("<<TreeviewSelect>>", self._al_seleccionar)
        self._tabla.bind("<Button-3>", self._al_clic_derecho)
        self._tabla.bind("<Button-1>", self._al_presionar_tabla)
        barra = ctk.CTkScrollbar(marco, command=self._tabla.yview)
        # Con varios exámenes las columnas pueden no caber: la tabla se desplaza horizontalmente.
        barra_h = ctk.CTkScrollbar(marco, orientation="horizontal", command=self._tabla.xview)
        self._tabla.configure(yscrollcommand=barra.set, xscrollcommand=barra_h.set)
        barra_h.pack(side="bottom", fill="x", padx=8, pady=(0, 4))
        self._tabla.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        barra.pack(side="right", fill="y", padx=(0, 4), pady=8)
        self._tabla.tag_configure("oyente", foreground=colores["suave"])
        # En ttk gana la etiqueta configurada primero: «reciente» va antes que los tonos de equipo
        # para que el resaltado de lo recién guardado se vea sobre ellos.
        self._tabla.tag_configure("reciente", background=colores["reciente"])
        for banda in (0, 1):  # equipos: encabezado fuerte y fila suave, dos tonos alternados
            self._tabla.tag_configure(f"enc{banda}", background=colores[f"enc{banda}"],
                                      font=tema.fuente(12, "bold"))
            self._tabla.tag_configure(f"fila{banda}", background=colores[f"fila{banda}"])

    # ====================== datos / tabla ======================
    def _aplicar_columnas(self) -> None:
        """Columnas fijas más una por examen («Examen - <nombre>»), antes de «Última»."""
        examenes = tuple(
            (f"examen_{e.id}", f"Examen - {e.nombre}", max(120, 7 * (len(e.nombre) + 9) + 40), "e")
            for e in self._examenes
        )
        fijas = COLUMNAS[:3] + ((COLUMNA_EQUIPO,) if self._modo == "proyecto" else ()) + COLUMNAS[3:-1]
        self._columnas = fijas + examenes + COLUMNAS[-1:]
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
            "proyecto": lambda f: f.proyecto,
            "equipo": lambda f: f.equipo or 0,
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
        filas = self._filtradas()
        if self._modo == "proyecto":
            self._insertar_agrupadas(filas)
        else:
            for f in filas:
                self._insertar_alumno(f)
        self._poner_encabezados()
        self._actualizar_resumen()

    def _insertar_alumno(self, f: ResumenAlumno, banda: int | None = None) -> None:
        valores = {
            "numero": self._numeros[f.alumno.id],
            "cuenta": f.alumno.num_cuenta or "—",
            "nombre": f.alumno.nombre_completo + ("   (oyente)" if f.tipo == TipoInscripcion.OYENTE else ""),
            "equipo": f"Equipo {f.equipo}" if f.equipo is not None else "",
            "total": formatear_decimas(f.total),
            "tareas": formatear_decimas(f.tareas),
            "proyecto": formatear_decimas(f.proyecto),
            "ultima": f.ultima_fecha.strftime("%d/%m/%Y") if f.ultima_fecha else "—",
            **{f"examen_{e.id}": formatear_decimas(f.calificaciones.get(e.id, 0.0)) for e in self._examenes},
        }
        etiquetas = ("oyente",) if f.tipo == TipoInscripcion.OYENTE else ()
        if banda is not None:
            etiquetas += (f"fila{banda}",)
        self._tabla.insert(
            "", "end", iid=str(f.alumno.id),
            values=tuple(valores[c[0]] for c in self._columnas), tags=etiquetas,
        )

    def _insertar_agrupadas(self, filas: list[ResumenAlumno]) -> None:
        """Modo Proyecto: una fila de encabezado por equipo y debajo sus miembros."""
        for grupo in agrupar_por_equipo(filas):
            if grupo.numero is not None:
                valores = {c[0]: "" for c in self._columnas}
                valores["nombre"] = grupo.titulo
                self._tabla.insert(
                    "", "end", iid=iid_encabezado(grupo.numero),
                    values=tuple(valores[c[0]] for c in self._columnas), tags=(f"enc{grupo.banda}",),
                )
            for f in grupo.filas:
                self._insertar_alumno(f, grupo.banda)

    def _al_seleccionar(self, _evento=None) -> None:
        """Los encabezados de equipo no son alumnos: nunca quedan seleccionados."""
        encabezados = [i for i in self._tabla.selection() if es_encabezado(i)]
        if encabezados:
            self._tabla.selection_remove(*encabezados)
        self._actualizar_barra()

    def _poner_encabezados(self) -> None:
        for clave, titulo, *_ in self._columnas:
            flecha = ""
            if clave == self._orden[0]:
                flecha = "  ▼" if self._orden[1] else "  ▲"
            self._tabla.heading(clave, text=titulo + flecha)

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
        if not iid or es_encabezado(iid) or self._tabla.identify_region(evento.x, evento.y) == "heading":
            return
        if self._formando:  # formando equipos el clic solo selecciona
            return
        fila = next((f for f in self._filas if str(f.alumno.id) == iid), None)
        if fila:
            self._elegir(fila.alumno)

    def _al_presionar_tabla(self, evento) -> str | None:
        """Formando equipos, un clic en un alumno lo suma o lo quita de la selección (sin Ctrl).

        Mayús y Ctrl conservan el comportamiento normal de la tabla (rango y alternar); el clic en
        el encabezado de una columna sigue ordenando. Fuera de ese modo no se interviene.
        """
        if not self._formando or evento.state & 0x5:
            return None
        if self._tabla.identify_region(evento.x, evento.y) == "heading":
            return None
        iid = self._tabla.identify_row(evento.y)
        if iid and not es_encabezado(iid):
            if iid in self._tabla.selection():
                self._tabla.selection_remove(iid)
            else:
                self._tabla.selection_add(iid)
        self._tabla.focus_set()
        return "break"

    def _al_doble_clic(self, evento) -> None:
        """Doble clic en una fila abre el historial de ese alumno."""
        if self._formando:  # formando equipos cada clic selecciona; el doble clic no debe abrir nada
            return
        iid = self._tabla.identify_row(evento.y)
        if iid and not es_encabezado(iid) and self._tabla.identify_region(evento.x, evento.y) != "heading":
            self._app.abrir_historial(self.curso.id, int(iid))

    def _ordenar_por(self, clave: str) -> None:
        descendente = (not self._orden[1]) if self._orden[0] == clave else (clave in ("total", "tareas", "proyecto", "ultima") or clave.startswith("examen_"))
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
            self._actualizar_usar_equipo()
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
        if self._modo in ("examen", "tareas", "proyecto"):
            self._cargar_calificacion_actual(alumno)
        self._actualizar_usar_equipo()
        self._entrada_decimas.focus_set()
        self._entrada_decimas.select_range(0, "end")

    def _cargar_calificacion_actual(self, alumno: Alumno) -> None:
        """En modo Examen, Tareas o Proyecto, elegir a un alumno trae su calificación para corregirla."""
        self._entrada_decimas.delete(0, "end")
        if self._modo == "tareas":
            actual = self._servicio.tareas_de(self.curso.id, alumno.id)
        elif self._modo == "proyecto":
            actual = self._servicio.proyecto_de(self.curso.id, alumno.id)
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
        if self._modo == "proyecto":
            self._guardar_proyecto()
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
        self._ultimo_proyecto = None
        self._ultima_equipo = None
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
        if self._ultimo_proyecto is not None:
            self._deshacer_proyecto()
            return
        if self._ultima_equipo is not None:
            self._deshacer_equipo()
            return
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
        era_proyecto = self._modo == "proyecto"
        self._modo = MODOS[valor]
        self._pendiente = None
        texto, ancho, placeholder, color, hover, ayuda = AJUSTES_MODO[self._modo]
        if self._modo == "proyecto":  # «Formar equipos» arriba; el registro solo evaluando
            self._fila_equipos.pack(fill="x", padx=16, pady=(6, 0))
            self._mostrar_registro(not self._formando)
        else:
            self._fila_equipos.pack_forget()
            if self._formando:
                self._formando = False
                self._aplicar_modo_formar()
            self._mostrar_registro(True)
        if (self._modo == "proyecto") != era_proyecto:  # cambian las columnas y el agrupado
            self._aplicar_columnas()
            self.recargar()  # también trae los equipos al día
        if self._modo == "examen":
            self._fila_examen.pack(fill="x", padx=16, pady=(6, 0), before=self._fila_registro)
            self._cargar_examenes()
        else:
            self._fila_examen.pack_forget()
        for boton in self._atajos:  # +5, +10 y +25 solo sirven para décimas
            boton.grid() if self._modo == "participacion" else boton.grid_remove()
        if self._modo == "proyecto":
            self._boton_usar_equipo.grid()
        else:
            self._boton_usar_equipo.grid_remove()
        self._entrada_alumno.configure(
            placeholder_text="Número de cuenta, nombre o «equipo N»…" if self._modo == "proyecto"
            else "Número de cuenta o nombre del alumno…"
        )
        self._actualizar_usar_equipo()
        self._entrada_decimas.delete(0, "end")
        self._entrada_decimas.configure(placeholder_text=placeholder)
        self._selector_modo.configure(selected_color=color, selected_hover_color=hover)
        self._boton_guardar.configure(text=texto, width=ancho, fg_color=color, hover_color=hover)
        self._info(ayuda)
        (self._tabla if self._formando else self._entrada_alumno).focus_set()

    def _mostrar_registro(self, visible: bool) -> None:
        """Muestra u oculta la fila del campo de registro. En «Proyecto» va debajo de «Formar equipos»."""
        if visible:
            if self._modo == "proyecto":  # siempre se recoloca: ya podía estar arriba de la fila de equipos
                self._fila_registro.pack(fill="x", padx=16, pady=(6, 12), after=self._fila_equipos)
            elif not self._fila_registro.winfo_manager():
                self._fila_registro.pack(fill="x", padx=16, pady=(6, 12))
        else:
            self._ocultar_sugerencias()
            self._fila_registro.pack_forget()
        if self._modo == "proyecto":  # sin el registro debajo, la fila de equipos cierra la tarjeta
            self._fila_equipos.pack_configure(pady=(6, 0) if visible else (6, 12))

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
        self._mostrar_aviso_reemplazo(f"{alumno.nombre_completo}  ·  {texto}")

    def _mostrar_aviso_reemplazo(self, texto: str) -> None:
        """Franja de advertencia con «Reemplazar» / «Cancelar» (el botón lleva el color del modo)."""
        self._mensaje.configure(text=f"⚠  {texto}", text_color=tema.COLOR_AVISO)
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
        if self._modo == "proyecto":
            self._confirmar_reemplazo_proyecto()
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
        self._ultimo_proyecto = None
        self._ultima_equipo = None
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
        """F2: recorre los modos (Participación → Examen → Tareas → Proyecto) sin soltar el teclado."""
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
        self._ultimo_proyecto = None
        self._ultima_equipo = None
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
        self._ultimo_proyecto = None
        self._ultima_equipo = None
        try:
            self._servicio.deshacer_importacion_tareas(self.curso.id, anteriores)
        except ErrorDominio as error:
            self._error(str(error))
            return
        self.recargar()
        self._info(f"Se deshizo la importación: {len(anteriores)} calificaciones de tareas restauradas.")
        self._entrada_alumno.focus_set()

    # ====================== calificación del proyecto ======================
    def _equipo_del_elegido(self) -> int | None:
        if self._elegido is None:
            return None
        fila = next((f for f in self._filas if f.alumno.id == self._elegido.id), None)
        return fila.equipo if fila else None

    def _actualizar_usar_equipo(self) -> None:
        numero = self._equipo_del_elegido() if self._modo == "proyecto" else None
        self._boton_usar_equipo.configure(
            state="normal" if numero is not None else "disabled",
            text="Usar equipo" if numero is None else f"Usar equipo {numero}",
        )

    def usar_equipo(self) -> None:
        """Cambia el destino de la calificación al equipo del alumno cargado («equipo N»)."""
        numero = self._equipo_del_elegido()
        if numero is None:
            return
        self._elegido = None
        self._entrada_alumno.delete(0, "end")
        self._entrada_alumno.insert(0, f"equipo {numero}")
        self._ocultar_sugerencias()
        self._actualizar_usar_equipo()
        self._entrada_decimas.focus_set()
        self._entrada_decimas.select_range(0, "end")

    def _guardar_proyecto(self) -> None:
        consulta = self._entrada_alumno.get().strip()
        if not consulta:
            self._error("Escribe un número de cuenta, un nombre o «equipo N».")
            self._entrada_alumno.focus_set()
            return
        try:
            puntos = leer_decimas(self._entrada_decimas.get())
        except ValueError:
            self._error("La calificación del proyecto debe ser un número (por ejemplo 8.5 o 85).")
            self._entrada_decimas.focus_set()
            return

        try:
            if self._elegido:
                resultado = self._servicio.registrar_proyecto_para_alumno(
                    self.curso.id, self._elegido.id, puntos
                )
            else:
                resultado = self._servicio.registrar_proyecto(self.curso.id, consulta, puntos)
        except ErrorDominio as error:
            self._error(str(error))
            return

        if resultado.estado == EstadoRegistro.GUARDADO:
            self._proyecto_guardado(resultado)
        elif resultado.estado == EstadoRegistro.CONFIRMAR_REEMPLAZO:
            self._advertir_proyecto(resultado)
        elif resultado.estado == EstadoRegistro.AMBIGUO:
            alumno = DialogoElegirAlumno(self, consulta, resultado.candidatos, self._tipos).mostrar()
            if alumno:
                self._elegido = alumno
                self._guardar_proyecto()
            else:
                self._info("Registro cancelado: había varias coincidencias.")
        else:
            self._ofrecer_alta_proyecto(consulta, puntos, resultado)

    def _advertir_proyecto(self, resultado: ResultadoProyecto) -> None:
        """Hay notas distintas que se reemplazarían: avisa y espera confirmación (nada se guardó)."""
        nueva = formatear_decimas(resultado.puntos)
        if resultado.equipo is not None:
            destino = resultado.equipo
            total, n = len(resultado.alumnos), resultado.con_otra
            texto = (f"Equipo {destino}  ·  {n} de {total} miembros ya "
                     f"{'tiene' if n == 1 else 'tienen'} calificación; se cambiarán a {nueva}.")
        else:
            destino = resultado.alumnos[0]
            anterior = resultado.anteriores[destino.id]
            texto = (f"{destino.nombre_completo}  ·  Ya tiene {formatear_decimas(anterior.puntos)} "
                     f"en el proyecto; se cambiará a {nueva}.")
        self._pendiente = (destino, resultado.puntos)
        self._mostrar_aviso_reemplazo(texto)

    def _confirmar_reemplazo_proyecto(self) -> None:
        destino, puntos = self._pendiente
        self._pendiente = None
        try:
            if isinstance(destino, int):
                resultado = self._servicio.registrar_proyecto_equipo(
                    self.curso.id, destino, puntos, reemplazar=True
                )
            else:
                resultado = self._servicio.registrar_proyecto_para_alumno(
                    self.curso.id, destino.id, puntos, reemplazar=True
                )
        except ErrorDominio as error:
            self._error(str(error))
            return
        self._proyecto_guardado(resultado)

    def _ofrecer_alta_proyecto(self, consulta: str, puntos: float, resultado: ResultadoProyecto) -> None:
        def crear_y_calificar(datos: dict) -> ResultadoProyecto:
            if datos["alumno_id"]:
                self._servicio.inscribir_alumno_existente(self.curso.id, datos["alumno_id"], datos["tipo"])
                alumno_id = datos["alumno_id"]
            else:
                alumno_id = self._servicio.crear_alumno_en_curso(
                    self.curso.id, datos["nombre"], datos["tipo"], datos["cuenta"]
                ).id
            return self._servicio.registrar_proyecto_para_alumno(self.curso.id, alumno_id, puntos)

        creado = DialogoAlumnoNuevo(
            self, crear_y_calificar, consulta, None, resultado.candidatos,
            resumen_registro=f"proyecto: {formatear_decimas(puntos)}",
        ).mostrar()
        if creado:
            self._proyecto_guardado(creado, alumno_nuevo=True)
        else:
            self._info(f"Registro cancelado: «{consulta}» no está en este curso.")
            self._entrada_alumno.focus_set()

    def _proyecto_guardado(self, resultado: ResultadoProyecto, alumno_nuevo: bool = False) -> None:
        nueva = formatear_decimas(resultado.puntos)
        if resultado.equipo is not None:
            k = len(resultado.alumnos)
            texto = f"Equipo {resultado.equipo}  ·  Proyecto: {nueva} ({k} alumno{'s' if k != 1 else ''})"
        else:
            alumno = resultado.alumnos[0]
            anterior = resultado.anteriores.get(alumno.id)
            antes = f"  (antes {formatear_decimas(anterior.puntos)})" if anterior else ""
            nuevo = "  (alumno agregado)" if alumno_nuevo else ""
            texto = f"{alumno.nombre_completo}  ·  Proyecto: {nueva}{antes}{nuevo}"
        self._exito(texto, deshacible=True)
        self._ultimo_registro = self._ultima_calificacion = self._ultima_tareas = None
        self._ultima_importacion = None
        self._ultima_equipo = None
        self._ultimo_proyecto = (resultado.equipo, resultado.anteriores)
        self._pendiente = None
        self._elegido = None
        self._entrada_alumno.delete(0, "end")
        self._entrada_decimas.delete(0, "end")
        self._ocultar_sugerencias()
        self._actualizar_usar_equipo()
        self.recargar()
        if len(resultado.alumnos) == 1:
            self._resaltar(resultado.alumnos[0].id)
        else:
            self._resaltar_miembros([a.id for a in resultado.alumnos])
        self._entrada_alumno.focus_set()

    def _deshacer_proyecto(self) -> None:
        equipo, anteriores = self._ultimo_proyecto
        self._ultimo_proyecto = None
        try:
            self._servicio.deshacer_proyecto(self.curso.id, anteriores)
        except ErrorDominio as error:
            self._error(str(error))
            return
        self.recargar()
        if equipo is not None:
            self._info(f"Se deshizo la calificación del proyecto del equipo {equipo} ({len(anteriores)} alumnos).")
        else:
            alumno = next((f.alumno for f in self._filas if f.alumno.id in anteriores), None)
            self._info(
                "Se deshizo la calificación del proyecto"
                + (f" de {alumno.nombre_completo}." if alumno else ".")
            )
        self._entrada_alumno.focus_set()

    # ====================== equipos de proyecto ======================
    def alternar_formar(self) -> None:
        """Activa o desactiva «Formar equipos»: con él activo la tabla permite elegir varios alumnos."""
        self._formando = not self._formando
        self._aplicar_modo_formar()
        self._info(
            "Haz clic en los alumnos del equipo (otro clic los quita) y pulsa «Crear equipo»."
            if self._formando else AJUSTES_MODO["proyecto"][5]
        )

    def _aplicar_modo_formar(self) -> None:
        seleccion = self._tabla.selection()
        if seleccion:
            self._tabla.selection_remove(*seleccion)
        self._tabla.configure(selectmode="extended" if self._formando else "browse")
        if self._modo == "proyecto":
            self._mostrar_registro(not self._formando)
        if self._formando:
            self._boton_formar.configure(
                fg_color=tema.COLOR_PROYECTO, hover_color=tema.COLOR_PROYECTO_HOVER,
                text_color=ctk.ThemeManager.theme["CTkButton"]["text_color"],
            )
            self._acciones_equipo.pack(anchor="w", pady=(8, 0))
        else:
            self._boton_formar.configure(
                fg_color="transparent", hover_color=tema.COLOR_NAV_ACTIVO, text_color=tema.COLOR_TEXTO,
            )
            self._acciones_equipo.pack_forget()
        self._actualizar_barra()

    def _seleccionados(self) -> list[int]:
        return [int(i) for i in self._tabla.selection() if not es_encabezado(i)]

    def _elegidos_con_equipo(self) -> tuple[list[int], list[int]]:
        """(alumnos seleccionados que tienen equipo, números de esos equipos). Los demás se ignoran."""
        equipos = {f.alumno.id: f.equipo for f in self._filas if f.equipo is not None}
        elegidos = [i for i in self._seleccionados() if i in equipos]
        return elegidos, sorted({equipos[i] for i in elegidos})

    def sacar_de_equipo(self) -> None:
        """Botón «Sacar de equipo»: lo mismo que «Sacar del equipo» del clic derecho, sobre la selección."""
        elegidos, _numeros = self._elegidos_con_equipo()
        if elegidos:
            self.separar(elegidos)

    def _actualizar_barra(self) -> None:
        n = len(self._seleccionados()) if self._formando else 0
        if not self._formando:
            self._etiqueta_seleccion.configure(text="")
        else:
            self._etiqueta_seleccion.configure(
                text="Ninguno seleccionado" if n == 0 else f"{n} seleccionado{'s' if n != 1 else ''}"
            )
        self._boton_crear_equipo.configure(
            state="normal" if n else "disabled",
            text="Crear equipo" if n == 0 else f"Crear equipo con {n} alumno{'s' if n != 1 else ''}",
        )
        con_equipo = len(self._elegidos_con_equipo()[0]) if self._formando else 0
        self._boton_sacar_equipo.configure(
            state="normal" if con_equipo else "disabled",
            text="Sacar de equipo" if con_equipo == 0 else f"Sacar de equipo ({con_equipo})",
        )

    def crear_equipo(self) -> None:
        ids = self._seleccionados()
        if not ids:
            return
        try:
            resultado = self._servicio.formar_equipo(self.curso.id, ids)
        except ErrorDominio as error:
            self._error(str(error))
            return
        if resultado.estado == EstadoEquipo.YA_TIENEN_EQUIPO:
            quienes = ", ".join(f"{a.nombre_completo} (equipo {n})" for a, n in resultado.con_equipo)
            self._error(f"Ya tienen equipo: {quienes}. Sácalos primero (botón «Sacar de equipo» o clic derecho).")
            return
        self._ultimo_registro = self._ultima_calificacion = self._ultima_tareas = None
        self._ultima_importacion = None
        self._ultimo_proyecto = None
        self._ultima_equipo = ("formado", resultado.numero)
        self.recargar()
        self._resaltar_miembros([a.id for a in resultado.miembros])
        k = len(resultado.miembros)
        self._exito(
            f"Equipo {resultado.numero} formado con {k} alumno{'s' if k != 1 else ''}.", deshacible=True
        )
        self._actualizar_barra()

    def _resaltar_miembros(self, alumno_ids: list[int]) -> None:
        iids = [str(i) for i in alumno_ids if self._tabla.exists(str(i))]
        for iid in iids:
            self._tabla.item(iid, tags=tuple(self._tabla.item(iid, "tags")) + ("reciente",))
        if iids:
            self._tabla.see(iids[0])
        if self._tarea_resaltado:
            self.after_cancel(self._tarea_resaltado)
        self._tarea_resaltado = self.after(MS_RESALTADO, lambda: self._quitar_resaltados(iids))

    def _quitar_resaltados(self, iids: list[str]) -> None:
        self._tarea_resaltado = None
        if not self.winfo_exists():
            return
        for iid in iids:
            if self._tabla.exists(iid):
                self._tabla.item(iid, tags=tuple(t for t in self._tabla.item(iid, "tags") if t != "reciente"))

    def _menu_equipos(self, evento) -> tk.Menu | None:
        """Menú del clic derecho sobre un alumno. None si no hay nada que ofrecer.

        Solo con «Formar equipos» activo. Un clic derecho sobre una fila que no está seleccionada
        la selecciona sola; sobre una seleccionada conserva la selección. Ofrece:
        - «Sacar del equipo N»: para los seleccionados que ya tienen equipo;
        - «Agregar a ▸» con los equipos ya formados: para los seleccionados que no tienen equipo
          (a quien ya tiene equipo no se le ofrece: primero hay que sacarlo).
        """
        if not self._formando:
            return None
        iid = self._tabla.identify_row(evento.y)
        if not iid or es_encabezado(iid) or self._tabla.identify_region(evento.x, evento.y) == "heading":
            return None
        if iid not in self._tabla.selection():
            self._tabla.selection_set(iid)
        elegidos, numeros = self._elegidos_con_equipo()
        sin_equipo = [i for i in self._seleccionados() if i not in elegidos]
        menu = tk.Menu(self, tearoff=0)
        if elegidos:
            n = len(elegidos)
            if len(numeros) > 1:
                texto = f"Sacar de sus equipos ({n} alumnos)"
            else:
                texto = f"Sacar del equipo {numeros[0]}" + (f" ({n} alumnos)" if n > 1 else "")
            menu.add_command(label=texto, command=lambda: self.separar(elegidos))
        equipos = self._servicio.equipos_del_curso(self.curso.id)
        if sin_equipo and equipos:
            submenu = tk.Menu(menu, tearoff=0)
            for equipo in equipos:
                k = len(equipo.miembros)
                submenu.add_command(
                    label=f"Equipo {equipo.numero} ({k} alumno{'s' if k != 1 else ''})",
                    command=lambda numero=equipo.numero: self.agregar_a(numero, sin_equipo),
                )
            m = len(sin_equipo)
            menu.add_cascade(label="Agregar a" + (f" ({m} alumnos)" if m > 1 else ""), menu=submenu)
        return menu if menu.index("end") is not None else None

    def _al_clic_derecho(self, evento) -> str:
        menu = self._menu_equipos(evento)
        if menu is not None:
            try:
                menu.tk_popup(evento.x_root, evento.y_root)
            finally:
                menu.grab_release()
        return "break"

    def separar(self, alumno_ids: list[int]) -> None:
        """Saca a los alumnos de su equipo (se puede deshacer)."""
        try:
            separados = self._servicio.separar_de_equipo(self.curso.id, alumno_ids)
        except ErrorDominio as error:
            self._error(str(error))
            return
        if not separados:
            return
        self._ultimo_registro = self._ultima_calificacion = self._ultima_tareas = None
        self._ultima_importacion = None
        self._ultimo_proyecto = None
        self._ultima_equipo = ("separado", separados)
        self.recargar()
        self._resaltar_miembros(list(separados))
        n = len(separados)
        numeros = sorted(set(separados.values()))
        de = f"del equipo {numeros[0]}" if len(numeros) == 1 else "de sus equipos"
        self._exito(f"Se sacó a {n} alumno{'s' if n != 1 else ''} {de}.", deshacible=True)
        self._actualizar_barra()

    def agregar_a(self, numero: int, alumno_ids: list[int]) -> None:
        """Suma alumnos sin equipo a un equipo ya formado (se puede deshacer)."""
        try:
            resultado = self._servicio.agregar_a_equipo(self.curso.id, numero, alumno_ids)
        except ErrorDominio as error:
            self._error(str(error))
            return
        if resultado.estado == EstadoEquipo.YA_TIENEN_EQUIPO:
            quienes = ", ".join(f"{a.nombre_completo} (equipo {n})" for a, n in resultado.con_equipo)
            self._error(f"Ya tienen equipo: {quienes}. Sácalos primero.")
            return
        ids = [a.id for a in resultado.miembros]
        self._ultimo_registro = self._ultima_calificacion = self._ultima_tareas = None
        self._ultima_importacion = None
        self._ultimo_proyecto = None
        self._ultima_equipo = ("agregado", (numero, ids))
        self.recargar()
        self._resaltar_miembros(ids)
        k = len(ids)
        self._exito(
            f"{k} alumno{'s' if k != 1 else ''} agregado{'s' if k != 1 else ''} al equipo {numero}.",
            deshacible=True,
        )
        self._actualizar_barra()

    def _deshacer_equipo(self) -> None:
        tipo, dato = self._ultima_equipo
        self._ultima_equipo = None
        try:
            if tipo == "formado":
                self._servicio.deshacer_equipo(self.curso.id, dato)
                texto = f"Se deshizo el equipo {dato}: sus alumnos quedaron sin equipo."
            elif tipo == "agregado":
                numero, ids = dato
                self._servicio.separar_de_equipo(self.curso.id, ids)
                texto = f"Se deshizo: {len(ids)} alumnos salieron del equipo {numero}."
            else:
                self._servicio.deshacer_separacion(self.curso.id, dato)
                texto = f"Se deshizo: {len(dato)} alumnos volvieron a su equipo."
        except ErrorDominio as error:
            self._error(str(error))
            return
        self.recargar()
        self._info(texto)

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
        self._ultima_equipo = None
        self._ultimo_proyecto = None
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
