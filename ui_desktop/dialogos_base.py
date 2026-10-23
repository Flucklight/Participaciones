"""Diálogos de importación de base: elegir el modo y, al fusionar, revisar la vista previa y decidir."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from core.importar_base import PlanFusion
from core.models import ResumenBase

from . import tema
from .dialogos import Dialogo


def _conteos(r: ResumenBase) -> str:
    return f"{r.cursos} cursos · {r.alumnos} alumnos · {r.participaciones} participaciones"


class DialogoImportarBase(Dialogo):
    """Devuelve «fusionar» o «reemplazar», o None si se cancela. No guarda nada: lo hace quien lo abre."""

    def __init__(self, master, nombre_archivo: str, local: ResumenBase, archivo: ResumenBase) -> None:
        super().__init__(master, "Importar base", ancho=560)
        ctk.CTkLabel(self.cuerpo, text="Importar base", font=tema.fuente(18, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            self.cuerpo, anchor="w", justify="left", wraplength=510,
            text=f"Archivo: {nombre_archivo}\nContiene: {_conteos(archivo)}\nAquí hay: {_conteos(local)}",
        ).pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(
            self.cuerpo, anchor="w", justify="left", wraplength=510,
            text="Fusionar suma lo que falta sin borrar nada de lo de aquí; antes de guardar verás qué se agrega "
                 "y cada diferencia para que elijas.",
        ).pack(fill="x", pady=(12, 0))
        ctk.CTkLabel(
            self.cuerpo, anchor="w", justify="left", wraplength=510, text_color=tema.COLOR_PELIGRO,
            text="Reemplazar todo borra lo de aquí y deja la base igual a la del archivo.",
        ).pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(
            self.cuerpo, anchor="w", text_color=tema.COLOR_TEXTO_SUAVE,
            text="En ambos casos se crea un respaldo y podrás deshacer la importación.",
        ).pack(fill="x", pady=(8, 0))
        fila = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        fila.pack(fill="x", pady=(18, 0))
        ctk.CTkButton(
            fila, text="Cancelar", width=100, fg_color="transparent", border_width=1,
            border_color=tema.COLOR_BORDE, text_color=tema.COLOR_TEXTO,
            hover_color=tema.COLOR_NAV_ACTIVO, command=self.cancelar,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            fila, text="Reemplazar todo", width=130, fg_color=tema.COLOR_PELIGRO,
            hover_color=tema.COLOR_PELIGRO_HOVER, command=lambda: self.cerrar("reemplazar"),
        ).pack(side="right")
        ctk.CTkButton(
            fila, text="Fusionar…", width=110, fg_color=tema.COLOR_ACENTO,
            hover_color=tema.COLOR_ACENTO_HOVER, command=lambda: self.cerrar("fusionar"),
        ).pack(side="right", padx=(0, 8))


class DialogoFusion(Dialogo):
    """Vista previa de la fusión. Devuelve {"unir", "usar_importado", "mantener_ambas"} (conjuntos de ids)
    al aplicar, o None si se cancela. Lo que se muestra es lo que se aplicará; nada se guarda aquí."""

    def __init__(self, master, nombre_archivo: str, previsualizar: Callable[[frozenset], PlanFusion]) -> None:
        super().__init__(master, "Fusionar base", ancho=820)
        self._previsualizar = previsualizar
        self._unir: set[str] = set()
        self._usar: set[str] = set()
        self._ambas: set[str] = set()
        self._plan: PlanFusion | None = None

        ctk.CTkLabel(self.cuerpo, text="Fusionar base", font=tema.fuente(18, "bold")).pack(anchor="w")
        ctk.CTkLabel(self.cuerpo, anchor="w", text=f"Archivo: {nombre_archivo}",
                     text_color=tema.COLOR_TEXTO_SUAVE).pack(fill="x", pady=(4, 0))
        self._resumen = ctk.CTkLabel(self.cuerpo, text="", anchor="w", justify="left", wraplength=770)
        self._resumen.pack(fill="x", pady=(10, 6))
        self._zona = ctk.CTkScrollableFrame(self.cuerpo, height=330, fg_color=tema.COLOR_TARJETA)
        self._zona.pack(fill="both", expand=True)
        self._boton = self.botones("Aplicar", self._aceptar)
        self._boton.configure(width=190)
        self._refrescar()

    # ---------------- estado ----------------
    def _refrescar(self) -> None:
        self._plan = plan = self._previsualizar(frozenset(self._unir))
        self._usar &= {c.id for c in plan.conflictos}
        self._ambas &= {d.id for d in plan.duplicados}
        partes = [f"{n} {nombre}" for nombre, n in plan.agregan.items()]
        texto = "Se agregará: " + (", ".join(partes) if partes else "nada nuevo") + "."
        if plan.iguales:
            texto += f"\n{plan.iguales} datos ya estaban iguales."
        if plan.omitidos:
            texto += f"\n{plan.omitidos} alumnos del archivo no se importan (confirma abajo si son la misma persona)."
        self._resumen.configure(text=texto)
        for hijo in self._zona.winfo_children():
            hijo.destroy()
        for aviso in plan.avisos:
            self._texto(aviso, color=tema.COLOR_AVISO)
        if plan.dudosos:
            self._titulo("Personas dudosas: marca solo las que sean la misma persona")
            for d in plan.dudosos:
                self._casilla(f"Es la misma persona · archivo: {d.archivo}  ↔  aquí: {d.local}",
                              d.id, self._unir, recalcular=True)
        if plan.conflictos:
            self._titulo("Diferencias: marca las que quieras cambiar por el valor del archivo (si no, se conserva lo de aquí)")
            for c in plan.conflictos:
                self._casilla(f"{c.entidad} · {c.descripcion}:  {c.antes}  →  {c.despues}", c.id, self._usar)
        if plan.duplicados:
            self._titulo("Participaciones iguales a las que ya hay: marca para conservar ambas (si no, se descartan las importadas)")
            for d in plan.duplicados:
                self._casilla(f"{d.descripcion} · {d.cantidad} coinciden", d.id, self._ambas)
        if not (plan.avisos or plan.dudosos or plan.conflictos or plan.duplicados):
            self._texto("No hay diferencias que decidir.", color=tema.COLOR_TEXTO_SUAVE)
        self._actualizar_boton()

    def _titulo(self, texto: str) -> None:
        ctk.CTkLabel(self._zona, text=texto, anchor="w", justify="left", wraplength=740,
                     font=tema.fuente(13, "bold")).pack(fill="x", padx=6, pady=(10, 4))

    def _texto(self, texto: str, color) -> None:
        ctk.CTkLabel(self._zona, text=texto, anchor="w", justify="left", wraplength=740,
                     text_color=color).pack(fill="x", padx=6, pady=2)

    def _casilla(self, texto: str, clave: str, conjunto: set[str], recalcular: bool = False) -> None:
        def alternar() -> None:
            conjunto.symmetric_difference_update({clave})
            if recalcular:
                self._refrescar()
            else:
                self._actualizar_boton()

        caja = ctk.CTkCheckBox(self._zona, text=texto, command=alternar, checkbox_width=20, checkbox_height=20)
        if clave in conjunto:
            caja.select()
        caja.pack(fill="x", padx=10, pady=3, anchor="w")
        caja._text_label.configure(wraplength=700, justify="left")

    @property
    def cambios(self) -> int:
        """Lo que se guardará: lo que se agrega más lo elegido."""
        plan = self._plan
        elegidas_ambas = sum(d.cantidad for d in plan.duplicados if d.id in self._ambas)
        return plan.total_agregan + len(self._usar) + elegidas_ambas

    def _actualizar_boton(self) -> None:
        n = self.cambios
        self._boton.configure(text=f"Aplicar {n} cambios" if n != 1 else "Aplicar 1 cambio",
                              state="normal" if n else "disabled")

    def _aceptar(self) -> None:
        self.cerrar({"unir": frozenset(self._unir), "usar_importado": frozenset(self._usar),
                     "mantener_ambas": frozenset(self._ambas)})
