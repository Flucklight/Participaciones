"""Pantalla Cursos: barra de acciones y cards de los cursos."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.errores import ErrorDominio
from core.models import Curso
from core.normalizacion import normalizar
from importers.lista_aragon import leer_lista

from . import tema
from .formato import titulo_legible
from .dialogos import DialogoCurso, DialogoEliminarCurso, DialogoImportacion

ANCHO_CARD = 290
ALTO_CARD = 170


class VistaCursos(ctk.CTkFrame):
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self._app = app
        self._servicio = app.servicio
        self._seleccionado: int | None = None
        self._tarjetas: dict[int, ctk.CTkFrame] = {}
        self._cursos: list[Curso] = []
        self._columnas = 0
        self._redibujo = None

        self._construir_barra()
        self._zona = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._zona.pack(fill="both", expand=True, padx=(24, 12), pady=(0, 16))
        self._zona.bind("<Configure>", self._al_cambiar_tamano)
        self._vacio = ctk.CTkLabel(
            self._zona, text_color=tema.COLOR_TEXTO_SUAVE, font=tema.fuente(14), justify="center"
        )
        self.recargar()

    # ---------- construcción ----------
    def _construir_barra(self) -> None:
        ctk.CTkLabel(self, text="Cursos", font=tema.fuente(26, "bold"), anchor="w").pack(
            fill="x", padx=24, pady=(22, 4)
        )
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=24, pady=(8, 14))

        ctk.CTkButton(barra, text="＋  Crear", width=100, height=36, command=self.crear,
                      fg_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_ACENTO_HOVER
                      ).pack(side="left")
        ctk.CTkButton(barra, text="⬆  Importar lista", width=140, height=36, command=self.importar,
                      fg_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_ACENTO_HOVER
                      ).pack(side="left", padx=8)
        self._boton_eliminar = ctk.CTkButton(
            barra, text="🗑  Eliminar", width=110, height=36, command=self.eliminar_seleccionado,
            fg_color=tema.COLOR_PELIGRO, hover_color=tema.COLOR_PELIGRO_HOVER, state="disabled",
        )
        self._boton_eliminar.pack(side="left")

        self._ver_archivados = ctk.CTkCheckBox(
            barra, text="Mostrar archivados", command=self.recargar,
            checkbox_width=20, checkbox_height=20,
        )
        self._ver_archivados.pack(side="right")
        self._buscar = ctk.CTkEntry(barra, placeholder_text="🔍  Buscar curso…", width=220, height=36)
        self._buscar.pack(side="right", padx=16)
        self._buscar.bind("<KeyRelease>", lambda _e: self._dibujar())

    # ---------- datos ----------
    def recargar(self) -> None:
        self._cursos = self._servicio.listar_cursos(
            incluir_archivados=bool(self._ver_archivados.get())
        )
        if self._seleccionado not in {c.id for c in self._cursos}:
            self._seleccionado = None
        self._dibujar()

    def _filtrados(self) -> list[Curso]:
        consulta = normalizar(self._buscar.get())
        if not consulta:
            return self._cursos
        tokens = consulta.split()
        return [
            c for c in self._cursos
            if all(t in normalizar(f"{c.materia} {c.grupo} {c.ciclo} {c.carrera}") for t in tokens)
        ]

    # ---------- dibujo ----------
    def _al_cambiar_tamano(self, _evento=None) -> None:
        if self._redibujo:
            self.after_cancel(self._redibujo)
        self._redibujo = self.after(120, self._reacomodar)

    def _reacomodar(self) -> None:
        self._redibujo = None
        columnas = max(1, (self._zona.winfo_width() - 8) // (ANCHO_CARD + 16))
        if columnas != self._columnas and self._tarjetas:
            self._dibujar()

    def _dibujar(self) -> None:
        for tarjeta in self._tarjetas.values():
            tarjeta.destroy()
        self._tarjetas.clear()
        self._vacio.pack_forget()
        for c in range(12):
            self._zona.grid_columnconfigure(c, weight=0)

        cursos = self._filtrados()
        if not cursos:
            hay_cursos = bool(self._cursos)
            self._vacio.configure(
                text=("Ningún curso coincide con la búsqueda." if hay_cursos else
                      "Aún no tienes cursos.\nCrea uno o importa una lista de inscripción.")
            )
            self._vacio.pack(pady=80)
            self._actualizar_botones()
            return

        self._columnas = max(1, (self._zona.winfo_width() - 8) // (ANCHO_CARD + 16))
        for i, curso in enumerate(cursos):
            tarjeta = self._crear_card(curso)
            tarjeta.grid(row=i // self._columnas, column=i % self._columnas,
                         padx=8, pady=8, sticky="nw")
            self._tarjetas[curso.id] = tarjeta
        self._pintar_seleccion()
        self._actualizar_botones()

    def _crear_card(self, curso: Curso) -> ctk.CTkFrame:
        tarjeta = ctk.CTkFrame(
            self._zona, width=ANCHO_CARD, height=ALTO_CARD, corner_radius=12,
            fg_color=tema.COLOR_TARJETA, border_width=2, border_color=tema.COLOR_BORDE,
        )
        tarjeta.grid_propagate(False)
        tarjeta.pack_propagate(False)

        encabezado = ctk.CTkFrame(tarjeta, fg_color="transparent")
        encabezado.pack(fill="x", padx=14, pady=(12, 0))
        titulo = ctk.CTkLabel(
            encabezado, text=titulo_legible(curso.materia), font=tema.fuente(15, "bold"),
            wraplength=ANCHO_CARD - 70, justify="left", anchor="nw",
        )
        titulo.pack(side="left", fill="x", expand=True, anchor="n")
        menu = ctk.CTkButton(
            encabezado, text="⋯", width=30, height=28, fg_color="transparent",
            text_color=("gray20", "gray90"), hover_color=tema.COLOR_NAV_ACTIVO,
            font=tema.fuente(16, "bold"),
        )
        menu.configure(command=lambda c=curso, b=menu: self._abrir_menu(c, b))
        menu.pack(side="right", anchor="n")

        datos = [f"Grupo {curso.grupo}", f"Semestre {curso.ciclo}"]
        if curso.carrera:
            datos.append(titulo_legible(curso.carrera))
        detalle = ctk.CTkLabel(
            tarjeta, text="\n".join(datos), justify="left", anchor="w",
            text_color=tema.COLOR_TEXTO_SUAVE, font=tema.fuente(12),
        )
        detalle.pack(fill="x", padx=14, pady=(6, 0))

        pie = ctk.CTkFrame(tarjeta, fg_color="transparent")
        pie.pack(side="bottom", fill="x", padx=14, pady=(0, 12))
        alumnos = self._servicio.contar_alumnos(curso.id)
        ctk.CTkLabel(pie, text=f"{alumnos} alumnos", font=tema.fuente(12, "bold"),
                     text_color=tema.COLOR_ACENTO).pack(side="left")
        if curso.archivado:
            ctk.CTkLabel(pie, text="ARCHIVADO", font=tema.fuente(10, "bold"), corner_radius=6,
                         fg_color=tema.COLOR_BORDE, text_color=tema.COLOR_TEXTO_SUAVE,
                         padx=8).pack(side="right")
        else:
            ctk.CTkButton(
                pie, text="Abrir", width=70, height=26, font=tema.fuente(12),
                command=lambda c=curso: self._app.abrir_curso(c.id),
                fg_color=tema.COLOR_ACENTO, hover_color=tema.COLOR_ACENTO_HOVER,
            ).pack(side="right")

        for widget in (tarjeta, encabezado, titulo, detalle, pie):
            widget.bind("<Button-1>", lambda _e, c=curso: self._seleccionar(c.id))
            widget.bind("<Double-Button-1>", lambda _e, c=curso: self._app.abrir_curso(c.id))
            widget.bind("<Button-3>", lambda e, c=curso: self._menu_en(c, e.x_root, e.y_root))
        return tarjeta

    # ---------- selección ----------
    def _seleccionar(self, curso_id: int) -> None:
        self._seleccionado = curso_id
        self._pintar_seleccion()
        self._actualizar_botones()

    def _pintar_seleccion(self) -> None:
        for curso_id, tarjeta in self._tarjetas.items():
            tarjeta.configure(
                border_color=tema.COLOR_ACENTO if curso_id == self._seleccionado
                else tema.COLOR_BORDE
            )

    def _actualizar_botones(self) -> None:
        self._boton_eliminar.configure(
            state="normal" if self._seleccionado in self._tarjetas else "disabled"
        )

    def _curso(self, curso_id: int) -> Curso:
        return next(c for c in self._cursos if c.id == curso_id)

    # ---------- menú contextual ----------
    def _abrir_menu(self, curso: Curso, boton: ctk.CTkButton) -> None:
        self._seleccionar(curso.id)
        self._menu_en(curso, boton.winfo_rootx(), boton.winfo_rooty() + boton.winfo_height())

    def _menu_en(self, curso: Curso, x: int, y: int) -> None:
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Abrir", command=lambda: self._app.abrir_curso(curso.id))
        menu.add_command(label="Editar…", command=lambda: self.editar(curso))
        menu.add_command(
            label="Restaurar" if curso.archivado else "Archivar",
            command=lambda: self.archivar(curso),
        )
        menu.add_separator()
        menu.add_command(label="Eliminar…", command=lambda: self.eliminar(curso))
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    # ---------- acciones ----------
    def crear(self) -> None:
        def guardar(d: dict) -> Curso:
            return self._servicio.crear_curso(d["ciclo"], d["materia"], d["grupo"], d["carrera"])

        curso = DialogoCurso(self, guardar).mostrar()
        if curso:
            self._seleccionado = curso.id
            self.recargar()

    def editar(self, curso: Curso) -> None:
        def guardar(d: dict) -> Curso:
            return self._servicio.editar_curso(
                curso.id, d["ciclo"], d["materia"], d["grupo"], d["carrera"]
            )

        if DialogoCurso(self, guardar, curso).mostrar():
            self.recargar()

    def archivar(self, curso: Curso) -> None:
        self._servicio.archivar_curso(curso.id, not curso.archivado)
        self.recargar()

    def eliminar_seleccionado(self) -> None:
        if self._seleccionado in self._tarjetas:
            self.eliminar(self._curso(self._seleccionado))

    def eliminar(self, curso: Curso) -> None:
        alumnos, participaciones = self._servicio.resumen_eliminacion(curso.id)
        if DialogoEliminarCurso(self, curso, alumnos, participaciones).mostrar():
            try:
                self._servicio.eliminar_curso(curso.id)
            except ErrorDominio as error:
                messagebox.showerror("No se pudo eliminar", str(error), parent=self)
            self.recargar()

    def importar(self) -> None:
        ruta = filedialog.askopenfilename(
            parent=self, title="Selecciona la lista de inscripción",
            filetypes=[("Excel", "*.xlsx"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        try:
            lista = leer_lista(ruta)
            vista = self._servicio.previsualizar_importacion(lista)
        except ErrorDominio as error:
            messagebox.showerror("No se pudo leer la lista", str(error), parent=self)
            return
        vinculos = DialogoImportacion(self, lista, vista).mostrar()
        if vinculos is None:
            return
        try:
            resultado = self._servicio.importar_lista(lista, vinculos)
        except ErrorDominio as error:
            messagebox.showerror("No se pudo importar", str(error), parent=self)
            return
        self._seleccionado = resultado.curso.id
        self.recargar()
        messagebox.showinfo(
            "Importación completa",
            f"{'Curso creado' if resultado.curso_creado else 'Curso actualizado'}: "
            f"{resultado.curso.titulo}\n\n"
            f"• Alumnos nuevos: {resultado.alumnos_creados}\n"
            f"• Inscripciones nuevas: {resultado.inscripciones_nuevas}\n"
            f"• Oyentes vinculados: {resultado.vinculados}",
            parent=self,
        )
