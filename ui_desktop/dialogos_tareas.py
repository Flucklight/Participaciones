"""Diálogo de importación de tareas: elegir columna, revisar la vista previa y confirmar dudosas."""

from __future__ import annotations

from tkinter import ttk
from typing import Callable

import customtkinter as ctk

from core.models import ArchivoCalificaciones, Curso, EstadoLinea, LineaImportacion, VistaPreviaTareas

from . import tema
from .dialogos import Dialogo
from .formato import formatear_decimas
from .tabla import ESTILO, configurar_estilo

MUESTRA = 5  # valores de ejemplo junto al selector de columna

COLUMNAS = (
    ("estado", "Estado", 80, "w"),
    ("archivo", "Alumno en el archivo", 240, "w"),
    ("antes", "Antes", 76, "e"),
    ("despues", "Después", 90, "e"),
    ("detalle", "Detalle", 340, "w"),
)


def _numero(valor: float | None) -> str:
    return "—" if valor is None else formatear_decimas(valor)


class DialogoImportarTareas(Dialogo):
    """Devuelve {"clave": columna elegida, "confirmadas": ids de alumno de las dudosas marcadas}
    al aplicar, o None si se cancela. No guarda nada: eso lo hace quien lo abre."""

    def __init__(
        self,
        master,
        curso: Curso,
        nombre_archivo: str,
        archivo: ArchivoCalificaciones,
        previsualizar: Callable[[str], VistaPreviaTareas],
    ) -> None:
        super().__init__(master, "Importar tareas", ancho=900)
        self._archivo = archivo
        self._previsualizar = previsualizar
        self._por_descripcion = {c.descripcion: c for c in archivo.columnas}
        self._confirmadas: set[int] = set()
        self._marcas: list[tuple[ctk.CTkCheckBox, int]] = []
        self._vista: VistaPreviaTareas | None = None
        self._colores = configurar_estilo()

        ctk.CTkLabel(self.cuerpo, text="Importar tareas", font=tema.fuente(18, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            self.cuerpo, anchor="w", justify="left", wraplength=840,
            text=f"Archivo: {nombre_archivo}\nSe aplicará a: {curso.titulo}",
        ).pack(fill="x", pady=(8, 0))

        self._aviso = ctk.CTkLabel(
            self.cuerpo, text="", anchor="w", justify="left", wraplength=840,
            text_color=tema.COLOR_AVISO, font=tema.fuente(13, "bold"),
        )
        self._forzar = ctk.CTkCheckBox(
            self.cuerpo, text="Importar de todos modos", command=self._actualizar_boton,
            checkbox_width=20, checkbox_height=20,
        )

        fila = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        fila.pack(fill="x", pady=(12, 0))
        ctk.CTkLabel(fila, text="Columna a importar:", font=tema.fuente(13, "bold")).pack(side="left")
        self._columna = ctk.CTkOptionMenu(
            fila, values=list(self._por_descripcion), command=self._al_elegir_columna, width=330,
            fg_color=tema.COLOR_TAREAS, button_color=tema.COLOR_TAREAS_HOVER,
            button_hover_color=tema.COLOR_TAREAS_HOVER,
        )
        self._columna.pack(side="left", padx=10)
        self._muestra = ctk.CTkLabel(fila, text="", text_color=tema.COLOR_TEXTO_SUAVE, anchor="w")
        self._muestra.pack(side="left", fill="x", expand=True)

        self._resumen = ctk.CTkLabel(self.cuerpo, text="", anchor="w", justify="left", wraplength=840)
        self._resumen.pack(fill="x", pady=(12, 6))

        self._titulo_dudosas = ctk.CTkLabel(
            self.cuerpo, anchor="w", justify="left", wraplength=840, font=tema.fuente(13, "bold"),
            text_color=tema.COLOR_AVISO,
            text="Coincidencias dudosas: marca solo las que sean la misma persona.",
        )
        self._zona_dudosas: ctk.CTkFrame | None = None

        marco = ctk.CTkFrame(self.cuerpo, corner_radius=8, fg_color=tema.COLOR_TARJETA,
                             border_width=1, border_color=tema.COLOR_BORDE)
        marco.pack(fill="both", expand=True, pady=(8, 0))
        self._tabla = ttk.Treeview(
            marco, columns=[c[0] for c in COLUMNAS], show="headings", style=ESTILO,
            selectmode="browse", height=8,
        )
        for clave, titulo, ancho, alineacion in COLUMNAS:
            self._tabla.heading(clave, text=titulo, anchor=alineacion)
            self._tabla.column(clave, width=ancho, anchor=alineacion, stretch=(clave == "detalle"), minwidth=50)
        barra = ctk.CTkScrollbar(marco, command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=barra.set)
        self._tabla.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        barra.pack(side="right", fill="y", padx=(0, 4), pady=6)
        self._tabla.tag_configure("dudosa", foreground=self._colores["aviso"])
        self._tabla.tag_configure("omitida", foreground=self._colores["suave"])

        self._boton = self.botones("Aplicar", self._aceptar)
        self._boton.configure(width=170, fg_color=tema.COLOR_TAREAS, hover_color=tema.COLOR_TAREAS_HOVER)

        self._columna.set(archivo.columna_sugerida.descripcion)
        self._refrescar()

    # ---------------- estado ----------------
    @property
    def clave(self) -> str:
        return self._por_descripcion[self._columna.get()].clave

    def _al_elegir_columna(self, _descripcion: str) -> None:
        self._refrescar()

    def _refrescar(self) -> None:
        self._vista = vista = self._previsualizar(self.clave)
        self._mostrar_muestra()
        self._mostrar_aviso(vista)
        self._mostrar_resumen(vista)
        self._mostrar_dudosas(vista)
        self._mostrar_tabla(vista)
        self._actualizar_boton()

    def _mostrar_muestra(self) -> None:
        valores = []
        for fila in self._archivo.filas:
            valor = fila.valores.get(self.clave)
            if isinstance(valor, float):
                valores.append(formatear_decimas(valor))
            if len(valores) == MUESTRA:
                break
        self._muestra.configure(text="valores: " + ", ".join(valores) + "…")

    def _mostrar_aviso(self, vista: VistaPreviaTareas) -> None:
        if vista.advertencia_grupo:
            self._aviso.configure(text="⚠  " + vista.advertencia_grupo)
            self._aviso.pack(fill="x", pady=(10, 0), after=self.cuerpo.winfo_children()[1])
            self._forzar.pack(anchor="w", pady=(4, 0), after=self._aviso)
        else:
            self._aviso.pack_forget()
            self._forzar.pack_forget()

    def _mostrar_resumen(self, vista: VistaPreviaTareas) -> None:
        texto = (
            f"{len(vista.lineas)} alumnos en el archivo\n"
            f"•  {len(vista.claras)} coinciden ({vista.cambian} cambian · {vista.iguales} quedan igual)\n"
            f"•  {len(vista.dudosas)} coincidencias dudosas\n"
            f"•  {len(vista.omitidas)} se omiten\n"
            f"•  {len(vista.sin_aparecer)} alumnos del curso no aparecen en el archivo (no se tocan)"
        )
        self._resumen.configure(text=texto)

    def _mostrar_dudosas(self, vista: VistaPreviaTareas) -> None:
        if self._zona_dudosas is not None:
            self._zona_dudosas.destroy()  # se rehace con el alto que toca
            self._zona_dudosas = None
        self._marcas = []
        ids = {l.alumno.id for l in vista.dudosas}
        self._confirmadas &= ids  # una dudosa que dejó de serlo ya no cuenta como confirmada
        if not vista.dudosas:
            self._titulo_dudosas.pack_forget()
            return
        self._titulo_dudosas.pack(fill="x", pady=(0, 4), before=self._tabla.master)
        # CTkScrollableFrame ignora `height`: un marco de alto fijo con la zona desplazable dentro.
        self._zona_dudosas = ctk.CTkFrame(self.cuerpo, fg_color="transparent",
                                          height=min(120, 32 * len(vista.dudosas) + 6))
        self._zona_dudosas.pack_propagate(False)
        self._zona_dudosas.pack(fill="x", before=self._tabla.master)
        zona = ctk.CTkScrollableFrame(self._zona_dudosas)
        zona.pack(fill="both", expand=True)
        for linea in vista.dudosas:
            marca = ctk.CTkCheckBox(
                zona, checkbox_width=20, checkbox_height=20,
                text=f"{linea.fila.nombre_completo}  →  {linea.alumno.nombre_completo}"
                     f"  ({formatear_decimas(linea.puntos)})",
                command=self._al_marcar,
            )
            if linea.alumno.id in self._confirmadas:
                marca.select()
            marca.pack(anchor="w", pady=2)
            self._marcas.append((marca, linea.alumno.id))

    def _al_marcar(self) -> None:
        self._confirmadas = {i for marca, i in self._marcas if marca.get()}
        self._actualizar_boton()

    def _mostrar_tabla(self, vista: VistaPreviaTareas) -> None:
        self._tabla.delete(*self._tabla.get_children())
        orden = vista.dudosas + [l for l in vista.claras if l.cambia] + \
            [l for l in vista.claras if not l.cambia] + vista.omitidas
        for linea in orden:
            self._tabla.insert("", "end", values=self._valores(linea), tags=self._etiquetas(linea))

    @staticmethod
    def _valores(linea: LineaImportacion) -> tuple[str, ...]:
        if linea.estado == EstadoLinea.OMITIDA:
            return ("Omitida", linea.fila.nombre_completo, _numero(linea.anterior), "—", linea.motivo)
        estado = "Dudosa" if linea.estado == EstadoLinea.DUDOSA else ("Cambia" if linea.cambia else "Igual")
        detalle = linea.motivo if linea.estado == EstadoLinea.DUDOSA else linea.alumno.nombre_completo
        return (estado, linea.fila.nombre_completo, _numero(linea.anterior), _numero(linea.puntos), detalle)

    @staticmethod
    def _etiquetas(linea: LineaImportacion) -> tuple[str, ...]:
        return {EstadoLinea.DUDOSA: ("dudosa",), EstadoLinea.OMITIDA: ("omitida",)}.get(linea.estado, ())

    # ---------------- aplicar ----------------
    def _a_aplicar(self) -> int:
        vista = self._vista
        extra = sum(1 for l in vista.dudosas if l.alumno.id in self._confirmadas and l.cambia)
        return vista.cambian + extra

    def _actualizar_boton(self) -> None:
        n = self._a_aplicar()
        self._boton.configure(text=f"Aplicar {n} {'cambio' if n == 1 else 'cambios'}")
        bloqueado = n == 0 or (bool(self._vista.advertencia_grupo) and not self._forzar.get())
        self._boton.configure(state="disabled" if bloqueado else "normal")

    def _aceptar(self) -> None:
        if str(self._boton.cget("state")) == "disabled":
            return
        self.cerrar({"clave": self.clave, "confirmadas": set(self._confirmadas)})
