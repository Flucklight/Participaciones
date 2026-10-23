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


def numero_de_encabezado(iid: str) -> int:
    return int(iid.removeprefix(PREFIJO_ENCABEZADO))


@dataclass
class GrupoEquipo:
    numero: int | None  # None: alumnos sin equipo
    filas: list[ResumenAlumno] = field(default_factory=list)
    banda: int | None = None  # 0 o 1, alternando por orden de aparición; None sin equipo
    nombre: str = ""  # opcionales: nombre del equipo y título de su proyecto
    proyecto: str = ""

    @property
    def titulo(self) -> str:
        """«Equipo 3 · 4 alumnos», seguido del nombre y del proyecto si el equipo los tiene. Lo
        importante va primero: si el encabezado no cabe, se recorta lo último."""
        n = len(self.filas)
        partes = [f"Equipo {self.numero}", f"{n} {'alumno' if n == 1 else 'alumnos'}"]
        partes += [p for p in (self.nombre, self.proyecto) if p]
        return " · ".join(partes)


def agrupar_por_equipo(
    filas: list[ResumenAlumno], datos: dict[int, tuple[str, str]] | None = None
) -> list[GrupoEquipo]:
    """Agrupa filas ya filtradas y ordenadas: equipos por número (conservando dentro de cada
    uno el orden recibido) y al final los alumnos sin equipo. Un equipo sin filas no aparece.
    `datos` trae {número: (nombre, proyecto)} para el encabezado."""
    datos = datos or {}
    por_equipo: dict[int, list[ResumenAlumno]] = {}
    sin_equipo: list[ResumenAlumno] = []
    for fila in filas:
        if fila.equipo is None:
            sin_equipo.append(fila)
        else:
            por_equipo.setdefault(fila.equipo, []).append(fila)
    grupos = [
        GrupoEquipo(numero, miembros, posicion % 2, *datos.get(numero, ("", "")))
        for posicion, (numero, miembros) in enumerate(sorted(por_equipo.items()))
    ]
    if sin_equipo:
        grupos.append(GrupoEquipo(None, sin_equipo))
    return grupos
