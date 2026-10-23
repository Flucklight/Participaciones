"""Proyecto final en la tabla del curso y en el historial del alumno (datos ficticios)."""

from datetime import date

import pytest

from tests.conftest import buscar_dialogo as _dialogo, hay_pantalla
from tests.test_ui_curso import _fila, curso_ui  # noqa: F401  (fixture)
from tests.test_ui_equipos import _en_proyecto, _formar
from tests.test_ui_historial import _filas_examenes, hist, hist_ex  # noqa: F401  (fixtures)

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


# ================= tabla del curso =================
def _columnas(v):
    return list(v._tabla["columns"])


def _celda(v, cuenta, columna):
    return v._tabla.item(str(_fila(v, cuenta).alumno.id), "values")[_columnas(v).index(columna)]


def test_la_columna_proyecto_va_entre_tareas_y_ultima(curso_ui):
    v = curso_ui.vista
    columnas = _columnas(v)
    assert columnas.index("tareas") + 1 == columnas.index("proyecto") < columnas.index("ultima")
    assert v._tabla.heading("proyecto", "text").startswith("Proyecto")


def test_la_columna_proyecto_va_antes_de_los_examenes(curso_ui):
    curso_ui.srv.crear_examen(curso_ui.curso.id, "Parcial 1")
    curso_ui.vista.recargar()
    columnas = _columnas(curso_ui.vista)
    assert columnas.index("proyecto") + 1 == columnas.index(next(c for c in columnas if c.startswith("examen_")))


def test_proyecto_vale_0_sin_captura_y_muestra_lo_capturado(curso_ui):
    v = curso_ui.vista
    assert _celda(v, "100000001", "proyecto") == "0"
    curso_ui.srv.registrar_proyecto(curso_ui.curso.id, "100000001", 9.5)
    v.recargar()
    assert _celda(v, "100000001", "proyecto") == "9.5" and _celda(v, "100000002", "proyecto") == "0"


def test_se_puede_ordenar_por_proyecto_de_mayor_a_menor_primero(curso_ui):
    srv = curso_ui.srv
    srv.registrar_proyecto(curso_ui.curso.id, "100000001", 5)
    srv.registrar_proyecto(curso_ui.curso.id, "100000003", 9)
    srv.registrar_proyecto(curso_ui.curso.id, "100000002", 7)
    v = curso_ui.vista
    v.recargar()
    v._ordenar_por("proyecto")
    nombres = [v._tabla.item(i, "values")[_columnas(v).index("nombre")] for i in v._tabla.get_children()]
    assert nombres[:3] == ["GARCIA LOPEZ ANA", "ACOSTA ORTEGA ELENA", "ABREU SOLANO MARCOS"]
    v._ordenar_por("proyecto")
    nombres = [v._tabla.item(i, "values")[_columnas(v).index("nombre")] for i in v._tabla.get_children()]
    assert nombres[-1] == "GARCIA LOPEZ ANA"


def test_en_proyecto_el_orden_de_columnas_incluye_equipo_y_proyecto(curso_ui):
    _formar(curso_ui, "100000001")
    v = _en_proyecto(curso_ui)
    columnas = _columnas(v)
    assert columnas[:5] == ["numero", "cuenta", "nombre", "equipo", "total"]
    assert columnas.index("proyecto") == columnas.index("tareas") + 1


def test_ordenar_por_proyecto_en_modo_proyecto_ordena_dentro_de_cada_equipo(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    curso_ui.srv.registrar_proyecto(curso_ui.curso.id, "100000001", 5)
    curso_ui.srv.registrar_proyecto(curso_ui.curso.id, "100000002", 9)
    v = _en_proyecto(curso_ui)
    v._ordenar_por("proyecto")
    nombres = [v._tabla.item(i, "values")[_columnas(v).index("nombre")] for i in v._tabla.get_children()]
    assert nombres[:3] == ["Equipo 1 · 2 alumnos", "ACOSTA ORTEGA ELENA", "ABREU SOLANO MARCOS"]


# ================= historial del alumno =================
def _seleccionar_proyecto(v):
    v._tabla_examenes.selection_set("proyecto")
    v.update()


def test_la_fila_proyecto_final_va_despues_de_tareas_y_vale_0_sin_captura(hist):
    filas = _filas_examenes(hist.vista)
    assert filas[0] == ("Tareas", "0", "—") and filas[1] == ("Proyecto final", "0", "—")


def test_la_fila_proyecto_muestra_el_equipo_si_tiene(hist):
    alumno = hist.alumno
    hist.srv.formar_equipo(hist.curso.id, [alumno.id])
    hist.vista.recargar()
    assert _filas_examenes(hist.vista)[1][0] == "Proyecto final · Equipo 1"


def test_la_fila_proyecto_muestra_calificacion_y_fecha(hist):
    hist.srv.establecer_proyecto(hist.curso.id, hist.alumno.id, 9.5, date(2026, 11, 2))
    hist.vista.recargar()
    assert _filas_examenes(hist.vista)[1] == ("Proyecto final", "9.5", "02/11/2026")


def test_calificar_el_proyecto_por_primera_vez(hist):
    v = hist.vista
    _seleccionar_proyecto(v)

    def capturar():
        d = _dialogo(hist.app)
        assert d._puntos.get() == ""
        d._puntos.insert(0, "88")
        d._fecha.delete(0, "end")
        d._fecha.insert(0, "20/11/2026")
        d._aceptar()

    hist.app.after(300, capturar)
    v.editar_calificacion()
    assert _filas_examenes(v)[1] == ("Proyecto final", "88", "20/11/2026")
    assert hist.srv.proyecto_de(hist.curso.id, hist.alumno.id).puntos == 88


def test_corregir_el_proyecto_parte_de_la_calificacion_actual(hist):
    v = hist.vista
    hist.srv.establecer_proyecto(hist.curso.id, hist.alumno.id, 70, date(2026, 10, 9))
    v.recargar()
    _seleccionar_proyecto(v)

    def editar():
        d = _dialogo(hist.app)
        assert d._puntos.get() == "70" and d._fecha.get() == "09/10/2026"
        d._puntos.delete(0, "end")
        d._puntos.insert(0, "105")  # sin tope
        d._aceptar()

    hist.app.after(300, editar)
    v.editar_calificacion()
    assert _filas_examenes(v)[1][:2] == ("Proyecto final", "105")


def test_el_dialogo_del_proyecto_valida_dentro_del_dialogo(hist):
    v = hist.vista
    _seleccionar_proyecto(v)

    def probar():
        d = _dialogo(hist.app)
        for puntos, fecha, mensaje in (("abc", "01/10/2026", "número"), ("-3", "01/10/2026", "mayor o igual a 0")):
            d._puntos.delete(0, "end")
            d._puntos.insert(0, puntos)
            d._fecha.delete(0, "end")
            d._fecha.insert(0, fecha)
            d._aceptar()
            assert mensaje in d._error.cget("text").lower()
        d.cancelar()

    hist.app.after(300, probar)
    v.editar_calificacion()
    assert _filas_examenes(v)[1][1] == "0"


def test_quitar_el_proyecto_pide_confirmacion_y_vuelve_a_0(hist):
    v = hist.vista
    hist.srv.establecer_proyecto(hist.curso.id, hist.alumno.id, 70, date(2026, 10, 9))
    v.recargar()
    _seleccionar_proyecto(v)
    hist.respuesta["si"] = False
    v.eliminar_calificacion()
    assert _filas_examenes(v)[1][1] == "70"  # cancelado: no pasa nada
    hist.respuesta["si"] = True
    v.eliminar_calificacion()
    assert _filas_examenes(v)[1] == ("Proyecto final", "0", "—")
    assert hist.srv.proyecto_de(hist.curso.id, hist.alumno.id) is None


def test_botones_segun_la_fila_del_proyecto(hist):
    v = hist.vista
    _seleccionar_proyecto(v)
    v._actualizar_botones_examenes()
    assert str(v._boton_calificar.cget("state")) == "normal"
    assert str(v._boton_quitar.cget("state")) == "disabled"  # no hay nada que quitar
    hist.srv.establecer_proyecto(hist.curso.id, hist.alumno.id, 70, date(2026, 10, 9))
    v.recargar()
    _seleccionar_proyecto(v)
    v._actualizar_botones_examenes()
    assert str(v._boton_quitar.cget("state")) == "normal"


def test_editar_el_proyecto_no_toca_tareas_ni_examenes(hist_ex):
    v = hist_ex.vista
    hist_ex.srv.establecer_tareas(hist_ex.curso.id, hist_ex.alumno.id, 70, date(2026, 10, 9))
    hist_ex.srv.establecer_proyecto(hist_ex.curso.id, hist_ex.alumno.id, 88, date(2026, 10, 10))
    v.recargar()
    assert _filas_examenes(v) == [
        ("Tareas", "70", "09/10/2026"), ("Proyecto final", "88", "10/10/2026"),
        ("Parcial 1", "42", "08/10/2026"), ("Final", "0", "—"),
    ]
    _seleccionar_proyecto(v)
    hist_ex.respuesta["si"] = True
    v.eliminar_calificacion()
    assert _filas_examenes(v)[0] == ("Tareas", "70", "09/10/2026")
    assert _filas_examenes(v)[2] == ("Parcial 1", "42", "08/10/2026")


def test_el_proyecto_no_altera_las_participaciones_ni_las_tarjetas(hist):
    v = hist.vista
    hist.srv.establecer_proyecto(hist.curso.id, hist.alumno.id, 88, date(2026, 10, 10))
    v.recargar()
    assert v._valores["total"].cget("text") == "5" and v._valores["registros"].cget("text") == "3"
