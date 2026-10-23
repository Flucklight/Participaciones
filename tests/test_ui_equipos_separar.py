"""Pantalla Curso: separar miembros de un equipo con clic derecho (datos ficticios)."""

from types import SimpleNamespace

import pytest

from tests.conftest import hay_pantalla
from tests.test_ui_curso import _fila, _texto_franja, curso_ui  # noqa: F401  (fixture)
from tests.test_ui_equipos import (
    _activar_formar,
    _crear,
    _boton_deshacer_visible,
    _en_proyecto,
    _etiquetas,
    _filas,
    _formar,
    _seleccionar,
)

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def _evento(ui, iid):
    """Evento de clic derecho sobre la fila `iid` (coordenadas reales de la tabla)."""
    v = ui.vista
    ui.app.update()
    x, y, _w, h = v._tabla.bbox(iid)
    return SimpleNamespace(x=x + 20, y=y + h // 2, x_root=10, y_root=10)


def _iid(v, cuenta):
    return str(_fila(v, cuenta).alumno.id)


def _etiqueta_menu(menu):
    return menu.entrycget(0, "label")


def _equipo(ui, v, cuenta):
    return ui.srv.equipo_de(ui.curso.id, int(_iid(v, cuenta)))


def test_fuera_de_formar_equipos_no_hay_menu(curso_ui):
    _formar(curso_ui, "100000001")
    v = _en_proyecto(curso_ui)
    assert v._menu_equipos(_evento(curso_ui, _iid(v, "100000001"))) is None


def test_clic_derecho_en_un_miembro_ofrece_separarlo_de_su_equipo(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    v = _activar_formar(curso_ui)
    menu = v._menu_equipos(_evento(curso_ui, _iid(v, "100000001")))
    assert _etiqueta_menu(menu) == "Sacar del equipo 1"
    assert v._tabla.selection() == (_iid(v, "100000001"),)  # el clic derecho selecciona esa fila


def test_separar_saca_al_alumno_actualiza_la_tabla_y_se_puede_deshacer(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    v = _activar_formar(curso_ui)
    v._menu_equipos(_evento(curso_ui, _iid(v, "100000001"))).invoke(0)
    assert "Se sacó a 1 alumno del equipo 1" in _texto_franja(v)
    assert _equipo(curso_ui, v, "100000001") is None
    assert [n for _, n in _filas(v)][:2] == ["Equipo 1 · 1 alumno", "ACOSTA ORTEGA ELENA"]
    assert _boton_deshacer_visible(v)
    v.deshacer()
    assert "volvieron a su equipo" in _texto_franja(v)
    assert _equipo(curso_ui, v, "100000001") == 1


def test_sin_equipo_y_sin_equipos_formados_no_hay_menu(curso_ui):
    v = _activar_formar(curso_ui)
    assert v._menu_equipos(_evento(curso_ui, _iid(v, "100000002"))) is None  # nada que separar ni a dónde agregar


def test_en_un_encabezado_no_hay_menu(curso_ui):
    _formar(curso_ui, "100000001")
    v = _activar_formar(curso_ui)
    assert v._menu_equipos(_evento(curso_ui, "equipo_1")) is None


def test_clic_derecho_fuera_de_las_filas_no_hace_nada(curso_ui):
    _formar(curso_ui, "100000001")
    v = _activar_formar(curso_ui)
    assert v._menu_equipos(SimpleNamespace(x=30, y=100000, x_root=0, y_root=0)) is None


def test_con_varios_seleccionados_separa_a_todos_los_que_tienen_equipo(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    _formar(curso_ui, "100000003")
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001", "100000002", "100000003", "100000004")  # el último sin equipo
    menu = v._menu_equipos(_evento(curso_ui, _iid(v, "100000001")))
    assert _etiqueta_menu(menu) == "Sacar de sus equipos (3 alumnos)"
    assert len(v._tabla.selection()) == 4  # clic sobre un seleccionado conserva la selección
    menu.invoke(0)
    assert "Se sacó a 3 alumnos" in _texto_franja(v)
    assert curso_ui.srv.equipos_del_curso(curso_ui.curso.id) == []


def test_varios_del_mismo_equipo_dicen_cuantos(curso_ui):
    _formar(curso_ui, "100000001", "100000002", "100000003")
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001", "100000002")
    menu = v._menu_equipos(_evento(curso_ui, _iid(v, "100000002")))
    assert _etiqueta_menu(menu) == "Sacar del equipo 1 (2 alumnos)"


def test_clic_derecho_en_una_fila_no_seleccionada_separa_solo_esa(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001")
    v._menu_equipos(_evento(curso_ui, _iid(v, "100000002"))).invoke(0)
    assert _equipo(curso_ui, v, "100000001") == 1
    assert _equipo(curso_ui, v, "100000002") is None


def test_separar_a_todos_hace_desaparecer_el_equipo_y_su_numero_no_se_reutiliza(curso_ui):
    _formar(curso_ui, "100000001")
    v = _activar_formar(curso_ui)
    v._menu_equipos(_evento(curso_ui, _iid(v, "100000001"))).invoke(0)
    assert not any(i.startswith("equipo_") for i in v._tabla.get_children())
    _seleccionar(curso_ui, "100000002")
    _crear(curso_ui)
    assert "Equipo 2 formado" in _texto_franja(v)


def test_separar_resalta_a_los_alumnos_separados(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    v = _activar_formar(curso_ui)
    v._menu_equipos(_evento(curso_ui, _iid(v, "100000001"))).invoke(0)
    assert "reciente" in _etiquetas(v, _iid(v, "100000001"))


def test_el_clic_derecho_abre_el_menu_en_la_posicion_del_clic(curso_ui, monkeypatch):
    import tkinter as tk

    abiertos = []
    monkeypatch.setattr(tk.Menu, "tk_popup", lambda self, x, y: abiertos.append((x, y)))
    _formar(curso_ui, "100000001")
    v = _activar_formar(curso_ui)
    evento = _evento(curso_ui, _iid(v, "100000001"))
    evento.x_root, evento.y_root = 123, 456
    assert v._al_clic_derecho(evento) == "break"
    assert abiertos == [(123, 456)]


def test_separar_no_altera_las_calificaciones(curso_ui):
    curso_ui.srv.registrar_tareas(curso_ui.curso.id, "100000001", 85)
    _formar(curso_ui, "100000001", "100000002")
    v = _activar_formar(curso_ui)
    v._menu_equipos(_evento(curso_ui, _iid(v, "100000001"))).invoke(0)
    tareas = {r.alumno.num_cuenta: r.tareas for r in curso_ui.srv.resumen_curso(curso_ui.curso.id)}
    assert tareas["100000001"] == 85
