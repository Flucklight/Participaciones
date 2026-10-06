"""Diálogos del Historial: alta/edición de una participación y edición de datos del alumno."""

from __future__ import annotations

from datetime import date
from typing import Callable

import customtkinter as ctk

from core.errores import ErrorDominio
from core.models import Alumno, Participacion

from . import tema
from .dialogos import Dialogo
from .formato import formatear_decimas, formatear_fecha, leer_decimas, leer_fecha


class _DialogoCampos(Dialogo):
    """Base: título, campos de una línea, mensaje de error y botones."""

    def __init__(self, master, titulo: str, ancho: int = 440) -> None:
        super().__init__(master, titulo, ancho)
        ctk.CTkLabel(self.cuerpo, text=titulo, font=tema.fuente(18, "bold")).pack(anchor="w", pady=(0, 6))
        self._error = ctk.CTkLabel(self.cuerpo, text="", text_color=tema.COLOR_PELIGRO,
                                   wraplength=ancho - 50, justify="left", anchor="w")

    def _campo(self, etiqueta: str, valor: str = "", ejemplo: str = "") -> ctk.CTkEntry:
        ctk.CTkLabel(self.cuerpo, text=etiqueta, anchor="w", font=tema.fuente(12),
                     text_color=tema.COLOR_TEXTO_SUAVE).pack(fill="x", pady=(8, 2))
        entrada = ctk.CTkEntry(self.cuerpo, height=34, placeholder_text=ejemplo)
        entrada.pack(fill="x")
        if valor:
            entrada.insert(0, valor)
        entrada.bind("<Return>", lambda _e: self._aceptar())
        return entrada

    def _pie(self, texto_ok: str) -> None:
        self._error.pack(fill="x", pady=(10, 0))
        self.botones(texto_ok, self._aceptar)

    def _aceptar(self) -> None:
        raise NotImplementedError


class DialogoParticipacion(_DialogoCampos):
    """Agregar (fecha libre, p. ej. anterior) o editar una participación.

    `guardar(datos)` recibe {"decimas": float, "fecha": date, "nota": str}, hace el trabajo
    y devuelve lo que `mostrar()` retornará; puede lanzar ErrorDominio.
    """

    def __init__(self, master, guardar: Callable[[dict], object],
                 participacion: Participacion | None = None) -> None:
        super().__init__(master, "Editar participación" if participacion else "Agregar participación")
        self._guardar = guardar
        self._decimas = self._campo(
            "Décimas (negativas restan; el total no baja de 0)",
            formatear_decimas(participacion.decimas) if participacion else "", "Ej. 10 o -5",
        )
        self._fecha = self._campo(
            "Fecha (dd/mm/aaaa)",
            formatear_fecha(participacion.fecha if participacion else date.today()),
        )
        self._nota = self._campo("Nota (opcional)", participacion.nota if participacion else "",
                                 "Ej. pasó al pizarrón")
        self._pie("Guardar")

    def al_mostrar(self) -> None:
        self._decimas.focus_set()
        self._decimas.select_range(0, "end")

    def _aceptar(self) -> None:
        try:
            try:
                decimas = leer_decimas(self._decimas.get())
            except ValueError:
                raise ErrorDominio("Las décimas deben ser un número (por ejemplo 10, 2.5 o -5).") from None
            try:
                fecha = leer_fecha(self._fecha.get())
            except ValueError:
                raise ErrorDominio("La fecha debe tener el formato dd/mm/aaaa.") from None
            resultado = self._guardar({"decimas": decimas, "fecha": fecha, "nota": self._nota.get()})
        except ErrorDominio as error:
            self._error.configure(text=str(error))
            return
        self.cerrar(resultado)


class DialogoEditarAlumno(_DialogoCampos):
    """Corregir nombre y número de cuenta. `guardar(nombre, cuenta)` puede lanzar ErrorDominio."""

    def __init__(self, master, alumno: Alumno,
                 guardar: Callable[[str, str], Alumno]) -> None:
        super().__init__(master, "Editar alumno", ancho=480)
        self._guardar = guardar
        self._nombre = self._campo("Nombre completo (apellidos y nombres)", alumno.nombre_completo)
        self._cuenta = self._campo("Número de cuenta (vacío si es oyente sin cuenta)",
                                   alumno.num_cuenta or "")
        self._pie("Guardar")

    def al_mostrar(self) -> None:
        self._nombre.focus_set()

    def _aceptar(self) -> None:
        try:
            alumno = self._guardar(self._nombre.get(), self._cuenta.get())
        except ErrorDominio as error:
            self._error.configure(text=str(error))
            return
        self.cerrar(alumno)
