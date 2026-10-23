"""Diálogo de ponderaciones de la calificación final (R18)."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from core.calificacion_final import POR_OMISION, Ponderaciones
from core.errores import ErrorDominio

from . import tema
from .dialogos import Dialogo
from .formato import formatear_decimas

COMPONENTES = (
    ("participaciones", "Participaciones"),
    ("examenes", "Exámenes"),
    ("tareas", "Tareas"),
    ("proyecto", "Proyecto final"),
)


class DialogoPonderaciones(Dialogo):
    """Los cuatro porcentajes de la calificación final, con la suma en vivo.

    `guardar(participaciones, examenes, tareas, proyecto)` puede lanzar ErrorDominio (se muestra
    dentro del diálogo) y devuelve las `Ponderaciones` guardadas, que son el resultado. «Restablecer»
    solo rellena los campos con 10 / 0 / 20 / 40; no guarda hasta pulsar «Guardar».
    """

    def __init__(
        self,
        master,
        ponderaciones: Ponderaciones,
        guardar: Callable[[float, float, float, float], Ponderaciones],
        enfocar: str = "participaciones",
        mensaje: str = "",
    ) -> None:
        super().__init__(master, "Ponderaciones", ancho=500)
        self._guardar = guardar
        self._enfocar = enfocar
        self._campos: dict[str, ctk.CTkEntry] = {}

        ctk.CTkLabel(self.cuerpo, text="Ponderaciones de la calificación final",
                     font=tema.fuente(18, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            self.cuerpo, anchor="w", justify="left", wraplength=450, font=tema.fuente(12),
            text_color=tema.COLOR_TEXTO_SUAVE,
            text="Cada componente aporta su calificación (de 0 a 100) por su porcentaje. Las "
                 "participaciones valen 10 puntos por décima. La suma puede pasar de 100 %: el "
                 "excedente son puntos extra.",
        ).pack(fill="x", pady=(6, 0))
        if mensaje:
            ctk.CTkLabel(self.cuerpo, text=mensaje, anchor="w", justify="left", wraplength=450,
                         font=tema.fuente(13, "bold"), text_color=tema.COLOR_AVISO).pack(fill="x", pady=(10, 0))

        cuadricula = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        cuadricula.pack(fill="x", pady=(12, 0))
        for i, (clave, nombre) in enumerate(COMPONENTES):
            fila, columna = divmod(i, 2)
            marco = ctk.CTkFrame(cuadricula, fg_color="transparent")
            marco.grid(row=fila, column=columna, sticky="ew", padx=(0, 14 if columna == 0 else 0), pady=6)
            cuadricula.grid_columnconfigure(columna, weight=1)
            ctk.CTkLabel(marco, text=nombre, anchor="w", font=tema.fuente(12),
                         text_color=tema.COLOR_TEXTO_SUAVE).pack(fill="x")
            interior = ctk.CTkFrame(marco, fg_color="transparent")
            interior.pack(fill="x")
            entrada = ctk.CTkEntry(interior, height=34, width=90)
            entrada.pack(side="left")
            ctk.CTkLabel(interior, text="%").pack(side="left", padx=(6, 0))
            entrada.insert(0, formatear_decimas(getattr(ponderaciones, clave)))
            entrada.bind("<KeyRelease>", lambda _e: self._actualizar_suma())
            entrada.bind("<Return>", lambda _e: self._aceptar())
            self._campos[clave] = entrada

        self._suma = ctk.CTkLabel(self.cuerpo, text="", anchor="w", font=tema.fuente(13, "bold"))
        self._suma.pack(fill="x", pady=(10, 0))
        self._error = ctk.CTkLabel(self.cuerpo, text="", text_color=tema.COLOR_PELIGRO,
                                   wraplength=450, justify="left", anchor="w")
        self._error.pack(fill="x", pady=(6, 0))
        self._boton = self.botones("Guardar", self._aceptar)
        self._restablecer = ctk.CTkButton(
            self._boton.master, text="Restablecer", width=110, command=self._restablecer_valores,
            fg_color="transparent", border_width=1, border_color=tema.COLOR_BORDE,
            text_color=tema.COLOR_TEXTO, hover_color=tema.COLOR_NAV_ACTIVO,
        )
        self._restablecer.pack(side="left")
        self._actualizar_suma()

    def al_mostrar(self) -> None:
        campo = self._campos.get(self._enfocar, self._campos["participaciones"])
        campo.focus_set()
        campo.select_range(0, "end")

    # ---------------- lectura y suma ----------------
    def _leer(self) -> dict[str, float]:
        """Los cuatro valores como números; ValueError con el mensaje si alguno no lo es."""
        valores = {}
        for clave, nombre in COMPONENTES:
            texto = self._campos[clave].get().strip().rstrip("%").strip().replace(",", ".")
            if not texto:
                raise ValueError(f"Escribe la ponderación de {nombre.lower()}.")
            try:
                valores[clave] = float(texto)
            except ValueError:
                raise ValueError(f"La ponderación de {nombre.lower()} debe ser un número.") from None
        return valores

    def _actualizar_suma(self) -> None:
        try:
            suma = sum(self._leer().values())
        except ValueError:
            self._suma.configure(text="Escribe solo números (por ejemplo 30 o 12.5).", text_color=tema.COLOR_AVISO)
            return
        texto = f"Suma: {formatear_decimas(suma)} %"
        if suma > 100:
            self._suma.configure(text=f"{texto}  ·  {formatear_decimas(suma - 100)} % de puntos extra",
                                 text_color=tema.COLOR_EXITO)
        elif suma < 100:
            self._suma.configure(text=f"{texto}  ·  faltan {formatear_decimas(100 - suma)} %",
                                 text_color=tema.COLOR_AVISO)
        else:
            self._suma.configure(text=texto, text_color=tema.COLOR_TEXTO)

    def _restablecer_valores(self) -> None:
        for clave, campo in self._campos.items():
            campo.delete(0, "end")
            campo.insert(0, formatear_decimas(getattr(POR_OMISION, clave)))
        self._error.configure(text="")
        self._actualizar_suma()

    def _aceptar(self) -> None:
        try:
            valores = self._leer()
            guardadas = self._guardar(
                valores["participaciones"], valores["examenes"], valores["tareas"], valores["proyecto"]
            )
        except (ValueError, ErrorDominio) as error:
            self._error.configure(text=str(error))
            return
        self.cerrar(guardadas)
