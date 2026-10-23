"""Asignar la ponderación de exámenes al crear el primero y recordarla (datos ficticios)."""

import time

import pytest

from core.calificacion_final import Ponderaciones
from tests.conftest import buscar_dialogo, hay_pantalla
from tests.test_ui_curso import _texto_franja, curso_ui  # noqa: F401  (fixture)

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def _crear_examen(ui, nombre="Parcial 1", al_ponderar=None):
    """«＋ Nuevo» examen con su diálogo real. Si luego se abre el de ponderaciones lo describe en el
    resultado ("valores", "mensaje", "foco") y le aplica `al_ponderar`; si no se abre, "dialogo" es False."""
    visto = {}

    def segundo():
        d = buscar_dialogo(ui.app)
        visto["dialogo"] = d is not None
        try:
            if d is not None:
                visto["valores"] = {c: e.get() for c, e in d._campos.items()}
                visto["foco"] = d.focus_get() is d._campos["examenes"]._entry
                if al_ponderar:
                    al_ponderar(d)
        except BaseException as error:  # noqa: BLE001
            visto["excepcion"] = error
        finally:
            visto["listo"] = True
            if d is not None and d.winfo_exists():
                d.cancelar()

    def primero():
        d = buscar_dialogo(ui.app)
        d._nombre.insert(0, nombre)
        d._aceptar()
        ui.app.after(300, segundo)

    ui.app.after(300, primero)
    ui.vista.nuevo_examen()
    for _ in range(60):  # espera a que el segundo paso haya corrido (haya o no diálogo)
        if "listo" in visto:
            break
        ui.app.update()
        time.sleep(0.03)
    if "excepcion" in visto:
        raise visto["excepcion"]
    return visto


def _asignar(**valores):
    def accion(d):
        for clave, valor in valores.items():
            d._campos[clave].delete(0, "end")
            d._campos[clave].insert(0, str(valor))
        d._aceptar()
    return accion


def _pesos(ui):
    return ui.srv.ponderaciones_de(ui.curso.id)


def _abrir(ui):
    ui.app.abrir_curso(ui.curso.id)
    ui.app.update()
    return ui.app._vista


# ================= al crear el primer examen =================
def test_el_primer_examen_abre_el_dialogo_con_30_sugerido_y_el_foco_en_examenes(curso_ui):
    visto = _crear_examen(curso_ui)
    assert visto["dialogo"] is True and visto["foco"] is True
    assert visto["valores"] == {"participaciones": "10", "examenes": "30", "tareas": "20", "proyecto": "40"}


def test_guardar_asigna_la_ponderacion_y_cambia_la_final(curso_ui):
    srv, cid = curso_ui.srv, curso_ui.curso.id
    visto = _crear_examen(curso_ui, al_ponderar=_asignar(examenes=30))
    assert visto["dialogo"] is True
    assert _pesos(curso_ui) == Ponderaciones(10, 30, 20, 40)
    assert "Ponderaciones guardadas" in _texto_franja(curso_ui.vista) and "exámenes 30 %" in _texto_franja(curso_ui.vista)
    srv.registrar_calificacion(cid, srv.listar_examenes(cid)[0].id, "100000001", 100)
    assert next(r.final for r in srv.resumen_curso(cid) if r.alumno.num_cuenta == "100000001") == pytest.approx(30)


def test_se_puede_asignar_otro_valor_distinto_del_sugerido(curso_ui):
    _crear_examen(curso_ui, al_ponderar=_asignar(examenes=25, proyecto=35))
    assert _pesos(curso_ui) == Ponderaciones(10, 25, 20, 35)


def test_cancelar_deja_el_examen_creado_y_recuerda_que_no_pesa(curso_ui):
    visto = _crear_examen(curso_ui)  # el diálogo se cancela
    assert visto["dialogo"] is True
    assert [e.nombre for e in curso_ui.srv.listar_examenes(curso_ui.curso.id)] == ["Parcial 1"]
    texto = _texto_franja(curso_ui.vista)
    assert "Parcial 1" in texto and "Los exámenes aún no pesan en la calificación final" in texto
    assert _pesos(curso_ui) == Ponderaciones(10, 0, 20, 40)  # no se guardó nada
    assert curso_ui.srv.ponderacion_examenes_pendiente(curso_ui.curso.id) is True


def test_tras_cancelar_el_siguiente_examen_vuelve_a_pedirla(curso_ui):
    _crear_examen(curso_ui, "Parcial 1")  # se cancela
    assert _crear_examen(curso_ui, "Parcial 2")["dialogo"] is True


def test_tras_guardar_ya_no_se_insiste_con_los_demas_examenes(curso_ui):
    _crear_examen(curso_ui, "Parcial 1", _asignar(examenes=30))
    visto = _crear_examen(curso_ui, "Parcial 2")
    assert visto["dialogo"] is False
    assert "Parcial 2" in _texto_franja(curso_ui.vista) and "creado" in _texto_franja(curso_ui.vista)


def test_guardar_0_explicito_tambien_deja_de_insistir(curso_ui):
    _crear_examen(curso_ui, "Parcial 1", _asignar(examenes=0))
    assert _pesos(curso_ui).examenes == 0
    assert _crear_examen(curso_ui, "Parcial 2")["dialogo"] is False


def test_un_examen_duplicado_no_abre_el_dialogo_de_ponderaciones(curso_ui):
    _crear_examen(curso_ui, "Parcial 1", _asignar(examenes=30))
    errores = []

    def repetir():
        d = buscar_dialogo(curso_ui.app)
        d._nombre.insert(0, "parcial 1")
        d._aceptar()
        errores.append(d._error.cget("text"))
        d.cancelar()

    curso_ui.app.after(300, repetir)
    curso_ui.vista.nuevo_examen()
    assert "Ya existe" in errores[0] and buscar_dialogo(curso_ui.app) is None


# ================= al abrir un curso =================
def test_un_curso_con_examenes_y_sin_ponderacion_asignada_la_recuerda_al_abrirse(curso_ui):
    curso_ui.srv.crear_examen(curso_ui.curso.id, "Parcial 1")  # curso anterior a esta versión
    v = _abrir(curso_ui)
    assert "Los exámenes aún no pesan en la calificación final" in _texto_franja(v)


def test_si_ya_se_asigno_no_se_recuerda(curso_ui):
    curso_ui.srv.crear_examen(curso_ui.curso.id, "Parcial 1")
    curso_ui.srv.establecer_ponderaciones(curso_ui.curso.id, 10, 30, 20, 40)
    assert "aún no pesan" not in _texto_franja(_abrir(curso_ui))


def test_si_se_guardo_0_explicito_no_se_recuerda(curso_ui):
    curso_ui.srv.crear_examen(curso_ui.curso.id, "Parcial 1")
    curso_ui.srv.establecer_ponderaciones(curso_ui.curso.id, 10, 0, 20, 40)
    assert "aún no pesan" not in _texto_franja(_abrir(curso_ui))


def test_sin_examenes_no_hay_recordatorio(curso_ui):
    assert "aún no pesan" not in _texto_franja(_abrir(curso_ui))
