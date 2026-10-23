"""Pantalla Curso: sección «Proyecto» y equipos (diálogos y tabla reales, datos ficticios)."""

from types import SimpleNamespace

import pytest

from tests.conftest import hay_pantalla
from tests.test_ui_curso import _fila, _texto_franja, curso_ui  # noqa: F401  (fixture)
from ui_desktop import tema

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def _ids(ui):
    return {r.alumno.num_cuenta: r.alumno.id for r in ui.srv.resumen_curso(ui.curso.id)}


def _formar(ui, *cuentas):
    n = _ids(ui)
    return ui.srv.formar_equipo(ui.curso.id, [n[c] for c in cuentas])


def _en_proyecto(ui):
    v = ui.vista
    v._selector_modo.set("Proyecto")
    v._cambiar_modo("Proyecto")
    ui.app.update()
    return v


def _filas(v):
    """[(iid, valores de nombre)] de la tabla en el orden en que se ve."""
    columnas = list(v._tabla["columns"])
    return [(i, v._tabla.item(i, "values")[columnas.index("nombre")]) for i in v._tabla.get_children()]


def _etiquetas(v, iid):
    return tuple(v._tabla.item(iid, "tags"))


def _clic(ui, iid):
    v = ui.vista
    ui.app.update()
    x, y, _w, h = v._tabla.bbox(iid)
    v._al_clic_tabla(SimpleNamespace(x=x + 20, y=y + h // 2))


# ---------------- el cuarto modo ----------------
def test_el_selector_tiene_cuatro_modos_y_f2_los_recorre_en_ciclo(curso_ui):
    v = curso_ui.vista
    assert v._selector_modo.cget("values") == ["Participación", "Examen", "Tareas", "Proyecto"]
    esperado = ["examen", "tareas", "proyecto", "participacion"]
    visto = []
    for _ in range(4):
        v._alternar_modo()
        visto.append(v._modo)
    assert visto == esperado and v._selector_modo.get() == "Participación"


def test_el_modo_proyecto_usa_su_propio_color(curso_ui):
    v = _en_proyecto(curso_ui)
    assert v._selector_modo.cget("selected_color") == tema.COLOR_PROYECTO


def test_en_proyecto_se_oculta_el_registro_y_al_salir_vuelve(curso_ui):
    v = curso_ui.vista
    assert v._fila_registro.winfo_manager() == "pack"
    _en_proyecto(curso_ui)
    assert v._fila_registro.winfo_manager() == ""
    assert "Formar equipos" in _texto_franja(v)
    v._selector_modo.set("Tareas")
    v._cambiar_modo("Tareas")
    assert v._fila_registro.winfo_manager() == "pack"


def test_la_columna_equipo_solo_existe_en_proyecto(curso_ui):
    v = curso_ui.vista
    assert "equipo" not in v._tabla["columns"]
    _en_proyecto(curso_ui)
    assert "equipo" in v._tabla["columns"]
    v._selector_modo.set("Participación")
    v._cambiar_modo("Participación")
    assert "equipo" not in v._tabla["columns"]


# ---------------- la tabla agrupada ----------------
def test_sin_equipos_la_tabla_es_la_de_siempre_aun_en_proyecto(curso_ui):
    v = _en_proyecto(curso_ui)
    assert [i for i, _ in _filas(v)] == [str(_fila(v, c).alumno.id) for c in
                                         ("100000001", "100000002", "100000003", "100000004")]


def test_agrupa_con_encabezados_y_deja_a_los_sin_equipo_al_final(curso_ui):
    _formar(curso_ui, "100000003", "100000001")  # equipo 1
    _formar(curso_ui, "100000004")               # equipo 2, de un solo alumno
    v = _en_proyecto(curso_ui)
    nombres = [n for _, n in _filas(v)]
    assert nombres == [
        "Equipo 1 · 2 alumnos", "ABREU SOLANO MARCOS", "GARCIA LOPEZ ANA",
        "Equipo 2 · 1 alumno", "GARCIA PEREZ ANA",
        "ACOSTA ORTEGA ELENA",  # sin equipo, al final y sin encabezado
    ]


def test_la_columna_equipo_muestra_el_numero(curso_ui):
    _formar(curso_ui, "100000001")
    v = _en_proyecto(curso_ui)
    columnas = list(v._tabla["columns"])
    valores = {i: v._tabla.item(i, "values") for i in v._tabla.get_children()}
    assert valores[str(_fila(v, "100000001").alumno.id)][columnas.index("equipo")] == "Equipo 1"
    assert valores[str(_fila(v, "100000002").alumno.id)][columnas.index("equipo")] == ""


def test_los_tonos_alternan_entre_equipos_y_los_sin_equipo_no_llevan_color(curso_ui):
    _formar(curso_ui, "100000001")
    _formar(curso_ui, "100000002")
    _formar(curso_ui, "100000003")
    v = _en_proyecto(curso_ui)
    filas = [i for i, _ in _filas(v)]
    por_equipo = {i: _etiquetas(v, i) for i in filas}
    assert "enc0" in por_equipo["equipo_1"] and "enc1" in por_equipo["equipo_2"] and "enc0" in por_equipo["equipo_3"]
    assert "fila0" in por_equipo[str(_fila(v, "100000001").alumno.id)]
    assert "fila1" in por_equipo[str(_fila(v, "100000002").alumno.id)]
    sin = por_equipo[str(_fila(v, "100000004").alumno.id)]
    assert not any(t.startswith(("fila", "enc")) for t in sin)


def test_fuera_de_proyecto_la_tabla_no_cambia(curso_ui):
    _formar(curso_ui, "100000003", "100000001")
    v = curso_ui.vista
    assert not any(i.startswith("equipo_") for i in v._tabla.get_children())
    _en_proyecto(curso_ui)
    assert any(i.startswith("equipo_") for i in v._tabla.get_children())
    v._selector_modo.set("Examen")
    v._cambiar_modo("Examen")
    assert not any(i.startswith("equipo_") for i in v._tabla.get_children())
    assert len(v._tabla.get_children()) == 4


def test_ordenar_por_otra_columna_ordena_dentro_de_cada_equipo(curso_ui):
    _formar(curso_ui, "100000003", "100000001")
    _formar(curso_ui, "100000002", "100000004")
    v = _en_proyecto(curso_ui)
    v._ordenar_por("nombre")  # ya estaba por nombre ascendente: invierte
    nombres = [n for _, n in _filas(v)]
    assert nombres == [
        "Equipo 1 · 2 alumnos", "GARCIA LOPEZ ANA", "ABREU SOLANO MARCOS",
        "Equipo 2 · 2 alumnos", "GARCIA PEREZ ANA", "ACOSTA ORTEGA ELENA",
    ]


def test_el_filtro_oculta_el_encabezado_de_un_equipo_sin_filas_visibles(curso_ui):
    _formar(curso_ui, "100000001")
    _formar(curso_ui, "100000002")
    v = _en_proyecto(curso_ui)
    v._buscar.insert(0, "acosta")
    v._dibujar_tabla()
    assert [n for _, n in _filas(v)] == ["Equipo 2 · 1 alumno", "ACOSTA ORTEGA ELENA"]


def test_ocultar_oyentes_quita_su_equipo_y_el_conteo_solo_cuenta_lo_visible(curso_ui):
    from core.models import TipoInscripcion

    oyente = curso_ui.srv.crear_alumno_en_curso(curso_ui.curso.id, "OYENTE UNO", TipoInscripcion.OYENTE)
    curso_ui.srv.formar_equipo(curso_ui.curso.id, [oyente.id])  # equipo 1, solo oyente
    _formar(curso_ui, "100000001")                              # equipo 2
    v = _en_proyecto(curso_ui)
    v.recargar()
    assert "Equipo 1 · 1 alumno" in [n for _, n in _filas(v)]
    v._ver_oyentes.deselect()
    v._dibujar_tabla()
    assert [n for _, n in _filas(v)][0] == "Equipo 2 · 1 alumno"
    assert not any("OYENTE" in n for _, n in _filas(v))


# ---------------- los encabezados no son alumnos ----------------
def test_un_clic_en_un_encabezado_no_carga_a_nadie(curso_ui):
    _formar(curso_ui, "100000001")
    v = _en_proyecto(curso_ui)
    antes = v._elegido
    _clic(curso_ui, "equipo_1")
    assert v._elegido is antes and v._entrada_alumno.get() == ""


def test_doble_clic_en_un_encabezado_no_abre_historial(curso_ui, monkeypatch):
    _formar(curso_ui, "100000001")
    v = _en_proyecto(curso_ui)
    abierto = []
    monkeypatch.setattr(curso_ui.app, "abrir_historial", lambda *a: abierto.append(a))
    curso_ui.app.update()
    x, y, _w, h = v._tabla.bbox("equipo_1")
    v._al_doble_clic(SimpleNamespace(x=x + 20, y=y + h // 2))
    assert abierto == []


def test_un_encabezado_no_se_puede_seleccionar(curso_ui):
    _formar(curso_ui, "100000001")
    v = _en_proyecto(curso_ui)
    v._tabla.selection_set("equipo_1")
    curso_ui.app.update()
    assert v._tabla.selection() == ()


def test_doble_clic_en_un_alumno_sigue_abriendo_su_historial(curso_ui, monkeypatch):
    _formar(curso_ui, "100000001")
    v = _en_proyecto(curso_ui)
    abierto = []
    monkeypatch.setattr(curso_ui.app, "abrir_historial", lambda *a: abierto.append(a))
    iid = str(_fila(v, "100000001").alumno.id)
    curso_ui.app.update()
    x, y, _w, h = v._tabla.bbox(iid)
    v._al_doble_clic(SimpleNamespace(x=x + 20, y=y + h // 2))
    assert abierto == [(curso_ui.curso.id, int(iid))]


def test_el_resumen_de_arriba_no_cuenta_los_encabezados(curso_ui):
    _formar(curso_ui, "100000001")
    v = _en_proyecto(curso_ui)
    assert "4 alumnos" in v._resumen.cget("text")
