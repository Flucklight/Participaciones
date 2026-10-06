"""Normalización de texto para guardar y comparar nombres."""

import re
import unicodedata

_ESPACIOS = re.compile(r"\s+")


def limpiar_nombre(texto: str) -> str:
    """Forma que se guarda: mayúsculas, sin espacios sobrantes (conserva acentos)."""
    return _ESPACIOS.sub(" ", texto).strip().upper()


def normalizar(texto: str) -> str:
    """Forma para comparar y buscar: sin mayúsculas, acentos ni espacios repetidos."""
    descompuesto = unicodedata.normalize("NFD", limpiar_nombre(texto))
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def es_numero_de_cuenta(texto: str) -> bool:
    return texto.strip().isdigit()
