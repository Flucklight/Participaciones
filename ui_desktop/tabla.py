"""Estilo común de las tablas (ttk.Treeview) para modo claro y oscuro."""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

from . import tema

ESTILO = "Curso.Treeview"


def configurar_estilo() -> dict[str, str]:
    """Aplica el estilo y devuelve colores para las etiquetas de fila (`tag_configure`)."""
    oscuro = ctk.get_appearance_mode() == "Dark"
    i = 1 if oscuro else 0
    fondo = tema.COLOR_TARJETA[i]
    texto = tema.COLOR_TEXTO[i]
    estilo = ttk.Style()
    estilo.theme_use("clam")
    estilo.configure(ESTILO, background=fondo, fieldbackground=fondo, foreground=texto,
                     rowheight=30, borderwidth=0, font=tema.fuente(12),
                     bordercolor=fondo, lightcolor=fondo, darkcolor=fondo)
    estilo.configure(f"{ESTILO}.Heading", background=tema.COLOR_PANEL[i], foreground=texto,
                     font=tema.fuente(12, "bold"), relief="flat", padding=(8, 6))
    estilo.map(ESTILO, background=[("selected", tema.COLOR_ACENTO[i])],
               foreground=[("selected", "#FFFFFF")])
    estilo.map(f"{ESTILO}.Heading", background=[("active", tema.COLOR_NAV_ACTIVO[i])])
    return {
        "suave": tema.COLOR_TEXTO_SUAVE[i],
        "reciente": tema.COLOR_RECIENTE[i],
        "aviso": tema.COLOR_AVISO[i],
    }
