"""Pantalla Curso: evaluar el proyecto final, a un alumno o a un equipo (diálogos y tabla reales)."""

from types import SimpleNamespace

import pytest

from core.models import TipoInscripcion
from tests.conftest import buscar_dialogo as _dialogo, hay_pantalla
from tests.test_ui_curso import _fila, _texto_franja, curso_ui  # noqa: F401  (fixture)
from tests.test_ui_equipos import _en_proyecto, _formar

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def _evaluar(ui):
    v = _en_proyecto(ui)
    assert not v._formando
    return v


def _calificar(v, destino, puntos):
    v._entrada_alumno.delete(0, "end")
    v._entrada_alumno.insert(0, destino)
    v._entrada_decimas.delete(0, "end")
    v._entrada_decimas.insert(0, puntos)
    v.guardar()


def _nota(ui, cuenta):
    alumno = _fila(ui.vista, cuenta).alumno
    return ui.srv.proyecto_de(ui.curso.id, alumno.id)


def _notas(ui):
    return {r.alumno.num_cuenta: r.proyecto for r in ui.srv.resumen_curso(ui.curso.id)}


def _boton_deshacer_visible(v):
    return v._boton_deshacer.winfo_manager() == "pack"


def _clic_en_fila(ui, cuenta):
    v = ui.vista
    ui.app.update()
    x, y, _w, h = v._tabla.bbox(str(_fila(v, cuenta).alumno.id))
    v._al_clic_tabla(SimpleNamespace(x=x + 20, y=y + h // 2))


# ================= evaluar a un alumno =================
def test_evaluar_muestra_el_campo_con_su_texto_y_el_boton_del_modo(curso_ui):
    v = _evaluar(curso_ui)
    assert v._boton_guardar.cget("text") == "Registrar proyecto"
    assert v._entrada_decimas._placeholder_text == "Calificación del proyecto"
    assert "equipo N" in v._entrada_alumno._placeholder_text
    assert str(v._boton_usar_equipo.cget("state")) == "disabled"
    assert not any(b.winfo_manager() for b in v._atajos)  # +5/+10/+25 no aplican


def test_guardar_a_un_alumno_por_cuenta(curso_ui):
    v = _evaluar(curso_ui)
    _calificar(v, "100000001", "9.5")
    assert "ABREU SOLANO MARCOS" in _texto_franja(v) and "Proyecto: 9.5" in _texto_franja(v)
    assert _nota(curso_ui, "100000001").puntos == 9.5 and _notas(curso_ui)["100000002"] == 0
    assert _boton_deshacer_visible(v)
    assert v._entrada_alumno.get() == "" and v._elegido is None  # listo para el siguiente


def test_guardar_a_un_alumno_por_nombre_parcial(curso_ui):
    v = _evaluar(curso_ui)
    _calificar(v, "acosta", "7")
    assert _nota(curso_ui, "100000002").puntos == 7


def test_valor_invalido_o_campo_vacio_muestra_el_error(curso_ui):
    v = _evaluar(curso_ui)
    _calificar(v, "100000001", "abc")
    assert "debe ser un número" in _texto_franja(v)
    _calificar(v, "100000001", "-3")
    assert "mayor o igual a 0" in _texto_franja(v)
    _calificar(v, "", "5")
    assert "Escribe un número de cuenta" in _texto_franja(v)
    assert set(_notas(curso_ui).values()) == {0.0}


def test_reemplazar_advierte_y_no_guarda_hasta_confirmar(curso_ui):
    v = _evaluar(curso_ui)
    _calificar(v, "100000001", "7")
    _calificar(v, "100000001", "9")
    assert "Ya tiene 7 en el proyecto" in _texto_franja(v) and "9" in _texto_franja(v)
    assert _nota(curso_ui, "100000001").puntos == 7
    assert v._boton_confirmar.winfo_manager() == "pack" and v._boton_cancelar.winfo_manager() == "pack"
    v.confirmar_reemplazo()
    assert _nota(curso_ui, "100000001").puntos == 9 and "antes 7" in _texto_franja(v)


def test_cancelar_el_reemplazo_conserva_la_nota(curso_ui):
    v = _evaluar(curso_ui)
    _calificar(v, "100000001", "7")
    _calificar(v, "100000001", "9")
    v.cancelar_reemplazo()
    assert _nota(curso_ui, "100000001").puntos == 7 and "se conserva" in _texto_franja(v)


def test_deshacer_restaura_la_anterior_o_elimina(curso_ui):
    v = _evaluar(curso_ui)
    _calificar(v, "100000001", "7")
    v.deshacer()
    assert _nota(curso_ui, "100000001") is None and "Se deshizo la calificación del proyecto" in _texto_franja(v)
    _calificar(v, "100000001", "7")
    _calificar(v, "100000001", "9")
    v.confirmar_reemplazo()
    v.deshacer()
    assert _nota(curso_ui, "100000001").puntos == 7


def test_ambiguo_pide_elegir_y_califica_al_elegido(curso_ui):
    v = _evaluar(curso_ui)

    def elegir():
        d = _dialogo(curso_ui.app)
        d.cerrar(next(a for a in v._servicio.buscar_alumnos_en_curso(v.curso.id, "garcia ana")
                      if a.num_cuenta == "100000004"))

    curso_ui.app.after(300, elegir)
    _calificar(v, "garcia ana", "8")
    assert _nota(curso_ui, "100000004").puntos == 8


def test_alumno_inexistente_ofrece_crear_oyente_y_califica(curso_ui):
    v = _evaluar(curso_ui)
    curso_ui.app.after(300, lambda: _dialogo(curso_ui.app)._aceptar())
    _calificar(v, "luis nuevo", "6")
    oyente = next(f for f in v._filas if f.alumno.nombre_completo == "LUIS NUEVO")
    assert oyente.tipo == TipoInscripcion.OYENTE and oyente.proyecto == 6
    assert "alumno agregado" in _texto_franja(v)


def test_clic_en_una_fila_carga_al_alumno_y_su_nota_actual(curso_ui):
    curso_ui.srv.registrar_proyecto(curso_ui.curso.id, "100000001", 8.5)
    v = _evaluar(curso_ui)
    v.recargar()
    _clic_en_fila(curso_ui, "100000001")
    assert v._elegido.num_cuenta == "100000001"
    assert v._entrada_alumno.get() == "ABREU SOLANO MARCOS" and v._entrada_decimas.get() == "8.5"
    _clic_en_fila(curso_ui, "100000002")  # sin nota: el campo queda vacío
    assert v._entrada_decimas.get() == ""


def test_corregir_desde_el_clic_en_fila(curso_ui):
    curso_ui.srv.registrar_proyecto(curso_ui.curso.id, "100000001", 8.5)
    v = _evaluar(curso_ui)
    v.recargar()
    _clic_en_fila(curso_ui, "100000001")
    v._entrada_decimas.delete(0, "end")
    v._entrada_decimas.insert(0, "10")
    v.guardar()
    assert "Ya tiene 8.5 en el proyecto" in _texto_franja(v)
    v.confirmar_reemplazo()
    assert _nota(curso_ui, "100000001").puntos == 10


def test_otra_captura_reemplaza_lo_deshacible(curso_ui):
    v = _evaluar(curso_ui)
    _calificar(v, "100000001", "9")
    v._selector_modo.set("Participación")
    v._cambiar_modo("Participación")
    v._entrada_alumno.insert(0, "100000002")
    v._entrada_decimas.insert(0, "5")
    v.guardar()
    v.deshacer()  # deshace la participación, no el proyecto
    assert _nota(curso_ui, "100000001").puntos == 9


def test_tras_calificar_el_proyecto_otra_captura_lo_reemplaza(curso_ui):
    v = _evaluar(curso_ui)
    _calificar(v, "100000001", "9")
    assert v._ultimo_proyecto is not None
    v._selector_modo.set("Tareas")
    v._cambiar_modo("Tareas")
    v._entrada_alumno.insert(0, "100000002")
    v._entrada_decimas.insert(0, "80")
    v.guardar()
    assert v._ultimo_proyecto is None
    v.deshacer()  # deshace tareas
    assert _nota(curso_ui, "100000001").puntos == 9


def test_formando_no_hay_registro_y_al_apagar_vuelve_a_evaluar(curso_ui):
    v = _evaluar(curso_ui)
    v.alternar_formar()
    assert v._fila_registro.winfo_manager() == ""
    v.alternar_formar()
    _calificar(v, "100000001", "9")
    assert _nota(curso_ui, "100000001").puntos == 9


def test_cambiar_de_modo_restablece_el_campo_de_alumno(curso_ui):
    v = _evaluar(curso_ui)
    v._selector_modo.set("Tareas")
    v._cambiar_modo("Tareas")
    assert "equipo N" not in v._entrada_alumno._placeholder_text
    assert v._boton_usar_equipo.winfo_manager() == ""


def test_evaluar_el_proyecto_no_altera_las_demas_calificaciones(curso_ui):
    curso_ui.srv.registrar_tareas(curso_ui.curso.id, "100000001", 85)
    curso_ui.srv.registrar(curso_ui.curso.id, "100000001", 4)
    antes = [(r.total, r.tareas) for r in curso_ui.srv.resumen_curso(curso_ui.curso.id)]
    v = _evaluar(curso_ui)
    _calificar(v, "100000001", "9")
    assert antes == [(r.total, r.tareas) for r in curso_ui.srv.resumen_curso(curso_ui.curso.id)]


# ================= evaluar a un equipo =================
def test_equipo_n_califica_a_todos_los_miembros(curso_ui):
    _formar(curso_ui, "100000001", "100000002", "100000003")
    v = _evaluar(curso_ui)
    v.recargar()
    _calificar(v, "equipo 1", "9.5")
    n = _notas(curso_ui)
    assert [n["100000001"], n["100000002"], n["100000003"], n["100000004"]] == [9.5, 9.5, 9.5, 0]
    assert "Equipo 1  ·  Proyecto: 9.5 (3 alumnos)" in _texto_franja(v)
    assert _boton_deshacer_visible(v)


def test_se_puede_calificar_al_equipo_solo_con_el_teclado_en_el_campo(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    v = _evaluar(curso_ui)
    v.recargar()
    assert v._entrada_decimas._entry.bind("<Return>")  # Enter en las décimas guarda (sin mouse)
    v._entrada_alumno.insert(0, "e 1")
    v._entrada_decimas.insert(0, "8")
    v.guardar()
    assert _notas(curso_ui)["100000001"] == 8 and _notas(curso_ui)["100000002"] == 8


def test_equipo_inexistente_muestra_el_error(curso_ui):
    v = _evaluar(curso_ui)
    _calificar(v, "equipo 7", "9")
    assert "no existe o no tiene miembros" in _texto_franja(v)
    assert set(_notas(curso_ui).values()) == {0.0}


def test_usar_equipo_se_habilita_solo_si_el_alumno_cargado_tiene_equipo(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    v = _evaluar(curso_ui)
    v.recargar()
    _clic_en_fila(curso_ui, "100000003")  # sin equipo
    assert str(v._boton_usar_equipo.cget("state")) == "disabled" and v._boton_usar_equipo.cget("text") == "Usar equipo"
    _clic_en_fila(curso_ui, "100000001")
    assert str(v._boton_usar_equipo.cget("state")) == "normal"
    assert v._boton_usar_equipo.cget("text") == "Usar equipo 1"


def test_usar_equipo_cambia_el_destino_a_todo_el_equipo(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    v = _evaluar(curso_ui)
    v.recargar()
    _clic_en_fila(curso_ui, "100000001")
    v.usar_equipo()
    assert v._entrada_alumno.get() == "equipo 1" and v._elegido is None
    assert str(v._boton_usar_equipo.cget("state")) == "disabled"  # ya no hay un alumno elegido
    v._entrada_decimas.delete(0, "end")
    v._entrada_decimas.insert(0, "9")
    v.guardar()
    assert _notas(curso_ui)["100000001"] == 9 and _notas(curso_ui)["100000002"] == 9


def test_si_se_escribe_otro_nombre_el_boton_usar_equipo_se_apaga(curso_ui):
    _formar(curso_ui, "100000001")
    v = _evaluar(curso_ui)
    v.recargar()
    _clic_en_fila(curso_ui, "100000001")
    v._entrada_alumno.insert("end", "x")
    v._al_escribir_alumno(SimpleNamespace(keysym="x"))
    assert str(v._boton_usar_equipo.cget("state")) == "disabled"


def test_reemplazo_de_equipo_advierte_n_de_m_y_no_guarda_hasta_confirmar(curso_ui):
    _formar(curso_ui, "100000001", "100000002", "100000003", "100000004")
    curso_ui.srv.registrar_proyecto(curso_ui.curso.id, "100000001", 5)
    curso_ui.srv.registrar_proyecto(curso_ui.curso.id, "100000002", 6)
    v = _evaluar(curso_ui)
    v.recargar()
    _calificar(v, "equipo 1", "9.5")
    assert "2 de 4 miembros ya tienen calificación; se cambiarán a 9.5" in _texto_franja(v)
    n = _notas(curso_ui)
    assert [n["100000001"], n["100000002"], n["100000003"], n["100000004"]] == [5, 6, 0, 0]  # nada cambió
    v.confirmar_reemplazo()
    assert set(_notas(curso_ui).values()) == {9.5}
    assert "Equipo 1  ·  Proyecto: 9.5 (4 alumnos)" in _texto_franja(v)


def test_un_solo_miembro_con_otra_nota_dice_ya_tiene(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    curso_ui.srv.registrar_proyecto(curso_ui.curso.id, "100000001", 5)
    v = _evaluar(curso_ui)
    v.recargar()
    _calificar(v, "equipo 1", "9")
    assert "1 de 2 miembros ya tiene calificación" in _texto_franja(v)


def test_cancelar_el_reemplazo_de_equipo_no_cambia_nada(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    curso_ui.srv.registrar_proyecto(curso_ui.curso.id, "100000001", 5)
    v = _evaluar(curso_ui)
    v.recargar()
    _calificar(v, "equipo 1", "9")
    v.cancelar_reemplazo()
    assert _notas(curso_ui)["100000001"] == 5 and _notas(curso_ui)["100000002"] == 0


def test_deshacer_devuelve_a_todos_sus_notas_previas(curso_ui):
    _formar(curso_ui, "100000001", "100000002", "100000003")
    curso_ui.srv.registrar_proyecto(curso_ui.curso.id, "100000001", 5)
    antes = _notas(curso_ui)
    v = _evaluar(curso_ui)
    v.recargar()
    _calificar(v, "equipo 1", "9.5")
    v.confirmar_reemplazo()
    v.deshacer()
    assert _notas(curso_ui) == antes
    assert "Se deshizo la calificación del proyecto del equipo 1 (3 alumnos)" in _texto_franja(v)
    assert _nota(curso_ui, "100000002") is None


def test_corregir_a_un_solo_alumno_no_mueve_al_resto_del_equipo(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    v = _evaluar(curso_ui)
    v.recargar()
    _calificar(v, "equipo 1", "9")
    _calificar(v, "100000002", "7")
    v.confirmar_reemplazo()
    n = _notas(curso_ui)
    assert (n["100000001"], n["100000002"]) == (9, 7)


def test_resalta_a_los_miembros_calificados(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    v = _evaluar(curso_ui)
    v.recargar()
    _calificar(v, "equipo 1", "9")
    for cuenta in ("100000001", "100000002"):
        assert "reciente" in v._tabla.item(str(_fila(v, cuenta).alumno.id), "tags")
