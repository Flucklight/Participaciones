"""Ícono de la aplicación para ventanas y diálogos."""

from __future__ import annotations

from core.rutas import recurso

RUTA_ICONO = recurso("assets/icon/app.ico")


def aplicar_icono(ventana) -> None:
    """Pone el ícono de la FES Aragón en una ventana.

    customtkinter reemplaza el ícono de sus ventanas ~200 ms después de crearlas, por eso
    se vuelve a aplicar un poco más tarde.
    """
    if not RUTA_ICONO.exists():
        return

    def poner() -> None:
        try:
            ventana.iconbitmap(str(RUTA_ICONO))
        except Exception:  # la ventana ya se cerró o el sistema no soporta .ico
            pass

    poner()
    ventana.after(300, poner)
