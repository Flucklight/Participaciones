"""Pantalla Curso: registro rápido de décimas y tabla de alumnos."""

from __future__ import annotations

from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from core.errores import ErrorDominio
from core.models import (
    Alumno,
    EstadoRegistro,
    ResultadoRegistro,
    ResumenAlumno,
    TipoInscripcion,
)
from core.normalizacion import normalizar
from exporters.curso import exportar_curso, nombre_sugerido

from . import tema
from .dialogos_curso import DialogoAlumnoNuevo, DialogoElegirAlumno, DialogoExportar
from .formato import formatear_decimas, leer_decimas, titulo_legible
from .tabla import ESTILO, configurar_estilo

MAX_SUGERENCIAS = 6
ATAJOS_DECIMAS = (5, 10, 25)
MS_RESALTADO = 2500

COLUMNAS = (
    ("numero", "No.", 55, "center"),
    ("cuenta", "Cuenta", 120, "center"),
    ("nombre", "Nombre", 420, "w"),
    ("total", "Décimas", 100, "e"),
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
            text_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_NAV_ACTIVO,
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
        for texto, comando in (("⬇  Exportar", self.exportar), ("＋  Agregar alumno", self.agregar_alumno)):
            ctk.CTkButton(
                titulo, text=texto, height=34, command=comando,
                fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
                text_color=("gray20", "gray90"), hover_color=tema.COLOR_NAV_ACTIVO,
            ).pack(side="right", anchor="s", padx=(8, 0))

    def _construir_registro(self) -> None:
        marco = ctk.CTkFrame(self, corner_radius=12, fg_color=tema.COLOR_TARJETA,
                             border_width=1, border_color=tema.COLOR_BORDE)
        marco.pack(fill="x", padx=24, pady=(14, 0))
        ctk.CTkLabel(marco, text="Registro rápido", font=tema.fuente(13, "bold"), anchor="w"
                     ).pack(fill="x", padx=16, pady=(10, 0))

        fila = ctk.CTkFrame(marco, fg_color="transparent")
        fila.pack(fill="x", padx=16, pady=(6, 12))
        fila.grid_columnconfigure(0, weight=1)

        self._entrada_alumno = ctk.CTkEntry(
            fila, height=38, placeholder_text="Número de cuenta o nombre del alumno…"
        )
        self._entrada_alumno.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._entrada_alumno.bind("<KeyRelease>", self._al_escribir_alumno)
        self._entrada_alumno.bind("<Down>", lambda _e: self._mover_sugerencia(1))
        self._entrada_alumno.bind("<Up>", lambda _e: self._mover_sugerencia(-1))
        self._entrada_alumno.bind("<Return>", self._enter_alumno)
        self._entrada_alumno.bind("<Escape>", lambda _e: self._ocultar_sugerencias())

        self._entrada_decimas = ctk.CTkEntry(fila, height=38, width=110, placeholder_text="Décimas")
        self._entrada_decimas.grid(row=0, column=1, padx=(0, 6))
        self._entrada_decimas.bind("<Return>", lambda _e: self.guardar())

        for i, valor in enumerate(ATAJOS_DECIMAS):
            ctk.CTkButton(
                fila, text=f"+{valor}", width=44, height=38, fg_color="transparent",
                border_width=1, border_color=tema.COLOR_BORDE, text_color=("gray20", "gray90"),
                hover_color=tema.COLOR_NAV_ACTIVO,
                command=lambda v=valor: self._poner_decimas(v),
            ).grid(row=0, column=2 + i, padx=3)
        ctk.CTkButton(
            fila, text="Guardar", width=100, height=38, command=self.guardar,
            fg_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_ACENTO_HOVER,
        ).grid(row=0, column=2 + len(ATAJOS_DECIMAS), padx=(10, 0))

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
            text_color=("gray20", "gray90"), hover_color=tema.COLOR_NAV_ACTIVO,
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
        for clave, titulo, ancho, alineacion in COLUMNAS:
            self._tabla.heading(clave, text=titulo, anchor=alineacion,
                                command=lambda c=clave: self._ordenar_por(c))
            self._tabla.column(clave, width=ancho, anchor=alineacion,
                               stretch=(clave == "nombre"), minwidth=50)
        self._tabla.bind("<ButtonRelease-1>", self._al_clic_tabla)
        self._tabla.bind("<Double-1>", self._al_doble_clic)
        barra = ctk.CTkScrollbar(marco, command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=barra.set)
        self._tabla.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        barra.pack(side="right", fill="y", padx=(0, 4), pady=8)
        self._tabla.tag_configure("oyente", foreground=colores["suave"])
        self._tabla.tag_configure("reciente", background=colores["reciente"])

    # ====================== datos / tabla ======================
    def recargar(self) -> None:
        self._filas = self._servicio.resumen_curso(self.curso.id)
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
            "ultima": lambda f: (f.ultima_fecha is None, f.ultima_fecha or 0),
        }
        return sorted(filas, key=llaves[clave], reverse=descendente)

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
                    f.ultima_fecha.strftime("%d/%m/%Y") if f.ultima_fecha else "—",
                ),
                tags=("oyente",) if f.tipo == TipoInscripcion.OYENTE else (),
            )
        for clave, titulo, *_ in COLUMNAS:
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
        descendente = (not self._orden[1]) if self._orden[0] == clave else (clave in ("total", "ultima"))
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
    def _info(self, texto: str) -> None:
        self._mensaje.configure(text=texto, text_color=tema.COLOR_TEXTO_SUAVE)
        self._boton_deshacer.pack_forget()

    def _error(self, texto: str) -> None:
        self._mensaje.configure(text="⚠  " + texto, text_color=tema.COLOR_PELIGRO)
        self._boton_deshacer.pack_forget()

    def _exito(self, texto: str, deshacible: bool) -> None:
        self._mensaje.configure(text="✓  " + texto, text_color=tema.COLOR_EXITO)
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
                text_color=("gray10", "gray95"), hover_color=tema.COLOR_NAV_ACTIVO,
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
        self._entrada_decimas.focus_set()
        self._entrada_decimas.select_range(0, "end")

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
