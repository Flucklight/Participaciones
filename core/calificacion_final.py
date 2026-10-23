"""Calificación final: suma ponderada de participaciones, exámenes, tareas y proyecto.

Única fuente del cálculo (como `promedio.py` y `puntaje.py`): el servicio la usa; la UI y el
exportador solo muestran. La calificación final **nunca se guarda**: se calcula siempre.

Todos los componentes se pasan a escala de 0 a 100 antes de ponderar:
    - participaciones: décimas × 10 (1 décima = 10 puntos; 10 décimas = 100 puntos = calificación 10);
    - promedio de exámenes, tareas y proyecto: tal cual se capturaron.
Sin tope: las ponderaciones pueden sumar más de 100 % y los componentes pasar de 100 (puntos extra).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

PUNTOS_POR_DECIMA = 10
SUGERIDA_EXAMENES = 30.0  # lo que se propone al asignar la ponderación de exámenes


@dataclass(frozen=True)
class Ponderaciones:
    """Porcentajes de cada componente de la calificación final (pueden sumar más de 100).

    Por omisión los exámenes pesan 0 %: se asigna su ponderación al crear el primer examen.
    """

    participaciones: float = 10.0
    examenes: float = 0.0
    tareas: float = 20.0
    proyecto: float = 40.0

    @property
    def suma(self) -> float:
        return self.participaciones + self.examenes + self.tareas + self.proyecto


POR_OMISION = Ponderaciones()


@dataclass(frozen=True)
class ComponenteFinal:
    """Una fila del desglose: el valor en escala 0–100, su ponderación y lo que aporta."""

    clave: str  # participaciones | examenes | tareas | proyecto
    nombre: str
    valor: float
    ponderacion: float

    @property
    def aporte(self) -> float:
        return self.valor * self.ponderacion / 100


@dataclass(frozen=True)
class DesgloseFinal:
    componentes: tuple[ComponenteFinal, ...]

    @property
    def final(self) -> float:
        """Valor exacto (sin redondear)."""
        return sum(c.aporte for c in self.componentes)


def desglose_final(
    decimas: float,
    promedio_examenes: float | None,
    tareas: float,
    proyecto: float,
    pesos: Ponderaciones = POR_OMISION,
) -> DesgloseFinal:
    """Los cuatro componentes en escala 0–100 con su ponderación.

    `decimas` es el total ya con el piso de 0 (R5). Sin exámenes (`promedio_examenes` None) el
    componente de exámenes vale 0: su peso no se redistribuye.
    """
    return DesgloseFinal((
        ComponenteFinal("participaciones", "Participaciones", decimas * PUNTOS_POR_DECIMA, pesos.participaciones),
        ComponenteFinal("examenes", "Exámenes", promedio_examenes or 0.0, pesos.examenes),
        ComponenteFinal("tareas", "Tareas", tareas, pesos.tareas),
        ComponenteFinal("proyecto", "Proyecto final", proyecto, pesos.proyecto),
    ))


def calificacion_final(
    decimas: float,
    promedio_examenes: float | None,
    tareas: float,
    proyecto: float,
    pesos: Ponderaciones = POR_OMISION,
) -> float:
    """Calificación final exacta (escala 0–100, sin redondear ni topar)."""
    return desglose_final(decimas, promedio_examenes, tareas, proyecto, pesos).final


def _decimal(valor: float) -> Decimal:
    # redondear a 10 decimales quita el error binario (0.1 + 0.2 = 0.30000000000000004) antes de decidir
    return Decimal(repr(round(valor, 10)))


def redondear(valor: float) -> int:
    """Entero más cercano con la mitad hacia arriba (87.5 → 88, 2.5 → 3; no el redondeo por banca)."""
    return int(_decimal(valor).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def sobre_diez(valor: float) -> float:
    """La misma calificación en escala de 0 a 10 con un decimal (81 → 8.1; mitad hacia arriba)."""
    return float((_decimal(valor) / 10).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
