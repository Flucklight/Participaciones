"""Colores y fuentes compartidos. Los pares son (modo claro, modo oscuro)."""

COLOR_ACENTO = ("#2B6CB0", "#4C8DDB")
COLOR_ACENTO_HOVER = ("#245A94", "#3F78BC")
COLOR_PELIGRO = ("#C53030", "#E05252")
COLOR_PELIGRO_HOVER = ("#9B2C2C", "#C24242")
COLOR_EXITO = ("#2F855A", "#48BB78")

COLOR_FONDO = ("#F4F6F9", "#1B1D21")
COLOR_PANEL = ("#E4E8EE", "#14161A")
COLOR_TARJETA = ("#FFFFFF", "#26292F")
COLOR_BORDE = ("#D5DAE1", "#363A42")
COLOR_TEXTO_SUAVE = ("#5A6472", "#9AA3B0")
COLOR_NAV_ACTIVO = ("#CBD5E1", "#2A2E36")

FUENTE = "Segoe UI"


def fuente(tam: int = 13, peso: str = "normal") -> tuple[str, int, str]:
    return (FUENTE, tam, peso)
