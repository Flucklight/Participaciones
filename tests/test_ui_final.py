"""Calificación final en la tabla del curso: columnas «Final» y «Final /10» (datos ficticios)."""

import pytest

from core.models import TipoInscripcion
from tests.conftest import hay_pantalla
from tests.test_ui_curso import _fila, curso_ui  # noqa: F401  (fixture)
from tests.test_ui_equipos import _en_proyecto, _formar

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def _columnas(v):
    return list(v._tabla["columns"])


def _celda(v, cuenta, columna):
    return v._tabla.item(str(_fila(v, cuenta).alumno.id), "values")[_columnas(v).index(columna)]


def _nombres(v):
    i = _columnas(v).index("nombre")
    return [v._tabla.item(f, "values")[i] for f in v._tabla.get_children() if not f.startswith("equipo_")]


def _con_todo(ui, cuenta="100000001", decimas=8, examen=70, tareas=90, proyecto=85):
    srv, cid = ui.srv, ui.curso.id
    srv.registrar(cid, cuenta, decimas)
    examenes = srv.listar_examenes(cid)
    e = examenes[0] if examenes else srv.crear_examen(cid, "Parcial 1")
    srv.registrar_calificacion(cid, e.id, cuenta, examen)
    srv.registrar_tareas(cid, cuenta, tareas)
    srv.registrar_proyecto(cid, cuenta, proyecto)
    srv.establecer_ponderaciones(cid, 10, 30, 20, 40)
    ui.vista.recargar()


def test_las_columnas_van_despues_de_los_examenes_y_antes_de_ultima(curso_ui):
    curso_ui.srv.crear_examen(curso_ui.curso.id, "Parcial 1")
    curso_ui.vista.recargar()
    c = _columnas(curso_ui.vista)
    examen = next(x for x in c if x.startswith("examen_"))
    assert c.index("proyecto") < c.index(examen) < c.index("final") + 0 < c.index("final10") < c.index("ultima")
    assert c.index("final") + 1 == c.index("final10") and c.index("final10") + 1 == c.index("ultima")


def test_sin_examenes_siguen_despues_de_proyecto_y_antes_de_ultima(curso_ui):
    c = _columnas(curso_ui.vista)
    assert c[-3:] == ["final", "final10", "ultima"] and c.index("proyecto") + 1 == c.index("final")


def test_los_encabezados_dicen_final_y_final_10(curso_ui):
    v = curso_ui.vista
    assert v._tabla.heading("final", "text").startswith("Final") and "/10" in v._tabla.heading("final10", "text")


def test_el_ejemplo_base_muestra_81_y_8_1(curso_ui):
    _con_todo(curso_ui)
    v = curso_ui.vista
    assert _celda(v, "100000001", "final") == "81" and _celda(v, "100000001", "final10") == "8.1"


def test_sin_captura_la_final_es_0(curso_ui):
    v = curso_ui.vista
    assert _celda(v, "100000002", "final") == "0" and _celda(v, "100000002", "final10") == "0.0"


def test_se_redondea_al_mostrar_pero_la_equivalencia_sale_del_valor_exacto(curso_ui):
    srv, cid = curso_ui.srv, curso_ui.curso.id
    srv.establecer_ponderaciones(cid, 0, 0, 100, 0)
    srv.registrar_tareas(cid, "100000001", 84.46)   # final exacta 84.46: se ve 84 y 8.4
    srv.registrar_tareas(cid, "100000002", 84.54)   # 84.54: se ve 85 y 8.5
    srv.registrar_tareas(cid, "100000003", 87.5)    # mitad hacia arriba: 88 y 8.8
    curso_ui.vista.recargar()
    v = curso_ui.vista
    assert (_celda(v, "100000001", "final"), _celda(v, "100000001", "final10")) == ("84", "8.4")
    assert (_celda(v, "100000002", "final"), _celda(v, "100000002", "final10")) == ("85", "8.5")
    assert (_celda(v, "100000003", "final"), _celda(v, "100000003", "final10")) == ("88", "8.8")


def test_la_final_pasa_de_100_con_puntos_extra(curso_ui):
    srv, cid = curso_ui.srv, curso_ui.curso.id
    srv.establecer_ponderaciones(cid, 10, 30, 20, 50)  # 110 %
    srv.registrar_proyecto(cid, "100000001", 100)
    srv.registrar_tareas(cid, "100000001", 100)
    srv.registrar(cid, "100000001", 10)
    curso_ui.vista.recargar()
    assert _celda(curso_ui.vista, "100000001", "final") == "80"  # 10 % de 100 + 0 + 20 % de 100 + 50 % de 100


def test_ordena_de_mayor_a_menor_primero_y_luego_al_reves(curso_ui):
    srv, cid = curso_ui.srv, curso_ui.curso.id
    srv.establecer_ponderaciones(cid, 0, 0, 100, 0)
    srv.registrar_tareas(cid, "100000001", 50)
    srv.registrar_tareas(cid, "100000003", 90)
    srv.registrar_tareas(cid, "100000002", 70)
    v = curso_ui.vista
    v.recargar()
    v._ordenar_por("final")
    assert _nombres(v)[:3] == ["GARCIA LOPEZ ANA", "ACOSTA ORTEGA ELENA", "ABREU SOLANO MARCOS"]
    v._ordenar_por("final")
    assert _nombres(v)[-1] == "GARCIA LOPEZ ANA"


def test_ordena_por_el_valor_exacto_no_por_el_redondeado(curso_ui):
    srv, cid = curso_ui.srv, curso_ui.curso.id
    srv.establecer_ponderaciones(cid, 0, 0, 100, 0)
    srv.registrar_tareas(cid, "100000001", 84.4)   # los dos se ven como 84
    srv.registrar_tareas(cid, "100000002", 84.46)
    v = curso_ui.vista
    v.recargar()
    v._ordenar_por("final")
    assert _celda(v, "100000001", "final") == _celda(v, "100000002", "final") == "84"
    assert _nombres(v)[:2] == ["ACOSTA ORTEGA ELENA", "ABREU SOLANO MARCOS"]


def test_final_10_ordena_igual_que_final(curso_ui):
    srv, cid = curso_ui.srv, curso_ui.curso.id
    srv.establecer_ponderaciones(cid, 0, 0, 100, 0)
    srv.registrar_tareas(cid, "100000001", 50)
    srv.registrar_tareas(cid, "100000002", 90)
    v = curso_ui.vista
    v.recargar()
    v._ordenar_por("final10")
    assert _nombres(v)[:2] == ["ACOSTA ORTEGA ELENA", "ABREU SOLANO MARCOS"]


def test_van_centradas_y_los_oyentes_tambien_la_tienen(curso_ui):
    srv, cid = curso_ui.srv, curso_ui.curso.id
    oyente = srv.crear_alumno_en_curso(cid, "OYENTE UNO", TipoInscripcion.OYENTE)
    srv.registrar_tareas_para_alumno(cid, oyente.id, 50)
    v = curso_ui.vista
    v.recargar()
    for columna in ("final", "final10"):
        assert str(v._tabla.column(columna, "anchor")) == "center"
    fila = next(f for f in v._filas if f.alumno.id == oyente.id)
    assert v._tabla.item(str(fila.alumno.id), "values")[_columnas(v).index("final")] == "10"  # 20 % de 50


def test_en_modo_proyecto_agrupado_tambien_estan_las_columnas(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    _con_todo(curso_ui)
    v = _en_proyecto(curso_ui)
    assert _celda(v, "100000001", "final") == "81"
    assert v._tabla.item("equipo_1", "values")[_columnas(v).index("final")] == ""  # el encabezado no tiene


def test_cambiar_las_ponderaciones_actualiza_la_tabla(curso_ui):
    _con_todo(curso_ui)
    curso_ui.srv.establecer_ponderaciones(curso_ui.curso.id, 10, 30, 20, 50)
    curso_ui.vista.recargar()
    assert _celda(curso_ui.vista, "100000001", "final") == "90"  # 81 + 10 % de 85 = 89.5 → 90
