"""Pantalla Curso: eliminar a un oyente con botón o clic derecho, y deshacer (datos ficticios)."""

from datetime import date
from types import SimpleNamespace

import customtkinter as ctk
import pytest

from core.models import TipoInscripcion
from tests.conftest import buscar_dialogo as _dialogo, hay_pantalla
from tests.test_ui_curso import _fila, _texto_franja, curso_ui  # noqa: F401  (fixture)
from tests.test_ui_equipos import _activar_formar, _boton_deshacer_visible

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def _oyente(ui):
    """Oyente con datos en el curso (cuenta 100000099) y la tabla recargada."""
    o = ui.srv.crear_alumno_en_curso(ui.curso.id, "Oyente Prueba", TipoInscripcion.OYENTE, "100000099")
    ui.srv.agregar_participacion(ui.curso.id, o.id, 5, date(2027, 2, 1))
    ui.srv.establecer_tareas(ui.curso.id, o.id, 9, date(2027, 2, 1))
    ui.vista.recargar()
    ui.app.update()
    return o


def _seleccionar(ui, alumno_id):
    v = ui.vista
    v._tabla.selection_set(str(alumno_id))
    ui.app.update()


def _evento(ui, iid):
    v = ui.vista
    ui.app.update()
    x, y, _w, h = v._tabla.bbox(iid)
    return SimpleNamespace(x=x + 20, y=y + h // 2, x_root=10, y_root=10)


def _confirmar_dialogo(ui, aceptar=True):
    def actuar():
        d = _dialogo(ui.app)
        assert d is not None
        d.cerrar(True) if aceptar else d.cancelar()

    ui.app.after(300, actuar)


def _hay(ui, cuenta):
    return any(f.alumno.num_cuenta == cuenta for f in ui.vista._filas)


# ---------------- botón ----------------
def test_el_boton_solo_se_habilita_con_un_oyente_elegido(curso_ui):
    v = curso_ui.vista
    o = _oyente(curso_ui)
    assert str(v._boton_eliminar_alumno.cget("state")) == "disabled"  # nada elegido
    _seleccionar(curso_ui, _fila(v, "100000001").alumno.id)
    assert str(v._boton_eliminar_alumno.cget("state")) == "disabled"  # un regular
    _seleccionar(curso_ui, o.id)
    assert str(v._boton_eliminar_alumno.cget("state")) == "normal"


def test_con_formar_equipos_activo_el_boton_se_deshabilita(curso_ui):
    o = _oyente(curso_ui)
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, o.id)
    assert str(v._boton_eliminar_alumno.cget("state")) == "disabled"


def test_eliminar_con_el_boton_confirma_refresca_y_avisa(curso_ui):
    v = curso_ui.vista
    o = _oyente(curso_ui)
    _seleccionar(curso_ui, o.id)
    _confirmar_dialogo(curso_ui)
    v.eliminar_alumno()
    assert not _hay(curso_ui, "100000099")
    assert "OYENTE PRUEBA eliminado del curso" in _texto_franja(v)
    assert _boton_deshacer_visible(v)
    assert len(v._tabla.get_children()) == 4


def test_cancelar_el_dialogo_no_elimina(curso_ui):
    v = curso_ui.vista
    o = _oyente(curso_ui)
    _seleccionar(curso_ui, o.id)
    _confirmar_dialogo(curso_ui, aceptar=False)
    v.eliminar_alumno()
    assert _hay(curso_ui, "100000099")
    assert "no se eliminó a nadie" in _texto_franja(v)


def test_el_dialogo_muestra_los_conteos(curso_ui):
    v = curso_ui.vista
    o = _oyente(curso_ui)
    _seleccionar(curso_ui, o.id)
    visto = {}

    def mirar():
        d = _dialogo(curso_ui.app)
        textos = [w.cget("text") for w in d.cuerpo.winfo_children() if isinstance(w, ctk.CTkLabel)]
        visto["texto"] = " ".join(textos)
        d.cancelar()

    curso_ui.app.after(400, mirar)
    v.eliminar_alumno()
    assert "OYENTE PRUEBA" in visto["texto"]
    assert "1 participación" in visto["texto"] and "calificación de tareas" in visto["texto"]
    assert "también se borrará del sistema" in visto["texto"]


def test_deshacer_restaura_al_oyente_y_resalta_su_fila(curso_ui):
    v = curso_ui.vista
    o = _oyente(curso_ui)
    _seleccionar(curso_ui, o.id)
    _confirmar_dialogo(curso_ui)
    v.eliminar_alumno()
    v.deshacer()
    assert _hay(curso_ui, "100000099")
    assert _fila(v, "100000099").total == 5
    assert "Se deshizo la eliminación de OYENTE PRUEBA" in _texto_franja(v)
    assert not _boton_deshacer_visible(v)
    v.deshacer()  # ya no hay nada que deshacer: no falla ni repite
    assert len([f for f in v._filas if f.alumno.num_cuenta == "100000099"]) == 1


def test_otra_captura_hace_que_ya_no_se_pueda_deshacer_la_eliminacion(curso_ui):
    v = curso_ui.vista
    o = _oyente(curso_ui)
    _seleccionar(curso_ui, o.id)
    _confirmar_dialogo(curso_ui)
    v.eliminar_alumno()
    v._entrada_alumno.insert(0, "100000001")
    v._entrada_decimas.insert(0, "10")
    v.guardar()
    v.deshacer()  # deshace la participación, no la eliminación
    assert not _hay(curso_ui, "100000099")
    assert _fila(v, "100000001").total == 0


def test_eliminar_a_quien_estaba_cargado_en_el_registro_lo_limpia(curso_ui):
    v = curso_ui.vista
    o = _oyente(curso_ui)
    v._elegir(o)
    _seleccionar(curso_ui, o.id)
    _confirmar_dialogo(curso_ui)
    v.eliminar_alumno()
    assert v._elegido is None and v._entrada_alumno.get() == ""


def test_sin_seleccion_el_metodo_avisa(curso_ui):
    v = curso_ui.vista
    _oyente(curso_ui)
    v._tabla.selection_set(())
    v.eliminar_alumno()
    assert "Elige en la tabla" in _texto_franja(v)


def test_un_regular_se_rechaza_aunque_se_llame_directo(curso_ui):
    v = curso_ui.vista
    v.eliminar_alumno(_fila(v, "100000001").alumno.id)
    assert "solo se pueden eliminar oyentes" in _texto_franja(v)
    assert _hay(curso_ui, "100000001")


# ---------------- clic derecho ----------------
def test_clic_derecho_en_un_oyente_ofrece_eliminarlo(curso_ui):
    v = curso_ui.vista
    o = _oyente(curso_ui)
    menu = v._menu_alumno(_evento(curso_ui, str(o.id)))
    assert menu.entrycget(0, "label") == "Eliminar alumno…"
    assert v._tabla.selection() == (str(o.id),)
    _confirmar_dialogo(curso_ui)
    menu.invoke(0)
    assert not _hay(curso_ui, "100000099")


def test_clic_derecho_en_un_regular_muestra_la_opcion_desactivada(curso_ui):
    v = curso_ui.vista
    iid = str(_fila(v, "100000001").alumno.id)
    menu = v._menu_alumno(_evento(curso_ui, iid))
    assert menu.entrycget(0, "label") == "Eliminar alumno (solo oyentes)"
    assert str(menu.entrycget(0, "state")) == "disabled"


def test_con_formar_equipos_activo_el_clic_derecho_no_ofrece_eliminar(curso_ui):
    o = _oyente(curso_ui)
    v = _activar_formar(curso_ui)
    assert v._menu_alumno(_evento(curso_ui, str(o.id))) is None
