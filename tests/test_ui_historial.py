"""Pantalla Historial: tarjetas, tabla editable, selector de curso y acciones del alumno."""

from datetime import date
from tkinter import messagebox
from types import SimpleNamespace

import pytest

from core.models import FilaLista, ListaInscripcion, TipoInscripcion
from tests.conftest import buscar_dialogo as _dialogo, hay_pantalla

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


@pytest.fixture
def hist(ui, monkeypatch):
    """Historial abierto de un alumno con 3 participaciones (una toca el piso de 0)."""
    lista = ListaInscripcion(
        "2027-I", "ING", "REDES", "3001",
        [FilaLista(1, "100000001", "ABREU SOLANO MARCOS"),
         FilaLista(2, "100000002", "ACOSTA ORTEGA ELENA")],
    )
    srv = ui.srv
    curso = srv.importar_lista(lista).curso
    r = srv.registrar(curso.id, "100000001", 10, date(2026, 10, 5))
    srv.agregar_participacion(curso.id, r.alumno.id, -25, date(2026, 10, 6), "se pasó")
    srv.agregar_participacion(curso.id, r.alumno.id, 5, date(2026, 10, 7), "dudas")
    ui.curso, ui.alumno = curso, r.alumno
    ui.respuesta = {"si": True}
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: ui.respuesta["si"])
    ui.app.abrir_historial(curso.id, r.alumno.id)
    ui.app.update()
    ui.vista = ui.app._vista
    return ui


def _filas(v):
    return [v._tabla.item(i, "values") for i in v._tabla.get_children()]


def test_muestra_nombre_tarjetas_y_filas_con_total_acumulado(hist):
    v = hist.vista
    assert v._titulo.cget("text") == "ABREU SOLANO MARCOS"
    assert "100000001" in v._subtitulo.cget("text") and "Regular" in v._subtitulo.cget("text")
    assert v._valores["total"].cget("text") == "5"
    assert v._valores["registros"].cget("text") == "3"
    assert v._valores["ultima"].cget("text") == "07/10/2026"
    # más reciente primero: (fecha, décimas, efecto, total, nota)
    assert _filas(v)[0][:4] == ("07/10/2026", "+5", "+5", "5")
    assert _filas(v)[1][:4] == ("06/10/2026", "-25", "-10  ⚑", "0")
    assert "mínimo de 0" in v._aviso.cget("text")
    assert "piso" in v._tabla.item(v._tabla.get_children()[1], "tags")


def test_agregar_participacion_con_fecha_anterior(hist):
    v = hist.vista

    def alta():
        d = _dialogo(hist.app)
        d._decimas.insert(0, "20")
        d._fecha.delete(0, "end")
        d._fecha.insert(0, "01/09/2026")
        d._nota.insert(0, "olvidada")
        d._aceptar()

    hist.app.after(300, alta)
    v.agregar_participacion()
    # cronológicamente: +20 (1/sep), +10, -25, +5  →  20, 30, 5, 10
    assert v._valores["total"].cget("text") == "10"
    assert v._valores["registros"].cget("text") == "4"
    assert _filas(v)[-1][:2] == ("01/09/2026", "+20")  # la más antigua queda al final


def test_dialogo_valida_decimas_y_fecha_dentro_del_dialogo(hist):
    v = hist.vista

    def probar():
        d = _dialogo(hist.app)
        d._decimas.insert(0, "abc")
        d._aceptar()
        assert "número" in d._error.cget("text")
        d._decimas.delete(0, "end")
        d._decimas.insert(0, "5")
        d._fecha.delete(0, "end")
        d._fecha.insert(0, "31/02/2026")
        d._aceptar()
        assert "fecha" in d._error.cget("text").lower()
        d._decimas.delete(0, "end")
        d._decimas.insert(0, "0")
        d._fecha.delete(0, "end")
        d._fecha.insert(0, "01/10/2026")
        d._aceptar()  # el servicio rechaza el cero y el error sigue en el diálogo
        assert "distinto de cero" in d._error.cget("text")
        d.cancelar()

    hist.app.after(300, probar)
    v.agregar_participacion()
    assert v._valores["registros"].cget("text") == "3"


def test_editar_participacion_recalcula_total(hist):
    v = hist.vista
    v._tabla.selection_set(v._tabla.get_children()[1])  # la de -25
    v.update()

    def editar():
        d = _dialogo(hist.app)
        assert d._decimas.get() == "-25" and d._fecha.get() == "06/10/2026"
        d._decimas.delete(0, "end")
        d._decimas.insert(0, "-3")
        d._aceptar()

    hist.app.after(300, editar)
    v.editar_participacion()
    # 10, -3, +5 -> 12 (ya no toca el piso)
    assert v._valores["total"].cget("text") == "12"
    assert "mínimo" not in v._aviso.cget("text")


def test_eliminar_participacion_con_confirmacion(hist):
    v = hist.vista
    v._tabla.selection_set(v._tabla.get_children()[1])
    v.update()
    hist.respuesta["si"] = False
    v.eliminar_participacion()
    assert v._valores["registros"].cget("text") == "3"  # cancelado: no pasa nada

    hist.respuesta["si"] = True
    v.eliminar_participacion()
    assert v._valores["registros"].cget("text") == "2"
    assert v._valores["total"].cget("text") == "15"  # 10 + 5


def test_botones_editar_y_eliminar_solo_con_seleccion(hist):
    v = hist.vista
    v._tabla.selection_remove(*v._tabla.selection())
    v._actualizar_botones()
    assert str(v._boton_editar.cget("state")) == "disabled"
    v._tabla.selection_set(v._tabla.get_children()[0])
    v._actualizar_botones()
    assert str(v._boton_editar.cget("state")) == "normal"
    v._tabla.selection_remove(*v._tabla.selection())
    v.editar_participacion()  # sin selección: no hace nada ni falla
    v.eliminar_participacion()


def test_selector_cambia_de_curso(hist):
    srv = hist.srv
    otro = srv.crear_curso("2027-II", "Otra materia", "9")
    srv.inscribir_alumno_existente(otro.id, hist.alumno.id)
    srv.registrar_para_alumno(otro.id, hist.alumno.id, 40)
    hist.app.abrir_historial(hist.curso.id, hist.alumno.id)
    hist.app.update()
    v = hist.app._vista
    assert len(v._etiquetas) == 2
    etiqueta = next(e for e, i in v._etiquetas.items() if i == otro.id)
    v._cambiar_curso(etiqueta)
    assert v._valores["total"].cget("text") == "40" and v._valores["registros"].cget("text") == "1"


def test_editar_datos_del_alumno(hist):
    v = hist.vista

    def editar():
        d = _dialogo(hist.app)
        d._nombre.delete(0, "end")
        d._nombre.insert(0, "abreu solano marcos jr")
        d._cuenta.delete(0, "end")
        d._cuenta.insert(0, "100000002")  # pertenece a otro alumno
        d._aceptar()
        assert "ya pertenece" in d._error.cget("text")
        d._cuenta.delete(0, "end")
        d._cuenta.insert(0, "100000011")
        d._aceptar()

    hist.app.after(300, editar)
    v.editar_alumno()
    assert v._titulo.cget("text") == "ABREU SOLANO MARCOS JR"
    assert "100000011" in v._subtitulo.cget("text")


def test_convertir_oyente_en_regular_conserva_historial(hist):
    srv = hist.srv
    oyente = srv.crear_alumno_en_curso(hist.curso.id, "Pablo Oyente")
    srv.registrar_para_alumno(hist.curso.id, oyente.id, 15)
    hist.app.abrir_historial(hist.curso.id, oyente.id)
    hist.app.update()
    v = hist.app._vista
    assert "Oyente" in v._subtitulo.cget("text") and "sin asignar" in v._subtitulo.cget("text")
    assert v._boton_regular.winfo_manager() == "pack"

    v.convertir_en_regular()
    assert "Regular" in v._subtitulo.cget("text")
    assert v._boton_regular.winfo_manager() == ""  # el botón desaparece
    assert v._valores["total"].cget("text") == "15"
    assert srv.tipo_inscripcion(hist.curso.id, oyente.id) == TipoInscripcion.REGULAR


def test_desde_la_tabla_del_curso_el_doble_clic_abre_el_historial_y_el_boton_regresa(hist):
    app = hist.app
    app.abrir_curso(hist.curso.id)
    app.update()
    vc = app._vista
    x, y, _w, h = vc._tabla.bbox(str(hist.alumno.id))
    vc._al_doble_clic(SimpleNamespace(x=x + 20, y=y + h // 2))
    app.update()
    vh = app._vista
    assert vh.__class__.__name__ == "VistaHistorial"
    assert vh._titulo.cget("text") == "ABREU SOLANO MARCOS"

    app.abrir_curso(vh._curso_id)  # lo que hace el botón «← Curso»
    app.update()
    assert app._vista.__class__.__name__ == "VistaCurso"


def test_doble_clic_en_el_encabezado_no_abre_nada(hist):
    app = hist.app
    app.abrir_curso(hist.curso.id)
    app.update()
    app._vista._al_doble_clic(SimpleNamespace(x=30, y=5))
    assert app._vista.__class__.__name__ == "VistaCurso"


# ---------------- sección «Exámenes» ----------------
def _filas_examenes(v):
    return [v._tabla_examenes.item(i, "values") for i in v._tabla_examenes.get_children()]


@pytest.fixture
def hist_ex(hist):
    """El historial anterior, con dos exámenes en el curso: Abreu tiene 42 en el Parcial 1."""
    srv, curso, alumno = hist.srv, hist.curso, hist.alumno
    hist.parcial = srv.crear_examen(curso.id, "Parcial 1")
    hist.final = srv.crear_examen(curso.id, "Final")
    srv.establecer_calificacion(curso.id, hist.parcial.id, alumno.id, 42, date(2026, 10, 8))
    hist.vista.recargar()
    hist.app.update()
    return hist


def _seleccionar_examen(v, examen):
    v._tabla_examenes.selection_set(str(examen.id))
    v.update()


def test_la_seccion_lista_cada_examen_con_su_calificacion_o_0(hist_ex):
    filas = _filas_examenes(hist_ex.vista)
    assert filas == [("Tareas", "0", "—"), ("Proyecto final", "0", "—"), ("Parcial 1", "42", "08/10/2026"), ("Final", "0", "—")]


def test_sin_examenes_la_seccion_avisa_que_no_hay(hist):
    v = hist.vista
    assert _filas_examenes(v) == [("Tareas", "0", "—"), ("Proyecto final", "0", "—")]  # esas dos filas siempre están
    assert "no tiene exámenes" in v._aviso_examenes.cget("text")


def test_la_seccion_no_altera_las_participaciones_ni_las_tarjetas(hist_ex):
    v = hist_ex.vista
    assert v._valores["total"].cget("text") == "5" and v._valores["registros"].cget("text") == "3"
    assert len(_filas(v)) == 3


def test_editar_una_calificacion_existente(hist_ex):
    v = hist_ex.vista
    _seleccionar_examen(v, hist_ex.parcial)

    def editar():
        d = _dialogo(hist_ex.app)
        assert d._puntos.get() == "42" and d._fecha.get() == "08/10/2026"
        d._puntos.delete(0, "end")
        d._puntos.insert(0, "47.5")
        d._aceptar()

    hist_ex.app.after(300, editar)
    v.editar_calificacion()
    assert _filas_examenes(v)[2][:2] == ("Parcial 1", "47.5")
    assert hist_ex.srv.calificacion_de(hist_ex.parcial.id, hist_ex.alumno.id).puntos == 47.5


def test_calificar_un_examen_sin_capturar(hist_ex):
    v = hist_ex.vista
    _seleccionar_examen(v, hist_ex.final)

    def capturar():
        d = _dialogo(hist_ex.app)
        assert d._puntos.get() == ""
        d._puntos.insert(0, "88")
        d._fecha.delete(0, "end")
        d._fecha.insert(0, "15/10/2026")
        d._aceptar()

    hist_ex.app.after(300, capturar)
    v.editar_calificacion()
    assert _filas_examenes(v)[3] == ("Final", "88", "15/10/2026")


def test_el_dialogo_de_calificacion_valida_dentro_del_dialogo(hist_ex):
    v = hist_ex.vista
    _seleccionar_examen(v, hist_ex.final)

    def probar():
        d = _dialogo(hist_ex.app)
        for puntos, fecha, mensaje in (("abc", "01/10/2026", "número"),
                                       ("-3", "01/10/2026", "mayor o igual a 0"),
                                       ("5", "31/02/2026", "fecha")):
            d._puntos.delete(0, "end")
            d._puntos.insert(0, puntos)
            d._fecha.delete(0, "end")
            d._fecha.insert(0, fecha)
            d._aceptar()
            assert mensaje in d._error.cget("text").lower()
        d.cancelar()

    hist_ex.app.after(300, probar)
    v.editar_calificacion()
    assert _filas_examenes(v)[3][1] == "0"


def test_eliminar_una_calificacion_pide_confirmacion(hist_ex):
    v = hist_ex.vista
    _seleccionar_examen(v, hist_ex.parcial)
    hist_ex.respuesta["si"] = False
    v.eliminar_calificacion()
    assert _filas_examenes(v)[2][1] == "42"  # cancelado: no pasa nada
    hist_ex.respuesta["si"] = True
    v.eliminar_calificacion()
    assert _filas_examenes(v)[2] == ("Parcial 1", "0", "—")


def test_botones_de_examenes_segun_la_seleccion(hist_ex):
    v = hist_ex.vista
    v._actualizar_botones_examenes()
    assert str(v._boton_calificar.cget("state")) == "disabled"
    assert str(v._boton_quitar.cget("state")) == "disabled"
    _seleccionar_examen(v, hist_ex.final)  # sin capturar: se puede calificar, no quitar
    v._actualizar_botones_examenes()
    assert str(v._boton_calificar.cget("state")) == "normal"
    assert str(v._boton_quitar.cget("state")) == "disabled"
    _seleccionar_examen(v, hist_ex.parcial)
    v._actualizar_botones_examenes()
    assert str(v._boton_quitar.cget("state")) == "normal"


def test_cambiar_de_curso_muestra_los_examenes_de_ese_curso(hist_ex):
    v = hist_ex.vista
    otro = hist_ex.srv.crear_curso("2027-II", "Bases de datos", "2002")
    hist_ex.srv.inscribir_alumno_existente(otro.id, hist_ex.alumno.id, TipoInscripcion.REGULAR)
    hist_ex.srv.crear_examen(otro.id, "Unico")
    v.destroy()
    hist_ex.app.abrir_historial(otro.id, hist_ex.alumno.id)
    hist_ex.app.update()
    assert _filas_examenes(hist_ex.app._vista) == [("Tareas", "0", "—"), ("Proyecto final", "0", "—"), ("Unico", "0", "—")]


# ---------------- fila «Tareas» ----------------
def _seleccionar_tareas(v):
    v._tabla_examenes.selection_set("tareas")
    v.update()


def test_la_seccion_se_llama_examenes_tareas_y_proyecto(hist):
    assert hist.vista._titulo_calificaciones.cget("text") == "Exámenes, tareas y proyecto"


def test_la_fila_tareas_muestra_la_calificacion_y_su_fecha(hist):
    v = hist.vista
    hist.srv.establecer_tareas(hist.curso.id, hist.alumno.id, 84.5, date(2026, 10, 9))
    v.recargar()
    assert _filas_examenes(v)[0] == ("Tareas", "84.5", "09/10/2026")


def test_tareas_no_altera_las_participaciones_ni_las_tarjetas(hist):
    v = hist.vista
    hist.srv.establecer_tareas(hist.curso.id, hist.alumno.id, 84.5, date(2026, 10, 9))
    v.recargar()
    assert v._valores["total"].cget("text") == "5" and v._valores["registros"].cget("text") == "3"
    assert len(_filas(v)) == 3


def test_calificar_tareas_por_primera_vez(hist):
    v = hist.vista
    _seleccionar_tareas(v)

    def capturar():
        d = _dialogo(hist.app)
        assert d._puntos.get() == ""
        d._puntos.insert(0, "91.5")
        d._fecha.delete(0, "end")
        d._fecha.insert(0, "15/10/2026")
        d._aceptar()

    hist.app.after(300, capturar)
    v.editar_calificacion()
    assert _filas_examenes(v)[0] == ("Tareas", "91.5", "15/10/2026")
    assert hist.srv.tareas_de(hist.curso.id, hist.alumno.id).puntos == 91.5


def test_corregir_tareas_parte_de_la_calificacion_actual(hist):
    v = hist.vista
    hist.srv.establecer_tareas(hist.curso.id, hist.alumno.id, 70, date(2026, 10, 9))
    v.recargar()
    _seleccionar_tareas(v)

    def editar():
        d = _dialogo(hist.app)
        assert d._puntos.get() == "70" and d._fecha.get() == "09/10/2026"
        d._puntos.delete(0, "end")
        d._puntos.insert(0, "105")  # sin tope: puntos extra
        d._aceptar()

    hist.app.after(300, editar)
    v.editar_calificacion()
    assert _filas_examenes(v)[0][:2] == ("Tareas", "105")


def test_el_dialogo_de_tareas_valida_dentro_del_dialogo(hist):
    v = hist.vista
    _seleccionar_tareas(v)

    def probar():
        d = _dialogo(hist.app)
        for puntos, fecha, mensaje in (("abc", "01/10/2026", "número"),
                                       ("-3", "01/10/2026", "mayor o igual a 0"),
                                       ("5", "31/02/2026", "fecha")):
            d._puntos.delete(0, "end")
            d._puntos.insert(0, puntos)
            d._fecha.delete(0, "end")
            d._fecha.insert(0, fecha)
            d._aceptar()
            assert mensaje in d._error.cget("text").lower()
        d.cancelar()

    hist.app.after(300, probar)
    v.editar_calificacion()
    assert _filas_examenes(v)[0][1] == "0"


def test_quitar_tareas_pide_confirmacion_y_vuelve_a_0(hist):
    v = hist.vista
    hist.srv.establecer_tareas(hist.curso.id, hist.alumno.id, 70, date(2026, 10, 9))
    v.recargar()
    _seleccionar_tareas(v)
    hist.respuesta["si"] = False
    v.eliminar_calificacion()
    assert _filas_examenes(v)[0][1] == "70"  # cancelado: no pasa nada
    hist.respuesta["si"] = True
    v.eliminar_calificacion()
    assert _filas_examenes(v)[0] == ("Tareas", "0", "—")
    assert hist.srv.tareas_de(hist.curso.id, hist.alumno.id) is None


def test_botones_segun_la_fila_de_tareas(hist):
    v = hist.vista
    _seleccionar_tareas(v)
    v._actualizar_botones_examenes()
    assert str(v._boton_calificar.cget("state")) == "normal"  # se puede calificar
    assert str(v._boton_quitar.cget("state")) == "disabled"  # pero no hay nada que quitar
    hist.srv.establecer_tareas(hist.curso.id, hist.alumno.id, 70, date(2026, 10, 9))
    v.recargar()
    _seleccionar_tareas(v)
    v._actualizar_botones_examenes()
    assert str(v._boton_quitar.cget("state")) == "normal"


def test_editar_tareas_no_toca_las_calificaciones_de_examen(hist_ex):
    v = hist_ex.vista
    hist_ex.srv.establecer_tareas(hist_ex.curso.id, hist_ex.alumno.id, 70, date(2026, 10, 9))
    v.recargar()
    assert _filas_examenes(v)[2] == ("Parcial 1", "42", "08/10/2026")  # el examen sigue igual
    _seleccionar_tareas(v)
    hist_ex.respuesta["si"] = True
    v.eliminar_calificacion()
    assert _filas_examenes(v) == [("Tareas", "0", "—"), ("Proyecto final", "0", "—"), ("Parcial 1", "42", "08/10/2026"), ("Final", "0", "—")]
