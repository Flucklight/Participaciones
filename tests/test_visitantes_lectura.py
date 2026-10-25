"""Visitantes (R21): lo que se ve en el grupo que visita es lo del origen (datos ficticios)."""

from datetime import date
from types import SimpleNamespace

import pytest

from core.calificacion_final import redondear
from core.models import TipoInscripcion

REGULAR = TipoInscripcion.REGULAR
HOY = date(2027, 3, 1)


@pytest.fixture
def g(servicio):
    """3001 (origen) y 3002 (visita). Ana: regular en 3001, visitante en 3002. Luis: regular en 3002."""
    a = servicio.crear_curso("2027-I", "Redes", "3001")
    b = servicio.crear_curso("2027-I", "Redes", "3002")
    ana = servicio.crear_alumno_en_curso(a.id, "Prueba Ana", REGULAR, "100000001")
    luis = servicio.crear_alumno_en_curso(b.id, "Prueba Luis", REGULAR, "100000002")
    servicio.inscribir_visitante(b.id, ana.id, a.id)
    return SimpleNamespace(a=a, b=b, ana=ana, luis=luis, srv=servicio)


def fila(g, curso, alumno):
    return next(f for f in g.srv.resumen_curso(curso.id) if f.alumno.id == alumno.id)


def test_la_fila_del_visitante_trae_los_datos_del_origen(g):
    g.srv.registrar_para_alumno(g.b.id, g.ana.id, 5, date(2027, 3, 1))
    g.srv.registrar_para_alumno(g.a.id, g.ana.id, 3, date(2027, 3, 4))
    g.srv.establecer_tareas(g.b.id, g.ana.id, 90, HOY)
    g.srv.establecer_proyecto(g.a.id, g.ana.id, 70, HOY)
    f = fila(g, g.b, g.ana)
    assert f.tipo == TipoInscripcion.VISITANTE and f.curso_origen_id == g.a.id
    assert (f.total, f.n_participaciones, f.ultima_fecha) == (8, 2, date(2027, 3, 4))
    assert (f.tareas, f.proyecto) == (90, 70)
    origen = fila(g, g.a, g.ana)
    assert origen.tipo == REGULAR and origen.curso_origen_id is None
    assert (origen.total, origen.tareas, origen.proyecto) == (f.total, f.tareas, f.proyecto)


def test_el_visitante_sin_datos_vale_cero_y_el_resto_no_cambia(g):
    f = fila(g, g.b, g.ana)
    assert (f.total, f.n_participaciones, f.ultima_fecha, f.tareas, f.proyecto, f.final) == (0, 0, None, 0, 0, 0)
    luis = fila(g, g.b, g.luis)
    assert luis.tipo == REGULAR and luis.curso_origen_id is None
    assert len(g.srv.resumen_curso(g.b.id)) == 2


def test_la_final_es_la_del_origen_aunque_las_ponderaciones_difieran(g):
    g.srv.establecer_ponderaciones(g.a.id, 10, 0, 20, 40)   # origen: las de omisión
    g.srv.establecer_ponderaciones(g.b.id, 50, 0, 50, 0)    # el grupo que visita pondera distinto
    g.srv.registrar_para_alumno(g.a.id, g.ana.id, 10, HOY)  # 10 décimas = 100 puntos
    g.srv.establecer_tareas(g.a.id, g.ana.id, 80, HOY)
    g.srv.establecer_proyecto(g.a.id, g.ana.id, 50, HOY)
    esperada = 100 * 0.10 + 80 * 0.20 + 50 * 0.40  # = 46
    assert fila(g, g.a, g.ana).final == pytest.approx(esperada)
    assert fila(g, g.b, g.ana).final == pytest.approx(esperada)
    assert redondear(fila(g, g.b, g.ana).final) == 46


def test_las_columnas_de_examen_se_reindexan_por_nombre(g):
    a1, a2 = g.srv.crear_examen(g.a.id, "Parcial 1"), g.srv.crear_examen(g.a.id, "Parcial 2")
    b1, b3 = g.srv.crear_examen(g.b.id, "parcial 1"), g.srv.crear_examen(g.b.id, "Parcial 3")
    g.srv.establecer_calificacion(g.a.id, a1.id, g.ana.id, 80, HOY)
    g.srv.establecer_calificacion(g.a.id, a2.id, g.ana.id, 60, HOY)
    f = fila(g, g.b, g.ana)
    assert f.calificaciones == {b1.id: 80}          # «Parcial 2» no existe allá y «Parcial 3» no tiene nota
    assert b3.id not in f.calificaciones
    assert f.prom_examenes == 70                    # el promedio es el del origen (sobre sus dos exámenes)
    assert fila(g, g.a, g.ana).calificaciones == {a1.id: 80, a2.id: 60}


def test_la_final_incluye_el_promedio_de_examenes_del_origen(g):
    g.srv.establecer_ponderaciones(g.a.id, 0, 100, 0, 0)
    a1, a2 = g.srv.crear_examen(g.a.id, "Parcial 1"), g.srv.crear_examen(g.a.id, "Parcial 2")
    g.srv.crear_examen(g.b.id, "Parcial 1")
    g.srv.establecer_calificacion(g.a.id, a1.id, g.ana.id, 80, HOY)
    assert fila(g, g.b, g.ana).final == fila(g, g.a, g.ana).final == 40  # (80 + 0) / 2


def test_el_equipo_de_la_fila_es_el_del_grupo_que_se_esta_viendo(g):
    g.srv.formar_equipo(g.b.id, [g.ana.id, g.luis.id])
    assert fila(g, g.b, g.ana).equipo == 1
    assert fila(g, g.a, g.ana).equipo is None


def test_el_historial_es_el_mismo_desde_cualquiera_de_los_dos_grupos(g):
    g.srv.registrar_para_alumno(g.b.id, g.ana.id, 5, date(2027, 3, 1))
    g.srv.registrar_para_alumno(g.a.id, g.ana.id, -10, date(2027, 3, 2))
    g.srv.registrar_para_alumno(g.b.id, g.ana.id, 5, date(2027, 3, 3))
    desde_a, desde_b = g.srv.historial(g.a.id, g.ana.id), g.srv.historial(g.b.id, g.ana.id)
    assert [(p.id, p.decimas) for p in desde_a] == [(p.id, p.decimas) for p in desde_b]
    assert len(desde_b) == 3
    det_a, det_b = g.srv.historial_detallado(g.a.id, g.ana.id), g.srv.historial_detallado(g.b.id, g.ana.id)
    assert [(l.aplicado, l.acumulado) for l in det_a] == [(l.aplicado, l.acumulado) for l in det_b] == [(5, 5), (-5, 0), (5, 5)]


def test_historial_de_examenes_y_desglose_desde_el_grupo_que_visita(g):
    a1 = g.srv.crear_examen(g.a.id, "Parcial 1")
    g.srv.establecer_calificacion(g.a.id, a1.id, g.ana.id, 90, HOY)
    g.srv.establecer_tareas(g.a.id, g.ana.id, 80, HOY)
    lineas = g.srv.historial_examenes(g.b.id, g.ana.id)
    assert [(l.examen.id, l.calificacion.puntos) for l in lineas] == [(a1.id, 90)]
    assert g.srv.desglose_final(g.b.id, g.ana.id) == g.srv.desglose_final(g.a.id, g.ana.id)


def test_ordenar_y_buscar_siguen_funcionando_con_visitantes(g):
    nombres = [f.alumno.nombre_completo for f in g.srv.resumen_curso(g.b.id)]
    assert nombres == ["PRUEBA ANA", "PRUEBA LUIS"]
    assert [a.id for a in g.srv.buscar_alumnos_en_curso(g.b.id, "prueba ana")] == [g.ana.id]


def test_origen_y_visita_cruzados_no_se_enredan(g):
    """Luis es regular en 3002 y visita el 3001 mientras Ana visita el 3002 (cada uno con su origen)."""
    g.srv.inscribir_visitante(g.a.id, g.luis.id, g.b.id)
    g.srv.registrar_para_alumno(g.b.id, g.ana.id, 4, HOY)
    g.srv.registrar_para_alumno(g.a.id, g.luis.id, 2, HOY)
    assert (fila(g, g.b, g.ana).total, fila(g, g.a, g.ana).total) == (4, 4)
    assert (fila(g, g.a, g.luis).total, fila(g, g.b, g.luis).total) == (2, 2)
    assert fila(g, g.a, g.luis).tipo == TipoInscripcion.VISITANTE
    assert fila(g, g.b, g.luis).tipo == REGULAR
