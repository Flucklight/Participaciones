"""Pantalla Curso: visitantes de otro grupo (R21) con los diálogos reales (datos ficticios)."""

from datetime import date
from types import SimpleNamespace

import customtkinter as ctk
import pytest

from core.models import TipoInscripcion
from tests.conftest import buscar_dialogo as _dialogo, hay_pantalla
from tests.test_ui_curso import _escribir, _fila, _modo_examen, _texto_franja, curso_ui  # noqa: F401  (fixture)
from tests.test_ui_equipos import _boton_deshacer_visible

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")

REGULAR, VISITANTE = TipoInscripcion.REGULAR, TipoInscripcion.VISITANTE
HOY = date(2027, 3, 1)


@pytest.fixture
def visita_ui(curso_ui):
    """El curso abierto es el 3001; Ana es regular en el 3002 (origen) y visitante aquí."""
    srv = curso_ui.srv
    origen = srv.crear_curso("2027-I", "REDES", "3002")
    ana = srv.crear_alumno_en_curso(origen.id, "Prueba Ana", REGULAR, "200000001")
    srv.inscribir_visitante(curso_ui.curso.id, ana.id, origen.id)
    curso_ui.vista.recargar()
    curso_ui.app.update()
    curso_ui.origen, curso_ui.ana = origen, ana
    return curso_ui


def _textos(dialogo):
    return " ".join(w.cget("text") for w in dialogo.cuerpo.winfo_children() if isinstance(w, ctk.CTkLabel))


def _evento(ui, iid):
    ui.app.update()
    x, y, _w, h = ui.vista._tabla.bbox(iid)
    return SimpleNamespace(x=x + 20, y=y + h // 2, x_root=10, y_root=10)


def _fila_ana(ui):
    return next(f for f in ui.vista._filas if f.alumno.id == ui.ana.id)


# ---------------- tabla ----------------
def test_la_fila_del_visitante_dice_de_donde_viene_y_lleva_su_color(visita_ui):
    v, iid = visita_ui.vista, str(visita_ui.ana.id)
    assert "(visitante · 3002)" in v._tabla.item(iid, "values")[2]
    assert "visitante" in v._tabla.item(iid, "tags")
    assert _fila_ana(visita_ui).tipo == VISITANTE


def test_el_resumen_cuenta_a_los_visitantes_aparte(visita_ui):
    assert "1 visitante" in visita_ui.vista._resumen.cget("text")
    assert "4 alumnos" in visita_ui.vista._resumen.cget("text")  # los visitantes no cuentan como alumnos del grupo


def test_ocultar_oyentes_y_visitantes(visita_ui):
    v = visita_ui.vista
    v._ver_oyentes.deselect()
    v._dibujar_tabla()
    assert not v._tabla.exists(str(visita_ui.ana.id))
    v._ver_oyentes.select()
    v._dibujar_tabla()
    assert v._tabla.exists(str(visita_ui.ana.id))


def test_los_valores_de_la_fila_son_los_del_origen(visita_ui):
    visita_ui.srv.registrar_para_alumno(visita_ui.origen.id, visita_ui.ana.id, 7, HOY)
    visita_ui.vista.recargar()
    assert _fila_ana(visita_ui).total == 7
    assert visita_ui.vista._tabla.item(str(visita_ui.ana.id), "values")[3] == "7"


# ---------------- capturar ----------------
def test_registrar_participacion_avisa_donde_se_guardo(visita_ui):
    v = visita_ui.vista
    _escribir(v, "200000001", "5")
    v.guardar()
    assert "guardado en el grupo 3002" in _texto_franja(v)
    assert visita_ui.srv.total_alumno(visita_ui.origen.id, visita_ui.ana.id) == 5
    assert _fila_ana(visita_ui).total == 5
    nota = visita_ui.srv.historial(visita_ui.origen.id, visita_ui.ana.id)[0].nota
    assert nota == "Grupo 3001"
    assert _boton_deshacer_visible(v)
    v.deshacer()
    assert visita_ui.srv.total_alumno(visita_ui.origen.id, visita_ui.ana.id) == 0


def test_registrar_por_nombre_en_el_registro_rapido(visita_ui):
    v = visita_ui.vista
    _escribir(v, "prueba ana", "3")
    v.guardar()
    assert "guardado en el grupo 3002" in _texto_franja(v)


def test_examen_sin_homonimo_en_el_origen_avisa_y_no_guarda(visita_ui):
    srv, v = visita_ui.srv, visita_ui.vista
    srv.crear_examen(visita_ui.curso.id, "Parcial 1")
    v.recargar()
    _modo_examen(visita_ui)
    v._cargar_examenes()
    _escribir(v, "200000001", "8")
    v.guardar()
    assert _texto_franja(v).startswith("⚠") and "El grupo 3002 no tiene un examen" in _texto_franja(v)
    assert srv.listar_examenes(visita_ui.origen.id) == []


def test_examen_con_homonimo_se_guarda_en_el_origen_y_se_ve_en_la_tabla(visita_ui):
    srv, v = visita_ui.srv, visita_ui.vista
    eb = srv.crear_examen(visita_ui.curso.id, "Parcial 1")
    ea = srv.crear_examen(visita_ui.origen.id, "Parcial 1")
    v.recargar()
    _modo_examen(visita_ui)
    v._cargar_examenes()
    _escribir(v, "200000001", "8")
    v.guardar()
    assert "guardado en el grupo 3002" in _texto_franja(v)
    assert srv._repo.obtener_calificacion(ea.id, visita_ui.ana.id).puntos == 8
    assert srv._repo.obtener_calificacion(eb.id, visita_ui.ana.id) is None
    assert _fila_ana(visita_ui).calificaciones == {eb.id: 8}
    v.deshacer()
    assert srv._repo.obtener_calificacion(ea.id, visita_ui.ana.id) is None


def test_tareas_del_visitante_se_guardan_en_el_origen(visita_ui):
    v = visita_ui.vista
    v._selector_modo.set("Tareas")
    v._cambiar_modo("Tareas")
    _escribir(v, "200000001", "90")
    v.guardar()
    assert "guardado en el grupo 3002" in _texto_franja(v)
    assert visita_ui.srv._repo.obtener_tareas(visita_ui.origen.id, visita_ui.ana.id).puntos == 90
    assert _fila_ana(visita_ui).tareas == 90


# ---------------- agregar un visitante ----------------
def _agregar_visitante_con(ui, consulta, despues):
    """Abre «Agregar alumno», pulsa «Agregar como visitante…» y corre `despues(dialogo_visitante)`."""
    ui.app.after(300, lambda: _dialogo(ui.app).cerrar("visitante"))

    def segundo():
        d = _dialogo(ui.app)
        d._consulta.insert(0, consulta)
        d._buscar_ahora()
        despues(d)

    ui.app.after(900, segundo)
    ui.vista.agregar_alumno()


def _otra_regular(ui, nombre="Prueba Beto", cuenta="200000002", grupo="3002"):
    origen = next((c for c in ui.srv.listar_cursos() if c.grupo == grupo), None) or ui.srv.crear_curso("2027-I", "REDES", grupo)
    return ui.srv.crear_alumno_en_curso(origen.id, nombre, REGULAR, cuenta)


def test_agregar_alumno_ofrece_el_camino_de_visitante(curso_ui):
    visto = {}

    def mirar():
        d = _dialogo(curso_ui.app)
        visto["boton"] = any(
            isinstance(w, ctk.CTkButton) and "visitante" in w.cget("text") for w in d.cuerpo.winfo_children()
        )
        d.cancelar()

    curso_ui.app.after(300, mirar)
    curso_ui.vista.agregar_alumno()
    assert visto["boton"]


def test_agregar_visitante_busca_elige_e_inscribe(curso_ui):
    beto = _otra_regular(curso_ui)

    def aceptar(d):
        d._aceptar()

    _agregar_visitante_con(curso_ui, "200000002", aceptar)
    v = curso_ui.vista
    assert "agregado como visitante" in _texto_franja(v) and "grupo de origen es el 3002" in _texto_franja(v)
    assert curso_ui.srv.tipo_inscripcion(curso_ui.curso.id, beto.id) == VISITANTE
    assert "(visitante · 3002)" in v._tabla.item(str(beto.id), "values")[2]


def test_con_varias_coincidencias_hay_que_elegir(curso_ui):
    ana, beto = _otra_regular(curso_ui, "Prueba Ana", "200000001"), _otra_regular(curso_ui, "Prueba Beto", "200000002")
    resultado = {}

    def intentar(d):
        d._aceptar()  # sin elegir
        resultado["sin_elegir"] = d._error.cget("text")
        d._opcion.set(f"{beto.id}:{next(c.id for c in curso_ui.srv.listar_cursos() if c.grupo == '3002')}")
        d._aceptar()

    _agregar_visitante_con(curso_ui, "prueba", intentar)
    assert "elige" in resultado["sin_elegir"]
    assert curso_ui.srv.tipo_inscripcion(curso_ui.curso.id, beto.id) == VISITANTE
    assert curso_ui.srv.buscar_alumnos_en_curso(curso_ui.curso.id, str(ana.num_cuenta)) == []


def test_sin_coincidencias_el_dialogo_avisa(curso_ui):
    _otra_regular(curso_ui)
    visto = {}

    def mirar(d):
        visto["texto"] = " ".join(w.cget("text") for w in d._lista.winfo_children() if isinstance(w, ctk.CTkLabel))
        d.cancelar()

    _agregar_visitante_con(curso_ui, "nadie con ese nombre", mirar)
    assert "Ningún alumno regular" in visto["texto"]


def test_sin_otros_grupos_el_dialogo_lo_explica(curso_ui):
    visto = {}

    def mirar(d):
        visto["texto"] = _textos(d)
        d.cancelar()

    _agregar_visitante_con(curso_ui, "x", mirar)
    assert "No hay otros grupos de esta materia" in visto["texto"]


# ---------------- quitar la visita ----------------
def test_el_boton_se_habilita_con_un_visitante_y_lo_quita_con_deshacer(visita_ui):
    v, srv = visita_ui.vista, visita_ui.srv
    srv.registrar_para_alumno(visita_ui.origen.id, visita_ui.ana.id, 5, HOY)
    v._tabla.selection_set(str(visita_ui.ana.id))
    visita_ui.app.update()
    assert str(v._boton_eliminar_alumno.cget("state")) == "normal"
    visto = {}

    def confirmar():
        d = _dialogo(visita_ui.app)
        visto["texto"] = _textos(d)
        d.cerrar(True)

    visita_ui.app.after(300, confirmar)
    v.eliminar_alumno()
    assert "Dejará de ser visitante de este grupo" in visto["texto"] and "grupo 3002 y no se tocan" in visto["texto"]
    assert "ya no es visitante de este grupo" in _texto_franja(v)
    assert not v._tabla.exists(str(visita_ui.ana.id))
    assert srv.total_alumno(visita_ui.origen.id, visita_ui.ana.id) == 5  # el origen no se toca
    assert _boton_deshacer_visible(v)
    v.deshacer()
    assert v._tabla.exists(str(visita_ui.ana.id)) and _fila_ana(visita_ui).tipo == VISITANTE
    assert _fila_ana(visita_ui).total == 5


def test_clic_derecho_en_un_visitante_ofrece_quitarlo(visita_ui):
    v = visita_ui.vista
    menu = v._menu_alumno(_evento(visita_ui, str(visita_ui.ana.id)))
    assert menu.entrycget(0, "label") == "Quitar visitante…"

    def confirmar():
        _dialogo(visita_ui.app).cerrar(True)

    visita_ui.app.after(300, confirmar)
    menu.invoke(0)
    assert not v._tabla.exists(str(visita_ui.ana.id))


# ---------------- equipos entre grupos ----------------
def test_el_aviso_de_equipo_dice_en_que_grupo_ya_tiene_equipo(visita_ui):
    srv, v = visita_ui.srv, visita_ui.vista
    srv.formar_equipo(visita_ui.origen.id, [visita_ui.ana.id])  # en su origen (3002)
    v.alternar_formar()
    visita_ui.app.update()
    v._tabla.selection_set(str(visita_ui.ana.id))
    visita_ui.app.update()
    visto = {}

    def intentar():
        d = _dialogo(visita_ui.app)
        d._aceptar()
        visto["error"] = d._error.cget("text")
        d.cancelar()

    visita_ui.app.after(300, intentar)
    v.crear_equipo()
    assert "equipo 1 del grupo 3002" in visto["error"] and "un solo equipo" in visto["error"]
    assert srv.equipos_del_curso(visita_ui.curso.id) == []


# ---------------- historial ----------------
def test_el_historial_de_un_visitante_muestra_los_datos_del_origen_y_regresa_al_grupo(visita_ui):
    visita_ui.srv.registrar_para_alumno(visita_ui.origen.id, visita_ui.ana.id, 4, HOY)
    visita_ui.app.abrir_historial(visita_ui.curso.id, visita_ui.ana.id)
    visita_ui.app.update()
    h = visita_ui.app._vista
    assert h._curso_id == visita_ui.origen.id and h._volver_a == visita_ui.curso.id
    assert len(h._lineas) == 1
    assert [c.id for c in h._cursos] == [visita_ui.origen.id]  # el grupo que solo visita no se lista


# ---------------- eliminar el curso de origen / exportar ----------------
def test_eliminar_el_curso_de_origen_avisa_cuantos_visitantes_dejan_de_aparecer(visita_ui):
    visita_ui.app.mostrar("cursos")
    visita_ui.app.update()
    visto = {}

    def mirar():
        d = _dialogo(visita_ui.app)
        visto["texto"] = _textos(d)
        d.cancelar()

    visita_ui.app.after(300, mirar)
    visita_ui.app._vista.eliminar(visita_ui.origen)
    assert "visitantes en otros grupos (1)" in visto["texto"]


def test_exportar_ofrece_incluir_oyentes_y_visitantes(visita_ui):
    visto = {}

    def mirar():
        d = _dialogo(visita_ui.app)
        visto["casilla"] = d._oyentes.cget("text")
        visto["estado"] = str(d._oyentes.cget("state"))
        d.cancelar()

    visita_ui.app.after(300, mirar)
    visita_ui.vista.exportar()
    assert visto["casilla"] == "Incluir oyentes y visitantes" and visto["estado"] == "normal"
