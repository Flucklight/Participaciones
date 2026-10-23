"""Formar equipos: clic simple, botones «Crear equipo» y «Sacar de equipo», y «Agregar a ▸»."""

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


def _iid(v, cuenta):
    return str(_fila(v, cuenta).alumno.id)


def _evento(ui, iid, estado=0):
    v = ui.vista
    ui.app.update()
    x, y, _w, h = v._tabla.bbox(iid)
    return SimpleNamespace(x=x + 20, y=y + h // 2, x_root=10, y_root=10, state=estado)


def _pulsar(ui, cuenta, estado=0):
    v = ui.vista
    resultado = v._al_presionar_tabla(_evento(ui, _iid(v, cuenta), estado))
    ui.app.update()  # el evento <<TreeviewSelect>> de un cambio de selección llega con el ciclo de eventos
    return resultado


def _equipo(ui, v, cuenta):
    return ui.srv.equipo_de(ui.curso.id, int(_iid(v, cuenta)))


# ---------------- el clic simple selecciona ----------------
def test_formando_un_clic_suma_al_alumno_a_la_seleccion_sin_ctrl(curso_ui):
    v = _activar_formar(curso_ui)
    assert _pulsar(curso_ui, "100000001") == "break"
    assert v._tabla.selection() == (_iid(v, "100000001"),)
    _pulsar(curso_ui, "100000003")
    assert set(v._tabla.selection()) == {_iid(v, "100000001"), _iid(v, "100000003")}
    assert v._etiqueta_seleccion.cget("text") == "2 seleccionados"


def test_otro_clic_sobre_un_seleccionado_lo_quita(curso_ui):
    v = _activar_formar(curso_ui)
    _pulsar(curso_ui, "100000001")
    _pulsar(curso_ui, "100000002")
    _pulsar(curso_ui, "100000001")
    assert v._tabla.selection() == (_iid(v, "100000002"),)


def test_se_puede_formar_el_equipo_solo_con_clics(curso_ui):
    v = _activar_formar(curso_ui)
    for cuenta in ("100000001", "100000002", "100000004"):
        _pulsar(curso_ui, cuenta)
    _crear(curso_ui)
    assert [e.numero for e in curso_ui.srv.equipos_del_curso(curso_ui.curso.id)] == [1]
    assert len(curso_ui.srv.equipos_del_curso(curso_ui.curso.id)[0].miembros) == 3


def test_ctrl_y_mayus_conservan_el_comportamiento_normal_de_la_tabla(curso_ui):
    v = _activar_formar(curso_ui)
    assert _pulsar(curso_ui, "100000001", estado=0x4) is None  # Ctrl: lo resuelve el Treeview
    assert _pulsar(curso_ui, "100000001", estado=0x1) is None  # Mayús


def test_un_clic_en_un_encabezado_de_equipo_no_selecciona_nada(curso_ui):
    _formar(curso_ui, "100000001")
    v = _activar_formar(curso_ui)
    assert v._al_presionar_tabla(_evento(curso_ui, "equipo_1")) == "break"
    assert v._tabla.selection() == ()


def test_el_clic_en_el_encabezado_de_columna_sigue_ordenando(curso_ui):
    v = _activar_formar(curso_ui)
    assert v._al_presionar_tabla(SimpleNamespace(x=30, y=5, state=0)) is None


def test_fuera_de_formar_equipos_no_se_interviene_el_clic(curso_ui):
    v = _en_proyecto(curso_ui)
    assert _pulsar(curso_ui, "100000001") is None


def test_formando_el_doble_clic_no_abre_el_historial(curso_ui, monkeypatch):
    v = _activar_formar(curso_ui)
    abierto = []
    monkeypatch.setattr(curso_ui.app, "abrir_historial", lambda *a: abierto.append(a))
    evento = _evento(curso_ui, _iid(v, "100000001"))
    v._al_doble_clic(evento)
    assert abierto == []


# ---------------- disposición de los botones ----------------
def test_crear_equipo_va_a_la_izquierda_justo_debajo_de_formar_equipos(curso_ui):
    v = _activar_formar(curso_ui)
    curso_ui.app.update()
    formar, crear, sacar = v._boton_formar, v._boton_crear_equipo, v._boton_sacar_equipo
    assert crear.winfo_rooty() > formar.winfo_rooty() + formar.winfo_height() - 1  # debajo
    assert abs(crear.winfo_rootx() - formar.winfo_rootx()) <= 4  # alineado a la izquierda
    assert sacar.winfo_rooty() == crear.winfo_rooty() and sacar.winfo_rootx() > crear.winfo_rootx()


def test_los_botones_de_accion_solo_se_ven_formando(curso_ui):
    v = _en_proyecto(curso_ui)
    assert v._acciones_equipo.winfo_manager() == ""
    v.alternar_formar()
    assert v._acciones_equipo.winfo_manager() == "pack"
    v.alternar_formar()
    assert v._acciones_equipo.winfo_manager() == ""


# ---------------- «Sacar de equipo» ----------------
def test_sacar_de_equipo_se_habilita_solo_si_hay_seleccionados_con_equipo(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    v = _activar_formar(curso_ui)
    assert str(v._boton_sacar_equipo.cget("state")) == "disabled"
    _pulsar(curso_ui, "100000003")  # sin equipo
    assert str(v._boton_sacar_equipo.cget("state")) == "disabled"
    _pulsar(curso_ui, "100000001")
    assert str(v._boton_sacar_equipo.cget("state")) == "normal"
    assert v._boton_sacar_equipo.cget("text") == "Sacar de equipo (1)"


def test_sacar_de_equipo_hace_lo_mismo_que_separar_del_clic_derecho(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    _formar(curso_ui, "100000003")
    v = _activar_formar(curso_ui)
    for cuenta in ("100000001", "100000003", "100000004"):  # el último sin equipo: se ignora
        _pulsar(curso_ui, cuenta)
    v.sacar_de_equipo()
    assert "Se sacó a 2 alumnos de sus equipos" in _texto_franja(v)
    assert _equipo(curso_ui, v, "100000001") is None and _equipo(curso_ui, v, "100000003") is None
    assert _equipo(curso_ui, v, "100000002") == 1
    assert _boton_deshacer_visible(v)
    v.deshacer()
    assert _equipo(curso_ui, v, "100000001") == 1 and _equipo(curso_ui, v, "100000003") == 2


def test_sacar_de_equipo_sin_nadie_con_equipo_no_hace_nada(curso_ui):
    v = _activar_formar(curso_ui)
    _pulsar(curso_ui, "100000001")
    v.sacar_de_equipo()
    assert "Se sacó" not in _texto_franja(v)


# ---------------- «Agregar a ▸» ----------------
def _submenu(menu, indice):
    return menu.nametowidget(menu.entrycget(indice, "menu"))


def _etiquetas_submenu(sub):
    return [sub.entrycget(i, "label") for i in range(sub.index("end") + 1)]


def test_el_clic_derecho_sobre_un_alumno_sin_equipo_ofrece_agregar_a_los_equipos_formados(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    _formar(curso_ui, "100000003")
    v = _activar_formar(curso_ui)
    menu = v._menu_equipos(SimpleNamespace(**vars(_evento(curso_ui, _iid(v, "100000004")))))
    assert menu.entrycget(0, "label") == "Agregar a"
    assert _etiquetas_submenu(_submenu(menu, 0)) == ["Equipo 1 (2 alumnos)", "Equipo 2 (1 alumno)"]


def test_agregar_a_un_equipo_suma_al_alumno_y_se_puede_deshacer(curso_ui):
    _formar(curso_ui, "100000001")
    v = _activar_formar(curso_ui)
    menu = v._menu_equipos(_evento(curso_ui, _iid(v, "100000002")))
    _submenu(menu, 0).invoke(0)
    assert "1 alumno agregado al equipo 1" in _texto_franja(v)
    assert _equipo(curso_ui, v, "100000002") == 1
    assert [n for _, n in _filas(v)][:3] == ["Equipo 1 · 2 alumnos", "ABREU SOLANO MARCOS", "ACOSTA ORTEGA ELENA"]
    assert "reciente" in _etiquetas(v, _iid(v, "100000002"))
    assert _boton_deshacer_visible(v)
    v.deshacer()
    assert _equipo(curso_ui, v, "100000002") is None and _equipo(curso_ui, v, "100000001") == 1
    assert "salieron del equipo 1" in _texto_franja(v)


def test_agregar_varios_seleccionados_a_la_vez(curso_ui):
    _formar(curso_ui, "100000001")
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000002", "100000003")
    menu = v._menu_equipos(_evento(curso_ui, _iid(v, "100000002")))
    assert menu.entrycget(0, "label") == "Agregar a (2 alumnos)"
    _submenu(menu, 0).invoke(0)
    assert _equipo(curso_ui, v, "100000002") == 1 and _equipo(curso_ui, v, "100000003") == 1
    assert "2 alumnos agregados al equipo 1" in _texto_franja(v)


def test_a_quien_ya_tiene_equipo_no_se_le_ofrece_agregar(curso_ui):
    _formar(curso_ui, "100000001")
    _formar(curso_ui, "100000002")
    v = _activar_formar(curso_ui)
    menu = v._menu_equipos(_evento(curso_ui, _iid(v, "100000001")))
    assert menu.index("end") == 0 and menu.entrycget(0, "label") == "Sacar del equipo 1"


def test_con_una_seleccion_mixta_se_ofrece_separar_y_agregar(curso_ui):
    _formar(curso_ui, "100000001")
    _formar(curso_ui, "100000002")
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001", "100000003")
    menu = v._menu_equipos(_evento(curso_ui, _iid(v, "100000001")))
    assert menu.entrycget(0, "label") == "Sacar del equipo 1"
    assert menu.entrycget(1, "label") == "Agregar a"
    _submenu(menu, 1).invoke(1)  # al equipo 2: solo se agrega el que no tenía equipo
    assert _equipo(curso_ui, v, "100000003") == 2 and _equipo(curso_ui, v, "100000001") == 1


def test_agregar_no_altera_calificaciones(curso_ui):
    curso_ui.srv.registrar_tareas(curso_ui.curso.id, "100000002", 77)
    _formar(curso_ui, "100000001")
    v = _activar_formar(curso_ui)
    _submenu(v._menu_equipos(_evento(curso_ui, _iid(v, "100000002"))), 0).invoke(0)
    tareas = {r.alumno.num_cuenta: r.tareas for r in curso_ui.srv.resumen_curso(curso_ui.curso.id)}
    assert tareas["100000002"] == 77
