"""Botón «⚖ Ponderaciones», su diálogo y la asignación de la ponderación de exámenes (datos ficticios)."""

import customtkinter as ctk
import pytest

from core.calificacion_final import Ponderaciones
from tests.conftest import buscar_dialogo, hay_pantalla
from tests.test_ui_curso import _fila, _texto_franja, curso_ui  # noqa: F401  (fixture)

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def _botones(raiz):
    for hijo in raiz.winfo_children():
        if isinstance(hijo, ctk.CTkButton):
            yield hijo
        yield from _botones(hijo)


def _abrir(ui, ajustar=None, aceptar=False, **kwargs):
    """Abre el diálogo de ponderaciones, lo ajusta y lo acepta o lo cancela. Devuelve lo que vio."""
    vistos = {}

    def accion():
        d = buscar_dialogo(ui.app)
        if d is None:
            return
        try:
            vistos["valores"] = {c: e.get() for c, e in d._campos.items()}
            vistos["suma"] = d._suma.cget("text")
            if ajustar:
                ajustar(d)
                vistos["suma_despues"] = d._suma.cget("text")
            if aceptar:
                d._aceptar()
            vistos["error"] = d._error.cget("text")
        except BaseException as error:  # noqa: BLE001
            vistos["excepcion"] = error
        finally:
            try:
                if d.winfo_exists():
                    d.cancelar()
            except Exception:  # noqa: BLE001
                pass

    ui.app.after(300, accion)
    vistos["resultado"] = ui.vista.ponderaciones(**kwargs)
    if "excepcion" in vistos:
        raise vistos["excepcion"]
    return vistos


def _poner(d, **valores):
    for clave, valor in valores.items():
        d._campos[clave].delete(0, "end")
        d._campos[clave].insert(0, str(valor))
    d._actualizar_suma()


def _final(ui, cuenta):
    return next(r.final for r in ui.srv.resumen_curso(ui.curso.id) if r.alumno.num_cuenta == cuenta)


# ================= botón y diálogo =================
def test_el_encabezado_tiene_el_boton_ponderaciones(curso_ui):
    assert any("Ponderaciones" in b.cget("text") for b in _botones(curso_ui.vista))


def test_abre_con_los_valores_actuales_y_la_suma(curso_ui):
    vistos = _abrir(curso_ui)
    assert vistos["valores"] == {"participaciones": "10", "examenes": "0", "tareas": "20", "proyecto": "40"}
    assert vistos["suma"] == "Suma: 70 %  ·  faltan 30 %"
    assert vistos["resultado"] is None  # se cerró sin guardar


def test_abre_con_lo_guardado_del_curso(curso_ui):
    curso_ui.srv.establecer_ponderaciones(curso_ui.curso.id, 5.5, 25, 20, 49.5)
    assert _abrir(curso_ui)["valores"] == {"participaciones": "5.5", "examenes": "25", "tareas": "20", "proyecto": "49.5"}


def test_la_suma_se_actualiza_en_vivo_con_el_mensaje_correcto(curso_ui):
    def ajustar(d):
        _poner(d, examenes=30)
        assert d._suma.cget("text") == "Suma: 100 %"
        _poner(d, proyecto=50)
        assert d._suma.cget("text") == "Suma: 110 %  ·  10 % de puntos extra"
        _poner(d, proyecto=20)
        assert d._suma.cget("text") == "Suma: 80 %  ·  faltan 20 %"
        _poner(d, tareas=12.5)
        assert d._suma.cget("text") == "Suma: 72.5 %  ·  faltan 27.5 %"

    assert "excepcion" not in _abrir(curso_ui, ajustar)


def test_un_texto_que_no_es_numero_avisa_en_la_suma_y_no_guarda(curso_ui):
    vistos = _abrir(curso_ui, lambda d: _poner(d, tareas="abc"), aceptar=True)
    assert "Escribe solo números" in vistos["suma_despues"]
    assert "debe ser un número" in vistos["error"]
    assert curso_ui.srv.ponderaciones_de(curso_ui.curso.id) == Ponderaciones()  # nada guardado


def test_un_campo_vacio_se_avisa_dentro_del_dialogo(curso_ui):
    vistos = _abrir(curso_ui, lambda d: _poner(d, proyecto=""), aceptar=True)
    assert "Escribe la ponderación de proyecto final" in vistos["error"]


@pytest.mark.parametrize("valor", [-5, 101, 1000])
def test_fuera_de_0_a_100_se_rechaza_dentro_del_dialogo(curso_ui, valor):
    vistos = _abrir(curso_ui, lambda d: _poner(d, examenes=valor), aceptar=True)
    assert "entre 0 y 100" in vistos["error"]
    assert curso_ui.srv.ponderaciones_de(curso_ui.curso.id) == Ponderaciones()


def test_cancelar_no_guarda_nada(curso_ui):
    vistos = _abrir(curso_ui, lambda d: _poner(d, examenes=30, proyecto=50))
    assert vistos["resultado"] is None
    assert curso_ui.srv.ponderaciones_de(curso_ui.curso.id) == Ponderaciones()
    assert "guardadas" not in _texto_franja(curso_ui.vista)


def test_restablecer_rellena_los_campos_sin_guardar(curso_ui):
    curso_ui.srv.establecer_ponderaciones(curso_ui.curso.id, 25, 25, 25, 25)

    def ajustar(d):
        d._restablecer.invoke()
        assert {c: e.get() for c, e in d._campos.items()} == {
            "participaciones": "10", "examenes": "0", "tareas": "20", "proyecto": "40"}
        assert d._suma.cget("text") == "Suma: 70 %  ·  faltan 30 %"

    vistos = _abrir(curso_ui, ajustar)
    assert "excepcion" not in vistos
    assert curso_ui.srv.ponderaciones_de(curso_ui.curso.id) == Ponderaciones(25, 25, 25, 25)  # sin Guardar no cambia


def test_guardar_actualiza_la_tabla_y_lo_dice_la_franja(curso_ui):
    srv, cid, v = curso_ui.srv, curso_ui.curso.id, curso_ui.vista
    srv.registrar_proyecto(cid, "100000001", 100)
    v.recargar()
    celda = lambda: v._tabla.item(str(_fila(v, "100000001").alumno.id), "values")[list(v._tabla["columns"]).index("final")]  # noqa: E731
    assert celda() == "40"  # 40 % por omisión
    vistos = _abrir(curso_ui, lambda d: _poner(d, proyecto=50), aceptar=True)
    assert vistos["resultado"] == Ponderaciones(10, 0, 20, 50)
    assert celda() == "50"
    assert "Ponderaciones guardadas" in _texto_franja(v) and "proyecto 50 %" in _texto_franja(v)
    assert "suma 80 %" in _texto_franja(v)


def test_guardar_una_suma_mayor_de_100_se_permite(curso_ui):
    vistos = _abrir(curso_ui, lambda d: _poner(d, participaciones=20, examenes=40, tareas=30, proyecto=50), aceptar=True)
    assert vistos["resultado"].suma == 140
    assert "suma 140 %" in _texto_franja(curso_ui.vista)


def test_acepta_coma_decimal_y_signo_porcentaje(curso_ui):
    _abrir(curso_ui, lambda d: _poner(d, tareas="12,5", proyecto="45 %"), aceptar=True)
    assert curso_ui.srv.ponderaciones_de(curso_ui.curso.id) == Ponderaciones(10, 0, 12.5, 45)


def test_enter_en_un_campo_guarda(curso_ui):
    def ajustar(d):
        assert d._campos["proyecto"]._entry.bind("<Return>")

    assert "excepcion" not in _abrir(curso_ui, ajustar)


def test_el_foco_empieza_donde_se_pide(curso_ui):
    enfocados = []

    def ajustar(d):
        enfocados.append(d.focus_get() is d._campos["examenes"]._entry)

    _abrir(curso_ui, ajustar, enfocar="examenes")
    assert enfocados == [True]


def test_guardar_ponderaciones_no_cambia_ningun_componente(curso_ui):
    srv, cid = curso_ui.srv, curso_ui.curso.id
    srv.registrar(cid, "100000001", 4)
    srv.registrar_tareas(cid, "100000001", 85)
    antes = [(r.total, r.tareas) for r in srv.resumen_curso(cid)]
    _abrir(curso_ui, lambda d: _poner(d, examenes=30), aceptar=True)
    assert antes == [(r.total, r.tareas) for r in srv.resumen_curso(cid)]
