"""Modelos del dominio (sin dependencias de base de datos ni de interfaz)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class TipoInscripcion(str, Enum):
    REGULAR = "regular"
    OYENTE = "oyente"


@dataclass
class Alumno:
    id: int | None
    nombre_completo: str
    num_cuenta: str | None = None


@dataclass
class Curso:
    id: int | None
    ciclo: str
    carrera: str
    materia: str
    grupo: str
    archivado: bool = False

    @property
    def titulo(self) -> str:
        return f"{self.materia} · {self.grupo} · {self.ciclo}"


@dataclass
class Inscripcion:
    curso_id: int
    alumno_id: int
    tipo: TipoInscripcion = TipoInscripcion.REGULAR


@dataclass
class Participacion:
    id: int | None
    curso_id: int
    alumno_id: int
    decimas: float
    fecha: date
    nota: str = ""


@dataclass
class Examen:
    id: int | None
    curso_id: int
    nombre: str


@dataclass
class Calificacion:
    """Calificación de un alumno en un examen (una por alumno y examen; sin tope)."""

    examen_id: int
    alumno_id: int
    puntos: float
    fecha: date


@dataclass
class CalificacionTareas:
    """Calificación de tareas de un alumno en un curso: el promedio ya calculado en otra
    plataforma (una por alumno y curso; sin tope)."""

    curso_id: int
    alumno_id: int
    puntos: float
    fecha: date


@dataclass
class LineaExamen:
    """Un examen del curso con la calificación del alumno (None si aún no se captura)."""

    examen: Examen
    calificacion: Calificacion | None

    @property
    def puntos(self) -> float:
        return self.calificacion.puntos if self.calificacion else 0.0


@dataclass
class LineaHistorial:
    """Una participación con su efecto real y el total acumulado tras ella."""

    participacion: Participacion
    aplicado: float   # cambio real del total (distinto de `decimas` si se tocó el piso de 0)
    acumulado: float  # total del alumno inmediatamente después de este registro

    @property
    def toco_el_piso(self) -> bool:
        return abs(self.aplicado - self.participacion.decimas) > 1e-9


@dataclass
class ResumenAlumno:
    """Una fila de la tabla de un curso."""

    alumno: Alumno
    tipo: TipoInscripcion
    total: float
    n_participaciones: int
    ultima_fecha: date | None
    # Promedio de exámenes (None si el curso no tiene exámenes); lo calcula core/promedio.py.
    prom_examenes: float | None = None
    # {examen_id: puntos} de los exámenes con calificación capturada (el resto vale 0).
    calificaciones: dict[int, float] = field(default_factory=dict)
    # Calificación de tareas (promedio ya calculado fuera); 0 si no se ha capturado.
    tareas: float = 0.0


class EstadoRegistro(str, Enum):
    GUARDADO = "guardado"
    AMBIGUO = "ambiguo"
    NO_EXISTE = "no_existe"
    CONFIRMAR_REEMPLAZO = "confirmar_reemplazo"  # solo calificaciones: ya había una


@dataclass
class ResultadoRegistro:
    estado: EstadoRegistro
    decimas: float
    alumno: Alumno | None = None
    participacion: Participacion | None = None
    total: float | None = None
    # Cambio real del total (puede ser menor al solicitado si se tocó el piso de 0).
    decimas_aplicadas: float | None = None
    # AMBIGUO: coincidencias dentro del curso. NO_EXISTE: alumnos que existen en
    # otros cursos y podrían inscribirse aquí.
    candidatos: list[Alumno] = field(default_factory=list)


@dataclass
class ResultadoCalificacion:
    estado: EstadoRegistro
    puntos: float
    alumno: Alumno | None = None
    examen: Examen | None = None
    # La calificación que había antes (None si era la primera). Con CONFIRMAR_REEMPLAZO
    # todavía no se reemplazó nada; con GUARDADO es lo que `deshacer_calificacion` restaura.
    calificacion_anterior: Calificacion | None = None
    promedio: float | None = None
    candidatos: list[Alumno] = field(default_factory=list)


@dataclass
class ResultadoTareas:
    estado: EstadoRegistro
    puntos: float
    alumno: Alumno | None = None
    # La calificación que había antes (None si era la primera). Con CONFIRMAR_REEMPLAZO todavía
    # no se reemplazó nada; con GUARDADO es lo que `deshacer_tareas` restaura.
    anterior: CalificacionTareas | None = None
    candidatos: list[Alumno] = field(default_factory=list)


@dataclass
class FilaLista:
    numero: int
    num_cuenta: str
    nombre_completo: str


@dataclass
class ListaInscripcion:
    ciclo: str
    carrera: str
    materia: str
    grupo: str
    alumnos: list[FilaLista]


@dataclass
class CoincidenciaOyente:
    """Un alumno de la lista que coincide por nombre con un oyente sin cuenta."""

    fila: FilaLista
    oyente: Alumno


@dataclass
class VistaPreviaImportacion:
    curso_existente: Curso | None
    alumnos_nuevos: int
    alumnos_existentes: int
    coincidencias_oyentes: list[CoincidenciaOyente]


@dataclass
class ResultadoImportacion:
    curso: Curso
    curso_creado: bool
    alumnos_creados: int
    inscripciones_nuevas: int
    vinculados: int
