"""Cómo se agrupa la tabla del curso en modo «Proyecto» (función pura, sin widgets)."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.models import ResumenAlumno

# iid de las filas de encabezado de equipo: no pueden chocar con los de alumno (su id como texto).
PREFIJO_ENCABEZADO = "equipo_"


def es_encabezado(iid: str) -> bool:
    return iid.startswith(PREFIJO_ENCABEZADO)


def iid_encabezado(numero: int) -> str:
    return f"{PREFIJO_ENCABEZADO}{numero}"


@dataclass
class GrupoEquipo:
    numero: int | None  # None: alumnos sin equipo
    filas: list[ResumenAlumno] = field(default_factory=list)
    banda: int | None = None  # 0 o 1, alternando por orden de aparición; None sin equipo

    @property
    def titulo(self) -> str:
        n = len(self.filas)
        return f"Equipo {self.numero} · {n} {'alumno' if n == 1 else 'alumnos'}"


def agrupar_por_equipo(filas: list[ResumenAlumno]) -> list[GrupoEquipo]:
    """Agrupa filas ya filtradas y ordenadas: equipos por número (conservando dentro de cada
    uno el orden recibido) y al final los alumnos sin equipo. Un equipo sin filas no aparece."""
    por_equipo: dict[int, list[ResumenAlumno]] = {}
    sin_equipo: list[ResumenAlumno] = []
    for fila in filas:
        if fila.equipo is None:
            sin_equipo.append(fila)
        else:
            por_equipo.setdefault(fila.equipo, []).append(fila)
    grupos = [
        GrupoEquipo(numero, miembros, banda=posicion % 2)
        for posicion, (numero, miembros) in enumerate(sorted(por_equipo.items()))
    ]
    if sin_equipo:
        grupos.append(GrupoEquipo(None, sin_equipo))
    return grupos
