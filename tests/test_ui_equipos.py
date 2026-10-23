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


# ================= formar equipos =================
def _activar_formar(ui):
    v = _en_proyecto(ui)
    v.alternar_formar()
    ui.app.update()
    return v


def _seleccionar(ui, *cuentas):
    v = ui.vista
    v._tabla.selection_set([str(_fila(v, c).alumno.id) for c in cuentas])
    ui.app.update()


def _boton_deshacer_visible(v):
    return v._boton_deshacer.winfo_manager() == "pack"


def test_formar_equipos_activa_y_desactiva_la_seleccion_multiple(curso_ui):
    v = _en_proyecto(curso_ui)
    assert str(v._tabla.cget("selectmode")) == "browse" and not v._formando
    v.alternar_formar()
    assert v._formando and str(v._tabla.cget("selectmode")) == "extended"
    assert v._boton_formar.cget("fg_color") == tema.COLOR_PROYECTO  # se ve activo
    assert "Ninguno seleccionado" in v._etiqueta_seleccion.cget("text")
    assert str(v._boton_crear_equipo.cget("state")) == "disabled"
    v.alternar_formar()
    assert not v._formando and str(v._tabla.cget("selectmode")) == "browse"


def test_la_fila_de_equipos_solo_existe_en_proyecto(curso_ui):
    v = curso_ui.vista
    assert v._fila_equipos.winfo_manager() == ""
    _en_proyecto(curso_ui)
    assert v._fila_equipos.winfo_manager() == "pack"
    v._selector_modo.set("Tareas")
    v._cambiar_modo("Tareas")
    assert v._fila_equipos.winfo_manager() == ""


def test_formando_el_clic_ya_no_carga_al_alumno(curso_ui):
    v = _activar_formar(curso_ui)
    _clic(curso_ui, str(_fila(v, "100000001").alumno.id))
    assert v._elegido is None and v._entrada_alumno.get() == ""


def test_la_barra_cuenta_los_seleccionados_y_ajusta_el_boton(curso_ui):
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001")
    assert v._etiqueta_seleccion.cget("text") == "1 seleccionado"
    assert v._boton_crear_equipo.cget("text") == "Crear equipo con 1 alumno"
    assert str(v._boton_crear_equipo.cget("state")) == "normal"
    _seleccionar(curso_ui, "100000001", "100000002", "100000003")
    assert v._etiqueta_seleccion.cget("text") == "3 seleccionados"
    assert v._boton_crear_equipo.cget("text") == "Crear equipo con 3 alumnos"


def test_los_encabezados_no_cuentan_en_la_seleccion(curso_ui):
    _formar(curso_ui, "100000001")
    v = _activar_formar(curso_ui)
    v._tabla.selection_set(["equipo_1", str(_fila(v, "100000002").alumno.id)])
    curso_ui.app.update()
    assert v._etiqueta_seleccion.cget("text") == "1 seleccionado"


def test_crear_equipo_asigna_el_numero_reagrupa_y_resalta(curso_ui):
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000003", "100000001")
    v.crear_equipo()
    assert "Equipo 1 formado con 2 alumnos" in _texto_franja(v)
    assert [n for _, n in _filas(v)][:3] == ["Equipo 1 · 2 alumnos", "ABREU SOLANO MARCOS", "GARCIA LOPEZ ANA"]
    assert v._tabla.selection() == () and v._formando  # sigue formando
    for cuenta in ("100000001", "100000003"):
        assert "reciente" in _etiquetas(v, str(_fila(v, cuenta).alumno.id))
    assert _boton_deshacer_visible(v)
    _seleccionar(curso_ui, "100000002")
    v.crear_equipo()
    assert "Equipo 2 formado con 1 alumno" in _texto_franja(v)


def test_sin_seleccion_crear_no_hace_nada(curso_ui):
    v = _activar_formar(curso_ui)
    v.crear_equipo()
    assert curso_ui.srv.equipos_del_curso(curso_ui.curso.id) == []


def test_incluir_a_alguien_con_equipo_se_rechaza_y_dice_quien(curso_ui):
    _formar(curso_ui, "100000001")
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001", "100000002")
    v.crear_equipo()
    texto = _texto_franja(v)
    assert "ABREU SOLANO MARCOS" in texto and "equipo 1" in texto and "Sácalos" in texto
    assert [e.numero for e in curso_ui.srv.equipos_del_curso(curso_ui.curso.id)] == [1]
    assert len(v._tabla.selection()) == 2  # la selección se conserva para corregir
    assert not _boton_deshacer_visible(v)


def test_deshacer_la_formacion_libera_a_los_miembros(curso_ui):
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001", "100000002")
    v.crear_equipo()
    v.deshacer()
    assert curso_ui.srv.equipos_del_curso(curso_ui.curso.id) == []
    assert "Se deshizo el equipo 1" in _texto_franja(v)
    assert not any(i.startswith("equipo_") for i in v._tabla.get_children())
    v.deshacer()  # una sola vez: no pasa nada más
    _seleccionar(curso_ui, "100000001")
    v.crear_equipo()
    assert "Equipo 2 formado" in _texto_franja(v)  # el número del equipo deshecho no se reutiliza


def test_desactivar_o_cambiar_de_modo_limpia_la_seleccion(curso_ui):
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001", "100000002")
    v.alternar_formar()
    assert v._tabla.selection() == ()
    v.alternar_formar()
    _seleccionar(curso_ui, "100000001")
    v._selector_modo.set("Tareas")
    v._cambiar_modo("Tareas")
    assert v._tabla.selection() == () and not v._formando
    assert str(v._tabla.cget("selectmode")) == "browse"


def test_otra_captura_reemplaza_lo_deshacible(curso_ui):
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001")
    v.crear_equipo()
    v._selector_modo.set("Participación")
    v._cambiar_modo("Participación")
    v._entrada_alumno.insert(0, "100000002")
    v._entrada_decimas.insert(0, "5")
    v.guardar()
    v.deshacer()  # deshace la participación, no el equipo
    assert [e.numero for e in curso_ui.srv.equipos_del_curso(curso_ui.curso.id)] == [1]
    assert {r.alumno.num_cuenta: r.total for r in curso_ui.srv.resumen_curso(curso_ui.curso.id)}["100000002"] == 0


def test_formar_equipos_no_altera_las_calificaciones(curso_ui):
    curso_ui.srv.registrar_tareas(curso_ui.curso.id, "100000001", 85)
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001", "100000002")
    v.crear_equipo()
    assert {r.alumno.num_cuenta: r.tareas for r in curso_ui.srv.resumen_curso(curso_ui.curso.id)}["100000001"] == 85
