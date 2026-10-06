"""Cálculo del total de décimas de un alumno. Única fuente de la regla del piso de 0."""

from __future__ import annotations

from typing import Iterable

PISO_DECIMAS = 0.0


def acumulados(decimas: Iterable[float]) -> list[float]:
    """Total después de cada participación, aplicadas en el orden recibido (cronológico).

    El total nunca baja del piso (0) en ningún paso. Las participaciones se guardan tal como
    se capturaron (p. ej. -10); el piso se aplica al acumular. Así +5, -10, +5 da 5 (no 0).
    """
    total = PISO_DECIMAS
    resultado: list[float] = []
    for valor in decimas:
        total = max(PISO_DECIMAS, total + valor)
        resultado.append(round(total, 4))
    return resultado


def total_con_piso(decimas: Iterable[float]) -> float:
    """Total final tras aplicar todas las participaciones con el piso de 0."""
    pasos = acumulados(decimas)
    return pasos[-1] if pasos else PISO_DECIMAS
