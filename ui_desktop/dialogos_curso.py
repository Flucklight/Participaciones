"""Diálogos de la pantalla Curso: alumno ambiguo y alumno inexistente."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from core.errores import ErrorDominio
from core.models import Alumno, TipoInscripcion
from core.normalizacion import es_numero_de_cuenta, limpiar_nombre

from . import tema
from .dialogos import Dialogo


class DialogoElegirAlumno(Dialogo):
    """Hay varias coincidencias: el profesor elige una. Devuelve el `Alumno` o None."""

    def __init__(self, master, consulta: str, candidatos: list[Alumno],
                 tipos: dict[int, TipoInscripcion]) -> None:
        super().__init__(master, "Varias coincidencias", ancho=480)
        ctk.CTkLabel(self.cuerpo, text="Varias coincidencias", font=tema.fuente(18, "bold")
                     ).pack(anchor="w")
        ctk.CTkLabel(
            self.cuerpo, anchor="w", justify="left", wraplength=430,
            text_color=tema.COLOR_TEXTO_SUAVE,
            text=f"«{consulta}» coincide con {len(candidatos)} alumnos. Elige a quién registrar:",
        ).pack(fill="x", pady=(6, 10))
        zona = ctk.CTkScrollableFrame(self.cuerpo, height=min(260, 44 * len(candidatos) + 8))
        zona.pack(fill="x")
        for alumno in candidatos:
            cuenta = alumno.num_cuenta or "sin cuenta"
            etiqueta = "  (oyente)" if tipos.get(alumno.id) == TipoInscripcion.OYENTE else ""
            ctk.CTkButton(
                zona, text=f"{alumno.nombre_completo}{etiqueta}\n{cuenta}", anchor="w", height=42,
                fg_color="transparent", text_color=("gray10", "gray95"),
                hover_color=tema.COLOR_NAV_ACTIVO, border_width=1, border_color=tema.COLOR_BORDE,
                command=lambda a=alumno: self.cerrar(a),
            ).pack(fill="x", pady=3)
        fila = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        fila.pack(fill="x", pady=(14, 0))
        ctk.CTkButton(fila, text="Cancelar", width=100, fg_color="transparent", border_width=1,
                      border_color=tema.COLOR_BORDE, text_color=("gray20", "gray90"),
                      hover_color=tema.COLOR_NAV_ACTIVO, command=self.cancelar).pack(side="right")


class DialogoAlumnoNuevo(Dialogo):
    """Crea un alumno en el curso (o inscribe uno que existe en otro curso).

    `guardar(datos)` hace el trabajo y devuelve lo que `mostrar()` retornará; puede lanzar
    ErrorDominio y el mensaje se muestra dentro del diálogo.
    `datos = {"alumno_id": int | 0, "nombre": str, "cuenta": str, "tipo": TipoInscripcion}`
    """

    def __init__(
        self,
        master,
        guardar: Callable[[dict], object],
        consulta: str = "",
        resumen_decimas: str | None = None,
        candidatos: list[Alumno] | None = None,
    ) -> None:
        super().__init__(master, "Alumno no encontrado" if consulta else "Agregar alumno", ancho=500)
        self._guardar = guardar
        candidatos = candidatos or []

        if consulta:
            ctk.CTkLabel(self.cuerpo, text="Alumno no encontrado", font=tema.fuente(18, "bold")
                         ).pack(anchor="w")
            ctk.CTkLabel(
                self.cuerpo, anchor="w", justify="left", wraplength=450,
                text_color=tema.COLOR_TEXTO_SUAVE,
                text=f"«{consulta}» no está inscrito en este curso. ¿Quieres agregarlo?"
                     + (f"\nSe registrarán {resumen_decimas} décimas." if resumen_decimas else ""),
            ).pack(fill="x", pady=(6, 8))
        else:
            ctk.CTkLabel(self.cuerpo, text="Agregar alumno al curso", font=tema.fuente(18, "bold")
                         ).pack(anchor="w", pady=(0, 8))

        self._opcion = ctk.IntVar(value=candidatos[0].id if candidatos else 0)
        if candidatos:
            ctk.CTkLabel(self.cuerpo, anchor="w", font=tema.fuente(12, "bold"),
                         text="Existe en otros cursos. ¿Es alguno de ellos?"
                         ).pack(fill="x", pady=(4, 2))
            for a in candidatos[:5]:
                ctk.CTkRadioButton(
                    self.cuerpo, variable=self._opcion, value=a.id, radiobutton_width=18,
                    radiobutton_height=18,
                    text=f"{a.nombre_completo}  ·  {a.num_cuenta or 'sin cuenta'}",
                ).pack(anchor="w", pady=2)
            ctk.CTkRadioButton(
                self.cuerpo, variable=self._opcion, value=0, radiobutton_width=18,
                radiobutton_height=18, text="Ninguno: crear un alumno nuevo",
            ).pack(anchor="w", pady=(2, 6))

        self._nombre = self._campo("Nombre completo (apellidos y nombres)")
        self._cuenta = self._campo("Número de cuenta (opcional)")
        if consulta:
            if es_numero_de_cuenta(consulta):
                self._cuenta.insert(0, consulta.strip())
            else:
                self._nombre.insert(0, limpiar_nombre(consulta))

        ctk.CTkLabel(self.cuerpo, text="Tipo", anchor="w", font=tema.fuente(12),
                     text_color=tema.COLOR_TEXTO_SUAVE).pack(fill="x", pady=(10, 2))
        self._tipo = ctk.CTkSegmentedButton(self.cuerpo, values=["Oyente", "Regular"])
        self._tipo.set("Oyente")
        self._tipo.pack(anchor="w")

        self._error = ctk.CTkLabel(self.cuerpo, text="", text_color=tema.COLOR_PELIGRO,
                                   wraplength=450, justify="left", anchor="w")
        self._error.pack(fill="x", pady=(8, 0))
        self.botones("Agregar y registrar" if resumen_decimas else "Agregar", self._aceptar)

    def _campo(self, etiqueta: str) -> ctk.CTkEntry:
        ctk.CTkLabel(self.cuerpo, text=etiqueta, anchor="w", font=tema.fuente(12),
                     text_color=tema.COLOR_TEXTO_SUAVE).pack(fill="x", pady=(8, 2))
        entrada = ctk.CTkEntry(self.cuerpo, height=34)
        entrada.pack(fill="x")
        entrada.bind("<Return>", lambda _e: self._aceptar())
        return entrada

    def al_mostrar(self) -> None:
        (self._nombre if not self._nombre.get() else self._cuenta).focus_set()

    def _aceptar(self) -> None:
        datos = {
            "alumno_id": self._opcion.get(),
            "nombre": self._nombre.get(),
            "cuenta": self._cuenta.get(),
            "tipo": TipoInscripcion.REGULAR if self._tipo.get() == "Regular"
            else TipoInscripcion.OYENTE,
        }
        try:
            resultado = self._guardar(datos)
        except ErrorDominio as error:
            self._error.configure(text=str(error))
            return
        self.cerrar(resultado)


class DialogoExportar(Dialogo):
    """Opciones de exportación. Devuelve {"formato", "oyentes", "detalle"} o None."""

    def __init__(self, master, n_alumnos: int, n_oyentes: int) -> None:
        super().__init__(master, "Exportar curso", ancho=460)
        ctk.CTkLabel(self.cuerpo, text="Exportar curso", font=tema.fuente(18, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            self.cuerpo, anchor="w", justify="left", wraplength=410, text_color=tema.COLOR_TEXTO_SUAVE,
            text=f"{n_alumnos} alumno{'s' if n_alumnos != 1 else ''} regular{'es' if n_alumnos != 1 else ''}"
                 + (f" y {n_oyentes} oyente{'s' if n_oyentes != 1 else ''}." if n_oyentes else "."),
        ).pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(self.cuerpo, text="Formato", anchor="w", font=tema.fuente(12),
                     text_color=tema.COLOR_TEXTO_SUAVE).pack(fill="x")
        self._formato = ctk.CTkSegmentedButton(
            self.cuerpo, values=["Excel (.xlsx)", "CSV (.csv)"], command=self._al_cambiar_formato
        )
        self._formato.set("Excel (.xlsx)")
        self._formato.pack(anchor="w", pady=(2, 12))

        self._oyentes = ctk.CTkCheckBox(
            self.cuerpo, text="Incluir oyentes", checkbox_width=20, checkbox_height=20,
            state="normal" if n_oyentes else "disabled",
        )
        self._oyentes.pack(anchor="w", pady=3)
        self._detalle = ctk.CTkCheckBox(
            self.cuerpo, text="Agregar hoja con todas las participaciones",
            checkbox_width=20, checkbox_height=20,
        )
        self._detalle.select()
        self._detalle.pack(anchor="w", pady=3)
        self._nota = ctk.CTkLabel(
            self.cuerpo, anchor="w", justify="left", wraplength=410, font=tema.fuente(11),
            text_color=tema.COLOR_TEXTO_SUAVE,
            text="Los totales ya incluyen el mínimo de 0. Se exportan como números, no como fórmulas.",
        )
        self._nota.pack(fill="x", pady=(10, 0))
        self.botones("Elegir destino…", self._aceptar)

    def _al_cambiar_formato(self, etiqueta: str) -> None:
        es_excel = etiqueta.startswith("Excel")
        self._detalle.configure(state="normal" if es_excel else "disabled")
        if not es_excel:
            self._detalle.deselect()
        else:
            self._detalle.select()

    def _aceptar(self) -> None:
        excel = self._formato.get().startswith("Excel")
        self.cerrar({
            "formato": "xlsx" if excel else "csv",
            "oyentes": bool(self._oyentes.get()),
            "detalle": excel and bool(self._detalle.get()),
        })
