"""Nombre y proyecto del equipo en pantalla, clic en el encabezado y columnas centradas (datos ficticios)."""

from types import SimpleNamespace

import pytest

from tests.conftest import buscar_dialogo, hay_pantalla
from tests.test_ui_curso import _fila, _texto_franja, curso_ui  # noqa: F401  (fixture)
from tests.test_ui_equipos import _activar_formar, _clic, _crear, _en_proyecto, _filas, _formar, _seleccionar

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def _encabezados(v):
    return [n for i, n in _filas(v) if i.startswith("equipo_")]


def _editar_con(ui, numero, nombre=None, proyecto=None, aceptar=True):
    """Doble clic en el encabezado del equipo: abre el diálogo, lo llena y lo acepta o cancela."""
    v = ui.vista
    vistos = {}

    def accion():
        d = buscar_dialogo(ui.app)
        if d is None:
            return
        try:
            vistos["nombre"], vistos["proyecto"] = d._nombre.get(), d._proyecto.get()
            for campo, valor in ((d._nombre, nombre), (d._proyecto, proyecto)):
                if valor is not None:
                    campo.delete(0, "end")
                    campo.insert(0, valor)
            if aceptar:
                d._aceptar()
        finally:
            if d.winfo_exists():
                d.cancelar()

    ui.app.after(300, accion)
    ui.app.update()
    x, y, _w, h = v._tabla.bbox(f"equipo_{numero}")
    v._al_doble_clic(SimpleNamespace(x=x + 20, y=y + h // 2))
    return vistos


# ---------------- formar con nombre y proyecto ----------------
def test_al_crear_el_equipo_se_abre_el_dialogo_con_el_numero_de_alumnos(curso_ui):
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001", "100000002")
    titulos = []

    def mirar():
        d = buscar_dialogo(curso_ui.app)
        titulos.append(d.title())
        d.cancelar()

    curso_ui.app.after(300, mirar)
    v.crear_equipo()
    assert titulos == ["Nuevo equipo con 2 alumnos"]


def test_el_encabezado_menciona_el_nombre_y_el_proyecto(curso_ui):
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001", "100000002")
    _crear(curso_ui, "Los Cuervos", "Sistema de riego")
    assert _encabezados(v) == ["Equipo 1 · 2 alumnos · Los Cuervos · Sistema de riego"]
    assert "Equipo 1 formado con 2 alumnos" in _texto_franja(v)


def test_solo_nombre_o_solo_proyecto_o_ninguno(curso_ui):
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001")
    _crear(curso_ui, nombre="Solo nombre")
    _seleccionar(curso_ui, "100000002")
    _crear(curso_ui, proyecto="Solo proyecto")
    _seleccionar(curso_ui, "100000003")
    _crear(curso_ui)
    assert _encabezados(v) == [
        "Equipo 1 · 1 alumno · Solo nombre",
        "Equipo 2 · 1 alumno · Solo proyecto",
        "Equipo 3 · 1 alumno",
    ]


def test_cancelar_el_dialogo_no_forma_el_equipo_y_conserva_la_seleccion(curso_ui):
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001", "100000002")
    _crear(curso_ui, "Los Cuervos", aceptar=False)
    assert curso_ui.srv.equipos_del_curso(curso_ui.curso.id) == []
    assert "Se canceló" in _texto_franja(v) and len(v._tabla.selection()) == 2
    _crear(curso_ui)  # y se puede volver a intentar; el número no se gastó
    assert "Equipo 1 formado" in _texto_franja(v)


def test_un_nombre_demasiado_largo_se_avisa_dentro_del_dialogo(curso_ui):
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001")
    errores = []

    def probar():
        d = buscar_dialogo(curso_ui.app)
        d._nombre.insert(0, "x" * 61)
        d._aceptar()
        errores.append(d._error.cget("text"))
        d._nombre.delete(0, "end")
        d._nombre.insert(0, "Corto")
        d._aceptar()  # ya con un nombre válido se forma

    curso_ui.app.after(300, probar)
    v.crear_equipo()
    assert "nombre del equipo" in errores[0]
    assert _encabezados(v) == ["Equipo 1 · 1 alumno · Corto"]


def test_deshacer_la_formacion_quita_tambien_sus_datos_de_la_tabla(curso_ui):
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001")
    _crear(curso_ui, "Los Cuervos", "Sistema de riego")
    v.deshacer()
    assert _encabezados(v) == []
    _seleccionar(curso_ui, "100000002")
    _crear(curso_ui)
    assert _encabezados(v) == ["Equipo 2 · 1 alumno"]  # el equipo 2 no hereda lo del 1


def test_el_aviso_de_quien_ya_tiene_equipo_sale_antes_del_dialogo(curso_ui):
    _formar(curso_ui, "100000001")
    v = _activar_formar(curso_ui)
    _seleccionar(curso_ui, "100000001", "100000002")
    v.crear_equipo()  # no hay diálogo pendiente: si se abriera, la prueba se colgaría
    assert "Ya tienen equipo" in _texto_franja(v) and "ABREU SOLANO MARCOS" in _texto_franja(v)


# ---------------- editar con doble clic ----------------
def test_doble_clic_en_el_encabezado_abre_el_dialogo_con_los_datos_actuales(curso_ui):
    curso_ui.srv.formar_equipo(
        curso_ui.curso.id, [_fila(curso_ui.vista, "100000001").alumno.id], "Los Cuervos", "Sistema de riego"
    )
    _en_proyecto(curso_ui)
    vistos = _editar_con(curso_ui, 1, aceptar=False)
    assert vistos == {"nombre": "Los Cuervos", "proyecto": "Sistema de riego"}


def test_editar_cambia_el_encabezado_y_se_puede_quitar(curso_ui):
    _formar(curso_ui, "100000001")
    v = _en_proyecto(curso_ui)
    _editar_con(curso_ui, 1, "Los Halcones", "App de tareas")
    assert _encabezados(v) == ["Equipo 1 · 1 alumno · Los Halcones · App de tareas"]
    assert "Equipo 1 actualizado" in _texto_franja(v)
    _editar_con(curso_ui, 1, "", "")
    assert _encabezados(v) == ["Equipo 1 · 1 alumno"]


def test_cancelar_la_edicion_no_cambia_nada(curso_ui):
    curso_ui.srv.formar_equipo(curso_ui.curso.id, [_fila(curso_ui.vista, "100000001").alumno.id], "Uno")
    v = _en_proyecto(curso_ui)
    _editar_con(curso_ui, 1, "Otro", aceptar=False)
    assert _encabezados(v) == ["Equipo 1 · 1 alumno · Uno"]


def test_editar_no_altera_las_calificaciones_ni_los_miembros(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    curso_ui.srv.registrar_proyecto(curso_ui.curso.id, "equipo 1", 9)
    v = _en_proyecto(curso_ui)
    _editar_con(curso_ui, 1, "Nuevo", "Proyecto")
    notas = {r.alumno.num_cuenta: r.proyecto for r in curso_ui.srv.resumen_curso(curso_ui.curso.id)}
    assert notas["100000001"] == notas["100000002"] == 9
    assert len(curso_ui.srv.equipos_del_curso(curso_ui.curso.id)[0].miembros) == 2


def test_se_evalua_al_equipo_desde_el_clic_en_su_encabezado(curso_ui):
    _formar(curso_ui, "100000001", "100000002")
    v = _en_proyecto(curso_ui)
    _clic(curso_ui, "equipo_1")
    v._entrada_decimas.delete(0, "end")
    v._entrada_decimas.insert(0, "9")
    v.guardar()
    notas = {r.alumno.num_cuenta: r.proyecto for r in curso_ui.srv.resumen_curso(curso_ui.curso.id)}
    assert notas["100000001"] == notas["100000002"] == 9 and notas["100000003"] == 0


# ---------------- columnas centradas ----------------
def test_los_valores_desde_decimas_van_centrados(curso_ui):
    curso_ui.srv.crear_examen(curso_ui.curso.id, "Parcial 1")
    v = curso_ui.vista
    v.recargar()
    for columna in v._tabla["columns"]:
        if columna in ("total", "tareas", "proyecto", "ultima") or columna.startswith("examen_"):
            assert str(v._tabla.column(columna, "anchor")) == "center", columna
            assert str(v._tabla.heading(columna, "anchor")) == "center", columna


def test_en_proyecto_tambien_van_centrados(curso_ui):
    v = _en_proyecto(curso_ui)
    for columna in ("equipo", "total", "tareas", "proyecto", "ultima"):
        assert str(v._tabla.column(columna, "anchor")) == "center", columna


def test_la_columna_nombre_se_ensancha_para_que_quepa_el_encabezado_del_equipo(curso_ui):
    _formar(curso_ui, "100000001")
    v = _en_proyecto(curso_ui)
    ancho_sin_datos = int(v._tabla.column("nombre", "width"))
    curso_ui.srv.editar_equipo(curso_ui.curso.id, 1, "Los Cuervos del Norte", "Sistema de riego automatizado con sensores")
    v.recargar()
    ancho = int(v._tabla.column("nombre", "width"))
    assert ancho > ancho_sin_datos and ancho <= 480
    assert int(v._tabla.column("nombre", "minwidth")) == ancho  # que ttk no la encoja al caber
    v._selector_modo.set("Tareas")
    v._cambiar_modo("Tareas")
    assert int(v._tabla.column("nombre", "width")) == 320  # fuera de Proyecto vuelve a su ancho
    assert int(v._tabla.column("nombre", "minwidth")) == 240
