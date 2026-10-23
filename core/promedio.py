"""Promedio de exámenes de un alumno. Única fuente de este cálculo."""

from __future__ import annotations

from typing import Sequence


def promedio_examenes(puntos: Sequence[float]) -> float | None:
    """Media simple de los puntos de TODOS los exámenes del curso.

    Un examen sin calificación se pasa como 0. Los exámenes no tienen tope (puede haber
    puntos extra). Sin exámenes no hay promedio (None).
    """
    if not puntos:
        return None
    return sum(puntos) / len(puntos)
