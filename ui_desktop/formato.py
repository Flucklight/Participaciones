"""Utilidades de presentación de texto."""

from datetime import date, datetime

_MINUSCULAS = {"a", "al", "de", "del", "el", "en", "la", "las", "los", "o", "para", "por", "y", "con", "u"}


def titulo_legible(texto: str) -> str:
    """'DISEÑO Y ANALISIS DE ALGORITMOS' -> 'Diseño y Analisis de Algoritmos'."""
    palabras = texto.lower().split()
    return " ".join(
        p if (i > 0 and p in _MINUSCULAS) else p.capitalize() for i, p in enumerate(palabras)
    )


def formatear_decimas(valor: float, con_signo: bool = False) -> str:
    """10.0 -> '10'; 2.5 -> '2.5'; con_signo: 10 -> '+10', -4 -> '-4'."""
    redondeado = round(valor, 2)
    texto = f"{redondeado:.2f}".rstrip("0").rstrip(".")
    if texto in ("-0", ""):
        texto = "0"
    if con_signo and redondeado > 0:
        texto = "+" + texto
    return texto


def leer_decimas(texto: str) -> float:
    """Convierte lo escrito por el usuario ('10', '+5', '-2,5'); lanza ValueError si no es número."""
    limpio = texto.strip().replace(",", ".")
    if not limpio:
        raise ValueError("vacío")
    return float(limpio)


def formatear_fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")


def leer_fecha(texto: str) -> date:
    """Acepta dd/mm/aaaa o aaaa-mm-dd; lanza ValueError si no es una fecha válida."""
    limpio = texto.strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(limpio, formato).date()
        except ValueError:
            continue
    raise ValueError("fecha inválida")
