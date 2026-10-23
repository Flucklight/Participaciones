"""Paleta y fuentes del proyecto. ÚNICO lugar con colores: las vistas usan estos nombres.

Cada color es un par (modo claro, modo oscuro).

Idea de la paleta: azul de la FES Aragón como color de marca (participaciones) e índigo, vecino
del azul en el círculo cromático, para el modo Examen: se distinguen a simple vista sin chocar.
Verde, rojo y ámbar quedan reservados para éxito, peligro y avisos.
"""

import customtkinter as ctk

# --- marca ---------------------------------------------------------------
# Los rellenos (botones, selección) llevan texto blanco, por eso en modo oscuro son más profundos;
# el azul claro de COLOR_ACENTO_TEXTO es para texto de enlaces sobre fondo oscuro.
COLOR_ACENTO = ("#2F5DA8", "#3F74D9")           # participaciones, selección, botón principal
COLOR_ACENTO_HOVER = ("#264C8A", "#3463BD")
COLOR_ACENTO_TEXTO = ("#2F5DA8", "#8DB1F7")
COLOR_EXAMEN = ("#5B46B2", "#7A64E0")           # modo Examen
COLOR_EXAMEN_HOVER = ("#4A3894", "#664FCB")
COLOR_TAREAS = ("#0F766E", "#0D8A80")           # modo Tareas (verde azulado)
COLOR_TAREAS_HOVER = ("#0B5F58", "#0A736B")

# --- estados ---------------------------------------------------------------
COLOR_EXITO = ("#237A5A", "#4FC79A")
COLOR_PELIGRO = ("#C0392B", "#EF6B5E")
COLOR_PELIGRO_HOVER = ("#9E2F23", "#D4574B")
COLOR_AVISO = ("#9A6212", "#E3B341")            # advertencias (p. ej. reemplazar una nota)

# --- superficies y texto -----------------------------------------------------
COLOR_FONDO = ("#F3F5F9", "#16181D")
COLOR_PANEL = ("#E6EAF2", "#101216")
COLOR_TARJETA = ("#FFFFFF", "#21242B")
COLOR_BORDE = ("#D6DCE6", "#323743")
COLOR_TEXTO = ("#1F2937", "#E6E9EF")
COLOR_TEXTO_SUAVE = ("#5B6678", "#9AA4B5")
COLOR_NAV_ACTIVO = ("#D5DEEE", "#2A3040")
COLOR_RECIENTE = ("#D5F2E3", "#25513F")         # fila recién registrada en la tabla

FUENTE = "Segoe UI"


def fuente(tam: int = 13, peso: str = "normal") -> tuple[str, int, str]:
    return (FUENTE, tam, peso)


def aplicar_a_customtkinter() -> None:
    """Hace que los widgets sin color explícito (casillas, radios, scrollbars…) usen la paleta.

    Llamar después de `ctk.set_default_color_theme(...)` y antes de crear widgets.
    """
    tema = ctk.ThemeManager.theme
    cambios = {
        "CTkButton": {"fg_color": COLOR_ACENTO, "hover_color": COLOR_ACENTO_HOVER},
        "CTkCheckBox": {"fg_color": COLOR_ACENTO, "hover_color": COLOR_ACENTO_HOVER},
        "CTkRadioButton": {"fg_color": COLOR_ACENTO, "hover_color": COLOR_ACENTO_HOVER},
        "CTkSegmentedButton": {
            "selected_color": COLOR_ACENTO, "selected_hover_color": COLOR_ACENTO_HOVER,
            "unselected_color": ("#7A869B", "#3A4050"),
            "unselected_hover_color": ("#6A768C", "#4A5164"),
            "text_color": ("#FFFFFF", "#FFFFFF"),
        },
        "CTkOptionMenu": {
            "fg_color": COLOR_ACENTO, "button_color": COLOR_ACENTO_HOVER,
            "button_hover_color": COLOR_ACENTO_HOVER,
        },
        "CTkScrollbar": {"button_color": COLOR_BORDE, "button_hover_color": COLOR_TEXTO_SUAVE},
    }
    for widget, colores in cambios.items():
        tema.setdefault(widget, {}).update({k: list(v) for k, v in colores.items()})
