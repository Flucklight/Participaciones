"""Visitantes (R21): lo que se captura en el grupo que visita se guarda en el origen (datos ficticios)."""

from datetime import date
from types import SimpleNamespace

import pytest

from core.errores import ErrorDominio
from core.models import (
    ArchivoCalificaciones,
    ColumnaCalificaciones,
    EstadoRegistro,
    FilaCalificacion,
    TipoInscripcion,
)

REGULAR, OYENTE = TipoInscripcion.REGULAR, TipoInscripcion.OYENTE
HOY = date(2027, 3, 1)


@pytest.fixture
def g(servicio):
    """3001 (origen) y 3002 (visita). Ana: regular en 3001, visitante en 3002. Luis: regular en 3002."""
    a = servicio.crear_curso("2027-I", "Redes", "3001")
    b = servicio.crear_curso("2027-I", "Redes", "3002")
    ana = servicio.crear_alumno_en_curso(a.id, "Prueba Ana", REGULAR, "100000001")
    luis = servicio.crear_alumno_en_curso(b.id, "Prueba Luis", REGULAR, "100000002")
    servicio.inscribir_visitante(b.id, ana.id, a.id)
    return SimpleNamespace(a=a, b=b, ana=ana, luis=luis, srv=servicio, repo=servicio._repo)


# ---------------- participaciones ----------------
def test_la_participacion_se_guarda_en_el_origen_con_la_nota_del_grupo(g):
    r = g.srv.registrar_para_alumno(g.b.id, g.ana.id, 5, HOY)
    assert r.estado == EstadoRegistro.GUARDADO
    assert r.participacion.curso_id == g.a.id and r.participacion.nota == "Grupo 3002"
    assert r.guardado_en.id == g.a.id
    assert g.repo.listar_participaciones(g.b.id, g.ana.id) == []  # nada en el grupo que visita
    assert [p.decimas for p in g.repo.listar_participaciones(g.a.id, g.ana.id)] == [5]


def test_la_nota_escrita_se_conserva_despues_de_la_del_grupo(g):
    r = g.srv.registrar_para_alumno(g.b.id, g.ana.id, 5, HOY, "preguntó bien")
    assert r.participacion.nota == "Grupo 3002 · preguntó bien"


def test_en_el_origen_no_hay_nota_automatica_ni_aviso(g):
    r = g.srv.registrar_para_alumno(g.a.id, g.ana.id, 5, HOY)
    assert r.participacion.nota == "" and r.guardado_en is None
    r2 = g.srv.registrar_para_alumno(g.a.id, g.ana.id, 5, HOY, "en clase")
    assert r2.participacion.nota == "en clase"


def test_el_total_con_piso_es_el_mismo_desde_ambos_grupos(g):
    g.srv.registrar_para_alumno(g.b.id, g.ana.id, 5, date(2027, 3, 1))
    g.srv.registrar_para_alumno(g.a.id, g.ana.id, -10, date(2027, 3, 2))
    r = g.srv.registrar_para_alumno(g.b.id, g.ana.id, 5, date(2027, 3, 3))
    assert r.total == 5  # +5, -10, +5 con piso en 0
    assert g.srv.total_alumno(g.a.id, g.ana.id) == g.srv.total_alumno(g.b.id, g.ana.id) == 5


def test_registro_rapido_por_nombre_en_el_grupo_que_visita(g):
    r = g.srv.registrar(g.b.id, "prueba ana", 4, HOY)
    assert r.estado == EstadoRegistro.GUARDADO and r.guardado_en.id == g.a.id
    assert g.srv.total_alumno(g.a.id, g.ana.id) == 4


def test_deshacer_la_participacion_funciona_con_el_id_guardado(g):
    r = g.srv.registrar_para_alumno(g.b.id, g.ana.id, 5, HOY)
    g.srv.deshacer(r.participacion.id)
    assert g.srv.total_alumno(g.a.id, g.ana.id) == 0


# ---------------- exámenes ----------------
def _examen(g, curso, nombre="Parcial 1"):
    return g.srv.crear_examen(curso.id, nombre)


def test_el_examen_se_guarda_en_el_homonimo_del_origen(g):
    ea, eb = _examen(g, g.a), _examen(g, g.b)
    r = g.srv.registrar_calificacion_para_alumno(g.b.id, eb.id, g.ana.id, 8.5, HOY)
    assert r.estado == EstadoRegistro.GUARDADO and r.examen.id == ea.id and r.guardado_en.id == g.a.id
    assert g.repo.obtener_calificacion(ea.id, g.ana.id).puntos == 8.5
    assert g.repo.obtener_calificacion(eb.id, g.ana.id) is None  # nada en el examen del grupo que visita


def test_el_homonimo_se_busca_ignorando_mayusculas_y_acentos(g):
    ea, eb = _examen(g, g.a, "PARCIAL 1"), _examen(g, g.b, "parcial  1")
    g.srv.registrar_calificacion_para_alumno(g.b.id, eb.id, g.ana.id, 7, HOY)
    assert g.repo.obtener_calificacion(ea.id, g.ana.id).puntos == 7


def test_sin_examen_homonimo_no_se_guarda_nada_ni_se_crea_el_examen(g):
    eb = _examen(g, g.b, "Parcial 2")
    with pytest.raises(ErrorDominio, match="El grupo 3001 no tiene un examen «Parcial 2»"):
        g.srv.registrar_calificacion_para_alumno(g.b.id, eb.id, g.ana.id, 9, HOY)
    assert g.srv.listar_examenes(g.a.id) == []
    assert g.repo.obtener_calificacion(eb.id, g.ana.id) is None


def test_el_registro_rapido_de_examen_tambien_se_redirige(g):
    ea, eb = _examen(g, g.a), _examen(g, g.b)
    r = g.srv.registrar_calificacion(g.b.id, eb.id, "100000001", 9, HOY)
    assert r.estado == EstadoRegistro.GUARDADO and g.repo.obtener_calificacion(ea.id, g.ana.id).puntos == 9


def test_reemplazo_de_examen_pide_confirmar_y_deshacer_restaura(g):
    ea, eb = _examen(g, g.a), _examen(g, g.b)
    g.srv.registrar_calificacion_para_alumno(g.b.id, eb.id, g.ana.id, 6, HOY)
    pide = g.srv.registrar_calificacion_para_alumno(g.b.id, eb.id, g.ana.id, 9, HOY)
    assert pide.estado == EstadoRegistro.CONFIRMAR_REEMPLAZO and pide.calificacion_anterior.puntos == 6
    assert g.repo.obtener_calificacion(ea.id, g.ana.id).puntos == 6  # no cambió
    r = g.srv.registrar_calificacion_para_alumno(g.b.id, eb.id, g.ana.id, 9, HOY, reemplazar=True)
    assert g.repo.obtener_calificacion(ea.id, g.ana.id).puntos == 9
    g.srv.deshacer_calificacion(r.examen.id, g.ana.id, r.calificacion_anterior)
    assert g.repo.obtener_calificacion(ea.id, g.ana.id).puntos == 6


def test_deshacer_la_primera_calificacion_la_elimina_del_origen(g):
    ea, eb = _examen(g, g.a), _examen(g, g.b)
    r = g.srv.registrar_calificacion_para_alumno(g.b.id, eb.id, g.ana.id, 6, HOY)
    g.srv.deshacer_calificacion(r.examen.id, g.ana.id, r.calificacion_anterior)
    assert g.repo.obtener_calificacion(ea.id, g.ana.id) is None


def test_ver_corregir_y_quitar_la_calificacion_desde_el_grupo_que_visita(g):
    ea, eb = _examen(g, g.a), _examen(g, g.b)
    assert g.srv.calificacion_de(eb.id, g.ana.id) is None
    g.srv.establecer_calificacion(g.b.id, eb.id, g.ana.id, 5, HOY)
    assert g.srv.calificacion_de(eb.id, g.ana.id).puntos == 5  # lee la del origen
    assert g.srv.establecer_calificacion(g.b.id, eb.id, g.ana.id, 7, HOY).puntos == 7
    g.srv.eliminar_calificacion(eb.id, g.ana.id)
    assert g.repo.obtener_calificacion(ea.id, g.ana.id) is None
    with pytest.raises(ErrorDominio, match="no tiene calificación"):
        g.srv.eliminar_calificacion(eb.id, g.ana.id)


def test_el_promedio_de_examenes_es_el_del_origen(g):
    ea1, ea2 = _examen(g, g.a, "Parcial 1"), _examen(g, g.a, "Parcial 2")
    eb1 = _examen(g, g.b, "Parcial 1")
    g.srv.registrar_calificacion_para_alumno(g.b.id, eb1.id, g.ana.id, 80, HOY)
    # el promedio es sobre TODOS los exámenes del origen: un examen sin calificación vale 0
    assert g.srv.promedio_examenes_alumno(g.b.id, g.ana.id) == g.srv.promedio_examenes_alumno(g.a.id, g.ana.id) == 40


# ---------------- tareas ----------------
def test_tareas_se_guardan_en_el_origen(g):
    r = g.srv.registrar_tareas_para_alumno(g.b.id, g.ana.id, 90, HOY)
    assert r.estado == EstadoRegistro.GUARDADO and r.guardado_en.id == g.a.id
    assert g.repo.obtener_tareas(g.a.id, g.ana.id).puntos == 90
    assert g.repo.obtener_tareas(g.b.id, g.ana.id) is None
    assert g.srv.tareas_de(g.b.id, g.ana.id).puntos == 90


def test_reemplazo_de_tareas_y_deshacer(g):
    g.srv.registrar_tareas_para_alumno(g.b.id, g.ana.id, 60, HOY)
    pide = g.srv.registrar_tareas_para_alumno(g.b.id, g.ana.id, 80, HOY)
    assert pide.estado == EstadoRegistro.CONFIRMAR_REEMPLAZO and pide.anterior.puntos == 60
    r = g.srv.registrar_tareas_para_alumno(g.b.id, g.ana.id, 80, HOY, reemplazar=True)
    g.srv.deshacer_tareas(g.b.id, g.ana.id, r.anterior)
    assert g.repo.obtener_tareas(g.a.id, g.ana.id).puntos == 60
    g.srv.deshacer_tareas(g.b.id, g.ana.id, None)
    assert g.repo.obtener_tareas(g.a.id, g.ana.id) is None


def test_establecer_y_eliminar_tareas_desde_el_grupo_que_visita(g):
    assert g.srv.establecer_tareas(g.b.id, g.ana.id, 70, HOY).puntos == 70
    g.srv.eliminar_tareas(g.b.id, g.ana.id)
    assert g.repo.obtener_tareas(g.a.id, g.ana.id) is None
    with pytest.raises(ErrorDominio, match="no tiene calificación de tareas"):
        g.srv.eliminar_tareas(g.b.id, g.ana.id)


# ---------------- proyecto ----------------
def test_proyecto_de_un_alumno_se_guarda_en_el_origen(g):
    r = g.srv.registrar_proyecto_para_alumno(g.b.id, g.ana.id, 95, HOY)
    assert r.estado == EstadoRegistro.GUARDADO and r.en_otro_grupo == 1
    assert g.repo.obtener_proyecto(g.a.id, g.ana.id).puntos == 95
    assert g.repo.obtener_proyecto(g.b.id, g.ana.id) is None
    assert g.srv.proyecto_de(g.b.id, g.ana.id).puntos == 95


def test_equipo_del_grupo_que_visita_califica_al_visitante_en_su_origen(g):
    g.srv.formar_equipo(g.b.id, [g.ana.id, g.luis.id])
    r = g.srv.registrar_proyecto_equipo(g.b.id, 1, 80, HOY)
    assert r.en_otro_grupo == 1 and {a.id for a in r.alumnos} == {g.ana.id, g.luis.id}
    assert g.repo.obtener_proyecto(g.a.id, g.ana.id).puntos == 80  # la de Ana, en su origen
    assert g.repo.obtener_proyecto(g.b.id, g.luis.id).puntos == 80  # la de Luis, en su grupo
    assert g.repo.obtener_proyecto(g.b.id, g.ana.id) is None


def test_reemplazo_y_deshacer_del_equipo_restauran_a_todos(g):
    g.srv.formar_equipo(g.b.id, [g.ana.id, g.luis.id])
    g.srv.registrar_proyecto_para_alumno(g.b.id, g.ana.id, 50, HOY)
    pide = g.srv.registrar_proyecto_equipo(g.b.id, 1, 80, HOY)
    assert pide.estado == EstadoRegistro.CONFIRMAR_REEMPLAZO and pide.con_otra == 1
    assert g.repo.obtener_proyecto(g.b.id, g.luis.id) is None  # no se guardó nada
    r = g.srv.registrar_proyecto_equipo(g.b.id, 1, 80, HOY, reemplazar=True)
    g.srv.deshacer_proyecto(g.b.id, r.anteriores)
    assert g.repo.obtener_proyecto(g.a.id, g.ana.id).puntos == 50  # volvió la de Ana
    assert g.repo.obtener_proyecto(g.b.id, g.luis.id) is None      # la de Luis no existía


def test_establecer_y_eliminar_proyecto_desde_el_grupo_que_visita(g):
    assert g.srv.establecer_proyecto(g.b.id, g.ana.id, 90, HOY).puntos == 90
    g.srv.eliminar_proyecto(g.b.id, g.ana.id)
    assert g.repo.obtener_proyecto(g.a.id, g.ana.id) is None


# ---------------- importar tareas desde un archivo ----------------
def _archivo(*filas):
    return ArchivoCalificaciones(
        [ColumnaCalificaciones("G", "Tarea"), ColumnaCalificaciones("H")],
        [FilaCalificacion(ap, no, {"H": v}) for ap, no, v in filas],
    )


def test_importar_tareas_en_el_grupo_que_visita_guarda_en_el_origen_y_se_deshace(g):
    g.srv.establecer_tareas(g.a.id, g.ana.id, 50, HOY)
    archivo = _archivo(("PRUEBA", "ANA", 90.0), ("PRUEBA", "LUIS", 70.0))
    vista = g.srv.previsualizar_importacion_tareas(g.b.id, archivo, "H")
    linea_ana = next(l for l in vista.lineas if l.alumno.id == g.ana.id)
    assert linea_ana.anterior == 50  # la calificación actual de Ana, la del origen
    r = g.srv.importar_tareas(g.b.id, archivo, "H", fecha=HOY)
    assert g.repo.obtener_tareas(g.a.id, g.ana.id).puntos == 90
    assert g.repo.obtener_tareas(g.b.id, g.ana.id) is None
    assert g.repo.obtener_tareas(g.b.id, g.luis.id).puntos == 70
    g.srv.deshacer_importacion_tareas(g.b.id, r.anteriores)
    assert g.repo.obtener_tareas(g.a.id, g.ana.id).puntos == 50
    assert g.repo.obtener_tareas(g.b.id, g.luis.id) is None


# ---------------- nada queda duplicado ----------------
def test_ningun_dato_del_visitante_queda_en_el_grupo_que_visita(g):
    eb, ea = _examen(g, g.b), _examen(g, g.a)
    g.srv.registrar_para_alumno(g.b.id, g.ana.id, 5, HOY)
    g.srv.registrar_calificacion_para_alumno(g.b.id, eb.id, g.ana.id, 8, HOY)
    g.srv.registrar_tareas_para_alumno(g.b.id, g.ana.id, 9, HOY)
    g.srv.registrar_proyecto_para_alumno(g.b.id, g.ana.id, 7, HOY)
    con = g.repo.transaccion()
    for sql in (
        "SELECT COUNT(*) FROM participacion WHERE curso_id = ? AND alumno_id = ?",
        "SELECT COUNT(*) FROM calificacion_tareas WHERE curso_id = ? AND alumno_id = ?",
        "SELECT COUNT(*) FROM calificacion_proyecto WHERE curso_id = ? AND alumno_id = ?",
    ):
        assert con.execute(sql, (g.b.id, g.ana.id)).fetchone()[0] == 0, sql
    assert con.execute(
        "SELECT COUNT(*) FROM calificacion c JOIN examen e ON e.id = c.examen_id"
        " WHERE e.curso_id = ? AND c.alumno_id = ?", (g.b.id, g.ana.id)
    ).fetchone()[0] == 0
