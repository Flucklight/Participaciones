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
class CalificacionProyecto:
    """Calificación del proyecto final de un alumno en un curso (una por alumno y curso; sin tope).
    Calificar a un equipo copia la misma nota a cada miembro: no se guarda vínculo con el equipo."""

    curso_id: int
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
    # Número de equipo de proyecto (None si no tiene).
    equipo: int | None = None
    # Calificación del proyecto final; 0 si no se ha capturado.
    proyecto: float = 0.0
    # Calificación final exacta (0–100, sin redondear); la calcula core/calificacion_final.py.
    final: float = 0.0


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


class EstadoEquipo(str, Enum):
    FORMADO = "formado"
    AGREGADO = "agregado"  # alumnos sumados a un equipo que ya existía
    YA_TIENEN_EQUIPO = "ya_tienen_equipo"  # no se creó nada: alguien ya está en otro equipo


@dataclass
class Equipo:
    """Equipo de proyecto de un curso, con los miembros que tiene ahora (puede ser uno solo).
    `nombre` y `proyecto` (título) son opcionales: vacíos si no se pusieron."""

    curso_id: int
    numero: int
    miembros: list[Alumno] = field(default_factory=list)
    nombre: str = ""
    proyecto: str = ""


@dataclass
class ResultadoEquipo:
    estado: EstadoEquipo
    numero: int | None = None  # el equipo formado
    miembros: list[Alumno] = field(default_factory=list)
    # Con YA_TIENEN_EQUIPO: quién ya tenía equipo y cuál (no se movió ni se creó nada).
    con_equipo: list[tuple[Alumno, int]] = field(default_factory=list)


@dataclass
class ResultadoProyecto:
    """Resultado de calificar el proyecto a un alumno o a todo un equipo."""

    estado: EstadoRegistro
    puntos: float
    alumnos: list[Alumno] = field(default_factory=list)  # a quién(es) se aplica o se aplicaría
    equipo: int | None = None  # el equipo, si se calificó a uno
    # Con CONFIRMAR_REEMPLAZO: cuántos de `alumnos` ya tienen una calificación distinta de la nueva
    # (todavía no se guardó nada).
    con_otra: int = 0
    # {alumno_id: calificación que había (None si no había)} de todos los afectados; con GUARDADO es
    # lo que `deshacer_proyecto` restaura.
    anteriores: dict[int, CalificacionProyecto | None] = field(default_factory=dict)
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


@dataclass
class ColumnaCalificaciones:
    """Columna numérica de un archivo de calificaciones de otra plataforma."""

    clave: str  # letra de la columna ("H"); identifica los valores de cada fila
    rotulo: str = ""  # texto del encabezado ("" si la columna no lo tiene)

    @property
    def descripcion(self) -> str:
        if self.rotulo:
            return f"{self.rotulo} (columna {self.clave})"
        return f"Columna {self.clave} (sin encabezado)"


@dataclass
class FilaCalificacion:
    """Una fila de alumno del archivo. `valores` va por clave de columna: número, texto
    (celda no numérica) o None (celda vacía o fórmula sin valor guardado)."""

    apellidos: str
    nombres: str
    valores: dict[str, float | str | None] = field(default_factory=dict)
    cuenta: str = ""  # solo si el archivo trae columna de cuenta

    @property
    def nombre_completo(self) -> str:
        return f"{self.apellidos} {self.nombres}"


@dataclass
class ArchivoCalificaciones:
    columnas: list[ColumnaCalificaciones]
    filas: list[FilaCalificacion]
    grupo: str = ""  # solo si el archivo lo trae (xlsx)
    ciclo: str = ""

    @property
    def columna_sugerida(self) -> ColumnaCalificaciones:
        """La numérica de más a la derecha (en las plataformas, el promedio)."""
        return self.columnas[-1]


class EstadoLinea(str, Enum):
    APLICAR = "aplicar"  # coincidencia clara: se aplica al confirmar
    DUDOSA = "dudosa"  # coincidencia por palabras: solo se aplica si la persona la confirma
    OMITIDA = "omitida"  # no se aplica (sin coincidencia, ambigua o valor inválido)


@dataclass
class LineaImportacion:
    """Qué pasaría con una fila del archivo al importar."""

    fila: FilaCalificacion
    estado: EstadoLinea
    alumno: Alumno | None = None  # el alumno del curso al que corresponde (si se encontró)
    puntos: float | None = None  # valor a guardar (APLICAR y DUDOSA)
    anterior: float | None = None  # calificación de tareas que ya tenía (None si no tenía)
    motivo: str = ""  # por qué se omitió o por qué es dudosa

    @property
    def cambia(self) -> bool:
        return self.puntos is not None and self.puntos != self.anterior


@dataclass
class VistaPreviaTareas:
    """Resultado de revisar el archivo contra el curso; no guarda nada."""

    columna: ColumnaCalificaciones
    lineas: list[LineaImportacion]
    sin_aparecer: list[Alumno]  # alumnos del curso que el archivo no menciona (no se tocan)
    advertencia_grupo: str = ""  # "" si coincide o el archivo no trae grupo

    def _con(self, estado: EstadoLinea) -> list[LineaImportacion]:
        return [l for l in self.lineas if l.estado == estado]

    @property
    def claras(self) -> list[LineaImportacion]:
        return self._con(EstadoLinea.APLICAR)

    @property
    def dudosas(self) -> list[LineaImportacion]:
        return self._con(EstadoLinea.DUDOSA)

    @property
    def omitidas(self) -> list[LineaImportacion]:
        return self._con(EstadoLinea.OMITIDA)

    @property
    def cambian(self) -> int:
        return sum(1 for l in self.claras if l.cambia)

    @property
    def iguales(self) -> int:
        return sum(1 for l in self.claras if not l.cambia)


@dataclass
class ResultadoImportacionTareas:
    actualizadas: int  # guardadas (nuevas o con otro valor)
    iguales: int  # coincidían y ya tenían ese valor: no se reescriben
    omitidas: int  # omitidas, más las dudosas que no se confirmaron
    # {alumno_id: calificación que tenía (None si no tenía)} de lo que se guardó; lo usa deshacer.
    anteriores: dict[int, CalificacionTareas | None] = field(default_factory=dict)


@dataclass(frozen=True)
class ResumenBase:
    """Conteos que describen una base completa (la local o la de un archivo a importar)."""

    cursos: int
    alumnos: int
    participaciones: int
