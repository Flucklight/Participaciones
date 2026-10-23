"""Apoyo para las pruebas de fusión de bases (datos ficticios)."""

from datetime import date

from core.database import conectar
from core.models import FilaLista, ListaInscripcion
from core.repository import Repositorio
from core.services import ServicioParticipaciones

D1, D2 = date(2027, 1, 10), date(2027, 1, 11)


def servicio(ruta):
    conexion = conectar(ruta)
    return ServicioParticipaciones(Repositorio(conexion)), conexion


def lista(materia="REDES", grupo="3001", alumnos=(("100000001", "ABREU SOLANO MARCOS"),
                                                  ("100000002", "ACOSTA ORTEGA ELENA"))):
    return ListaInscripcion(
        "2027-I", "ING", materia, grupo,
        [FilaLista(i, c, n) for i, (c, n) in enumerate(alumnos, 1)],
    )


def alumno(srv, curso, cuenta):
    return srv.buscar_alumnos_en_curso(curso.id, cuenta)[0]


def curso_de(srv, materia="REDES"):
    return next(c for c in srv.listar_cursos(incluir_archivados=True) if c.materia == materia)


def poblar_completo(srv):
    """Curso con todo: participaciones, examen, tareas, proyecto, ponderaciones y un equipo."""
    curso = srv.importar_lista(lista()).curso
    a, b = alumno(srv, curso, "100000001"), alumno(srv, curso, "100000002")
    srv.registrar_para_alumno(curso.id, a.id, 8, D1)
    srv.registrar_para_alumno(curso.id, a.id, -3, D2, "corrección")
    examen = srv.crear_examen(curso.id, "Parcial 1")
    srv.establecer_calificacion(curso.id, examen.id, a.id, 7.5, D1)
    srv.establecer_tareas(curso.id, a.id, 9, D1)
    srv.establecer_proyecto(curso.id, a.id, 8, D1)
    srv.establecer_ponderaciones(curso.id, 10, 30, 20, 40)
    srv.formar_equipo(curso.id, [a.id, b.id], "Los redes", "Proyecto X")
    return curso


def foto(srv):
    """Todo lo observable por curso, sin ids: total, final, equipo y participaciones de cada alumno."""
    resultado = {}
    for curso in srv.listar_cursos(incluir_archivados=True):
        filas = []
        for f in srv.resumen_curso(curso.id):
            historial = sorted((p.fecha, p.decimas, p.nota) for p in srv.historial(curso.id, f.alumno.id))
            filas.append((f.alumno.num_cuenta or f.alumno.nombre_completo, f.tipo.value, f.total, round(f.final, 6),
                          f.tareas, f.proyecto, f.equipo, tuple(sorted(f.calificaciones.values())), tuple(historial)))
        equipos = tuple(sorted((e.numero, e.nombre, e.proyecto) for e in srv.equipos_del_curso(curso.id)))
        resultado[(curso.ciclo, curso.materia, curso.grupo)] = (
            curso.archivado, tuple(sorted(filas)), equipos, srv.ponderaciones_de(curso.id),
            tuple(sorted(e.nombre for e in srv.listar_examenes(curso.id))))
    return resultado
