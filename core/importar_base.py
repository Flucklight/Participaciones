"""Fusionar la base de un archivo con la local (R19). Sin SQL ni interfaz: lee y escribe por `Repositorio`.

Identidad por clave natural, nunca por `id` (los `id` difieren entre máquinas):
curso = ciclo + materia + grupo · alumno = cuenta (sin cuenta: nombre normalizado, siempre con confirmación)
· examen = curso + nombre normalizado · equipo = curso + número.

`calcular_plan` solo lee y devuelve lo que se haría; `aplicar_plan` ejecuta exactamente ese plan, en una
transacción, con las decisiones de la persona. Nunca borra nada local ni importa totales (solo eventos).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from .calificacion_final import Ponderaciones
from .models import (
    Alumno,
    Calificacion,
    CalificacionProyecto,
    CalificacionTareas,
    Curso,
    Examen,
    Participacion,
    TipoInscripcion,
)
from .normalizacion import normalizar
from .repository import Repositorio

ClaveCurso = tuple[str, str, str]  # ciclo, materia, grupo


def _num(valor: float) -> str:
    return str(int(valor)) if float(valor).is_integer() else f"{valor:g}"


def _etiqueta(clave: ClaveCurso) -> str:
    return f"{clave[1]} · {clave[2]} · {clave[0]}"


# ---------------------------------------------------------------- resultado
@dataclass
class Conflicto:
    """Un valor distinto en cada base. Por omisión se conserva el local."""

    id: str
    entidad: str
    descripcion: str
    antes: str  # lo local
    despues: str  # lo del archivo


@dataclass
class DuplicadoParticipaciones:
    """Participaciones del archivo idénticas a otras locales (alumno, curso, fecha, décimas y nota).
    Por omisión se descartan las importadas."""

    id: str
    descripcion: str
    cantidad: int


@dataclass
class Dudoso:
    """Alumno del archivo que podría ser uno local con el mismo nombre. Por omisión no se une ni se importa."""

    id: str
    archivo: str
    local: str
    unir: bool


@dataclass
class PlanFusion:
    agregan: dict[str, int] = field(default_factory=dict)
    iguales: int = 0
    omitidos: int = 0
    avisos: list[str] = field(default_factory=list)
    conflictos: list[Conflicto] = field(default_factory=list)
    duplicados: list[DuplicadoParticipaciones] = field(default_factory=list)
    dudosos: list[Dudoso] = field(default_factory=list)
    # ---- operaciones (privado: lo consume `aplicar_plan`); `ref` = id de la decisión de la que dependen
    _cursos: list[tuple[ClaveCurso, str, bool]] = field(default_factory=list, repr=False)
    _alumnos_nuevos: dict[int, Alumno] = field(default_factory=dict, repr=False)
    _mapa: dict[int, int] = field(default_factory=dict, repr=False)  # alumno del archivo -> alumno local
    _cuentas: dict[int, str] = field(default_factory=dict, repr=False)  # alumno local -> cuenta a asignar
    _inscripciones: list[tuple[ClaveCurso, int, TipoInscripcion, str | None]] = field(default_factory=list, repr=False)
    _examenes: list[tuple[ClaveCurso, str]] = field(default_factory=list, repr=False)
    _ponderaciones: list[tuple[ClaveCurso, Ponderaciones, str | None]] = field(default_factory=list, repr=False)
    _participaciones: list[tuple[ClaveCurso, int, Participacion, str | None]] = field(default_factory=list, repr=False)
    _calificaciones: list[tuple[ClaveCurso, str, int, float, date, str | None]] = field(default_factory=list, repr=False)
    _tareas: list[tuple[ClaveCurso, int, float, date, str | None]] = field(default_factory=list, repr=False)
    _proyecto: list[tuple[ClaveCurso, int, float, date, str | None]] = field(default_factory=list, repr=False)
    _equipos: list[tuple[ClaveCurso, int, str, str, list[int], str | None]] = field(default_factory=list, repr=False)

    @property
    def total_agregan(self) -> int:
        return sum(self.agregan.values())

    def _sumar(self, entidad: str, n: int = 1) -> None:
        if n:
            self.agregan[entidad] = self.agregan.get(entidad, 0) + n


@dataclass
class ResultadoFusion:
    aplicados: dict[str, int]
    omitidos: int


# ------------------------------------------------------------------ lectura
@dataclass
class _CursoArchivo:
    curso: Curso
    ponderaciones: Ponderaciones | None
    examenes: list[Examen]
    inscritos: list[tuple[Alumno, TipoInscripcion]]
    participaciones: dict[int, list[Participacion]]
    calificaciones: dict[tuple[int, int], Calificacion]
    tareas: dict[int, CalificacionTareas]
    proyecto: dict[int, CalificacionProyecto]
    equipos: dict[int, tuple[str, str]]
    miembros: dict[int, list[int]]

    @property
    def clave(self) -> ClaveCurso:
        return (self.curso.ciclo, self.curso.materia, self.curso.grupo)


def _leer(repo: Repositorio) -> list[_CursoArchivo]:
    cursos = []
    for curso in repo.listar_cursos(incluir_archivados=True):
        examenes = repo.listar_examenes(curso.id)
        inscritos = [(r.alumno, r.tipo) for r in repo.resumen_curso(curso.id)]
        ids = [a.id for a, _ in inscritos]
        cursos.append(_CursoArchivo(
            curso=curso,
            ponderaciones=repo.obtener_ponderaciones(curso.id),
            examenes=examenes,
            inscritos=inscritos,
            participaciones={i: repo.listar_participaciones(curso.id, i) for i in ids},
            calificaciones={
                (e.id, i): c for e in examenes for i in ids if (c := repo.obtener_calificacion(e.id, i))
            },
            tareas={i: c for i in ids if (c := repo.obtener_tareas(curso.id, i))},
            proyecto={i: c for i in ids if (c := repo.obtener_proyecto(curso.id, i))},
            equipos=repo.datos_equipos(curso.id),
            miembros={n: [a.id for a in alumnos] for n, alumnos in repo.miembros_por_equipo(curso.id).items()},
        ))
    return cursos


# --------------------------------------------------------------------- plan
def calcular_plan(local: Repositorio, archivo: Repositorio, unir: frozenset[str] = frozenset()) -> PlanFusion:
    """Compara el archivo con la base local sin modificar ninguna. `unir`: ids de dudosos que la persona confirmó."""
    plan = PlanFusion()
    datos = _leer(archivo)
    nombres: dict[int, Alumno] = {}
    for d in datos:
        for alumno, _ in d.inscritos:
            nombres[alumno.id] = alumno
    omitidos = _emparejar_alumnos(local, nombres, unir, plan)

    for d in datos:
        _comparar_curso(local, d, plan, omitidos)
    plan.omitidos = len(omitidos)
    return plan


def _emparejar_alumnos(local: Repositorio, alumnos: dict[int, Alumno], unir: frozenset[str], plan: PlanFusion) -> set[int]:
    """Llena `plan._mapa`/`_alumnos_nuevos`/`_cuentas`. Devuelve los alumnos del archivo que no se importan."""
    omitidos: set[int] = set()
    usados: set[int] = set()
    for src_id, a in sorted(alumnos.items()):
        directo = local.buscar_alumno_por_cuenta(a.num_cuenta) if a.num_cuenta else None
        if directo is not None:
            plan._mapa[src_id] = directo.id
            usados.add(directo.id)
            continue
        candidatos = [
            c for c in local.buscar_alumnos_por_nombre(a.nombre_completo)
            if a.num_cuenta is None or c.num_cuenta is None
        ]
        if not candidatos:
            plan._alumnos_nuevos[src_id] = Alumno(None, a.nombre_completo, a.num_cuenta)
            continue
        if len(candidatos) > 1:
            plan.avisos.append(f"«{a.nombre_completo}» coincide con varios alumnos locales: no se importa.")
            omitidos.add(src_id)
            continue
        c = candidatos[0]
        clave = f"dudoso|{src_id}"
        plan.dudosos.append(Dudoso(
            clave,
            f"{a.nombre_completo} (cuenta {a.num_cuenta or 'sin cuenta'})",
            f"{c.nombre_completo} (cuenta {c.num_cuenta or 'sin cuenta'})",
            clave in unir,
        ))
        if clave not in unir or c.id in usados:
            omitidos.add(src_id)
            continue
        usados.add(c.id)
        plan._mapa[src_id] = c.id
        if c.num_cuenta is None and a.num_cuenta:
            plan._cuentas[c.id] = a.num_cuenta
    plan._sumar("alumnos", len(plan._alumnos_nuevos))
    return omitidos


def _comparar_curso(local: Repositorio, d: _CursoArchivo, plan: PlanFusion, omitidos: set[int]) -> None:
    clave = d.clave
    etiqueta = _etiqueta(clave)
    existente = local.buscar_curso_por_clave(*clave)
    if existente is None:
        plan._cursos.append((clave, d.curso.carrera, d.curso.archivado))
        plan._sumar("cursos")
    cid = existente.id if existente else None
    nombre_alumno = {a.id: a.nombre_completo for a, _ in d.inscritos}
    tipos = dict((a.id, t) for a, t in d.inscritos)
    activos = [i for i in nombre_alumno if i not in omitidos]

    def local_id(src: int) -> int | None:
        return plan._mapa.get(src)  # None = alumno nuevo (no existe aún aquí)

    # ---- ponderaciones
    if d.ponderaciones is not None:
        actual = local.obtener_ponderaciones(cid) if cid else None
        if actual is None:
            plan._ponderaciones.append((clave, d.ponderaciones, None))
            plan._sumar("ponderaciones")
        elif actual == d.ponderaciones:
            plan.iguales += 1
        else:
            ref = f"ponderacion|{clave}"
            plan.conflictos.append(Conflicto(ref, "Ponderaciones", etiqueta, _texto_pond(actual), _texto_pond(d.ponderaciones)))
            plan._ponderaciones.append((clave, d.ponderaciones, ref))

    # ---- exámenes
    nombres_locales = {e.nombre: e for e in local.listar_examenes(cid)} if cid else {}
    por_norma = {normalizar(n): e for n, e in nombres_locales.items()}
    examen_local: dict[int, Examen | None] = {}
    for e in d.examenes:
        encontrado = por_norma.get(normalizar(e.nombre))
        examen_local[e.id] = encontrado
        if encontrado is None:
            plan._examenes.append((clave, e.nombre))
            plan._sumar("exámenes")
        else:
            plan.iguales += 1

    # ---- inscripciones
    for src in activos:
        lid = local_id(src)
        actual = local.obtener_tipo_inscripcion(cid, lid) if (cid and lid) else None
        if actual is None:
            plan._inscripciones.append((clave, src, tipos[src], None))
            plan._sumar("inscripciones")
        elif actual == tipos[src]:
            plan.iguales += 1
        else:
            ref = f"inscripcion|{clave}|{src}"
            plan.conflictos.append(Conflicto(
                ref, "Tipo de inscripción", f"{nombre_alumno[src]} · {etiqueta}", actual.value, tipos[src].value))
            plan._inscripciones.append((clave, src, tipos[src], ref))

    # ---- participaciones (eventos): se agregan; las idénticas a las locales las decide la persona
    for src in activos:
        lid = local_id(src)
        locales = Counter(
            (p.fecha, p.decimas, p.nota) for p in local.listar_participaciones(cid, lid)
        ) if (cid and lid) else Counter()
        ref = f"participaciones|{clave}|{src}"
        coinciden = 0
        for p in sorted(d.participaciones.get(src, []), key=lambda p: (p.fecha, p.id)):
            llave = (p.fecha, p.decimas, p.nota)
            if locales[llave] > 0:
                locales[llave] -= 1
                coinciden += 1
                plan._participaciones.append((clave, src, p, ref))
            else:
                plan._participaciones.append((clave, src, p, None))
                plan._sumar("participaciones")
        if coinciden:
            plan.duplicados.append(DuplicadoParticipaciones(ref, f"{nombre_alumno[src]} · {etiqueta}", coinciden))

    # ---- calificaciones de exámenes
    for (examen_id, src), c in d.calificaciones.items():
        if src in omitidos:
            continue
        e = next(x for x in d.examenes if x.id == examen_id)
        lid, el = local_id(src), examen_local[examen_id]
        actual = local.obtener_calificacion(el.id, lid) if (el and lid) else None
        _valor(plan, plan._calificaciones, f"examen|{clave}|{e.nombre}|{src}", f"Examen «{e.nombre}»",
               f"{nombre_alumno[src]} · {etiqueta}", actual.puntos if actual else None, c.puntos,
               (clave, e.nombre, src, c.puntos, c.fecha), "calificaciones")

    # ---- tareas y proyecto
    for src, c in d.tareas.items():
        if src in omitidos:
            continue
        lid = local_id(src)
        actual = local.obtener_tareas(cid, lid) if (cid and lid) else None
        _valor(plan, plan._tareas, f"tareas|{clave}|{src}", "Tareas", f"{nombre_alumno[src]} · {etiqueta}",
               actual.puntos if actual else None, c.puntos, (clave, src, c.puntos, c.fecha), "tareas")
    for src, c in d.proyecto.items():
        if src in omitidos:
            continue
        lid = local_id(src)
        actual = local.obtener_proyecto(cid, lid) if (cid and lid) else None
        _valor(plan, plan._proyecto, f"proyecto|{clave}|{src}", "Proyecto final", f"{nombre_alumno[src]} · {etiqueta}",
               actual.puntos if actual else None, c.puntos, (clave, src, c.puntos, c.fecha), "proyecto")

    # ---- equipos
    locales_datos = local.datos_equipos(cid) if cid else {}
    locales_miembros = {n: {a.id for a in m} for n, m in local.miembros_por_equipo(cid).items()} if cid else {}
    for numero, (nombre, proyecto) in sorted(d.equipos.items()):
        miembros = [i for i in d.miembros.get(numero, []) if i not in omitidos]
        if numero not in locales_datos:
            plan._equipos.append((clave, numero, nombre, proyecto, miembros, None))
            plan._sumar("equipos")
            continue
        del_archivo = {plan._mapa.get(i) for i in miembros}
        mismos = del_archivo == locales_miembros.get(numero, set())
        if mismos and locales_datos[numero] == (nombre, proyecto):
            plan.iguales += 1
            continue
        ref = f"equipo|{clave}|{numero}"
        actuales = ", ".join(sorted(a.nombre_completo for a in local.miembros_por_equipo(cid).get(numero, []))) or "sin miembros"
        nuevos = ", ".join(sorted(nombre_alumno[i] for i in miembros)) or "sin miembros"
        plan.conflictos.append(Conflicto(
            ref, "Equipo", f"Equipo {numero} · {etiqueta}",
            f"{_texto_equipo(locales_datos[numero])}: {actuales}", f"{_texto_equipo((nombre, proyecto))}: {nuevos}"))
        plan._equipos.append((clave, numero, nombre, proyecto, miembros, ref))


def _texto_pond(p: Ponderaciones) -> str:
    return (f"participaciones {_num(p.participaciones)} % · exámenes {_num(p.examenes)} % · "
            f"tareas {_num(p.tareas)} % · proyecto {_num(p.proyecto)} %")


def _texto_equipo(datos: tuple[str, str]) -> str:
    nombre, proyecto = datos
    return " · ".join(x for x in (nombre, proyecto) if x) or "sin nombre"


def _valor(plan: PlanFusion, destino: list, ref: str, entidad: str, descripcion: str,
           actual: float | None, nuevo: float, operacion: tuple, contador: str) -> None:
    """Agrega, ignora (igual) o marca conflicto (distinto) un valor con una sola captura por alumno."""
    if actual is None:
        destino.append((*operacion, None))
        plan._sumar(contador)
    elif actual == nuevo:
        plan.iguales += 1
    else:
        plan.conflictos.append(Conflicto(ref, entidad, descripcion, _num(actual), _num(nuevo)))
        destino.append((*operacion, ref))


# ------------------------------------------------------------------- aplicar
def aplicar_plan(
    local: Repositorio, plan: PlanFusion, usar_importado: frozenset[str] = frozenset(),
    mantener_ambas: frozenset[str] = frozenset(),
) -> ResultadoFusion:
    """Ejecuta el plan en una sola transacción: si algo falla no queda nada a medias.
    Los conflictos solo se aplican si su id está en `usar_importado`; las participaciones idénticas
    a las locales, solo si su id está en `mantener_ambas`."""
    aplicados: Counter[str] = Counter()

    def vale(ref: str | None, elegidos: frozenset[str]) -> bool:
        return ref is None or ref in elegidos

    with local.transaccion():
        cursos: dict[ClaveCurso, int] = {}

        def curso_id(clave: ClaveCurso) -> int:
            if clave not in cursos:
                cursos[clave] = local.buscar_curso_por_clave(*clave).id
            return cursos[clave]

        for clave, carrera, archivado in plan._cursos:
            nuevo = local.insertar_curso(Curso(None, clave[0], carrera, clave[1], clave[2], archivado))
            cursos[clave] = nuevo.id
            aplicados["cursos"] += 1
        mapa = dict(plan._mapa)
        for src, alumno in plan._alumnos_nuevos.items():
            mapa[src] = local.insertar_alumno(Alumno(None, alumno.nombre_completo, alumno.num_cuenta)).id
            aplicados["alumnos"] += 1
        for lid, cuenta in plan._cuentas.items():
            alumno = local.obtener_alumno(lid)
            alumno.num_cuenta = cuenta
            local.actualizar_alumno(alumno)
        for clave, nombre in plan._examenes:
            local.insertar_examen(Examen(None, curso_id(clave), nombre))
            aplicados["exámenes"] += 1
        for clave, p, ref in plan._ponderaciones:
            if vale(ref, usar_importado):
                local.guardar_ponderaciones(curso_id(clave), p)
                aplicados["ponderaciones"] += 1
        for clave, src, tipo, ref in plan._inscripciones:
            if vale(ref, usar_importado):
                local.guardar_inscripcion(curso_id(clave), mapa[src], tipo)
                aplicados["inscripciones"] += 1
        for clave, src, p, ref in plan._participaciones:
            if ref is None or ref in mantener_ambas:
                local.insertar_participacion(Participacion(None, curso_id(clave), mapa[src], p.decimas, p.fecha, p.nota))
                aplicados["participaciones"] += 1
        for clave, nombre, src, puntos, fecha, ref in plan._calificaciones:
            if vale(ref, usar_importado):
                examen = local.buscar_examen_por_nombre(curso_id(clave), nombre)
                local.guardar_calificacion(Calificacion(examen.id, mapa[src], puntos, fecha))
                aplicados["calificaciones"] += 1
        for clave, src, puntos, fecha, ref in plan._tareas:
            if vale(ref, usar_importado):
                local.guardar_tareas(CalificacionTareas(curso_id(clave), mapa[src], puntos, fecha))
                aplicados["tareas"] += 1
        for clave, src, puntos, fecha, ref in plan._proyecto:
            if vale(ref, usar_importado):
                local.guardar_proyecto(CalificacionProyecto(curso_id(clave), mapa[src], puntos, fecha))
                aplicados["proyecto"] += 1
        for clave, numero, nombre, proyecto, miembros, ref in plan._equipos:
            if not vale(ref, usar_importado):
                continue
            cid = curso_id(clave)
            if ref is None:
                local.crear_equipo(cid, numero, nombre, proyecto)
            else:
                local.actualizar_equipo(cid, numero, nombre, proyecto)
                for alumno in local.miembros_por_equipo(cid).get(numero, []):
                    local.quitar_miembro_equipo(cid, alumno.id)
            for src in miembros:
                if local.equipo_de(cid, mapa[src]) is None:  # nunca se mueve a quien ya tiene otro equipo
                    local.agregar_miembro_equipo(cid, mapa[src], numero)
            aplicados["equipos"] += 1
    return ResultadoFusion(dict(aplicados), plan.omitidos)
