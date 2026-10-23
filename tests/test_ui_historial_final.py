"""Calificación final en el historial del alumno: tarjeta, equivalencia /10 y desglose (datos ficticios)."""

from datetime import date

import pytest

from core.calificacion_final import redondear, sobre_diez
from tests.conftest import hay_pantalla
from tests.test_ui_historial import _filas_examenes, hist, hist_ex  # noqa: F401  (fixtures)

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def _con_todo(ui, examen=70, tareas=90, proyecto=85, pesos=(10, 30, 20, 40)):
    """El alumno del historial tiene 5 décimas (50 puntos); se le agrega lo demás."""
    srv, cid, aid = ui.srv, ui.curso.id, ui.alumno.id
    e = srv.crear_examen(cid, "Parcial 1")
    srv.establecer_calificacion(cid, e.id, aid, examen, date(2026, 10, 8))
    srv.establecer_tareas(cid, aid, tareas, date(2026, 10, 9))
    srv.establecer_proyecto(cid, aid, proyecto, date(2026, 10, 10))
    srv.establecer_ponderaciones(cid, *pesos)
    ui.vista.recargar()


def _valor(ui, clave):
    return ui.vista._valores[clave].cget("text")


def test_hay_una_tarjeta_de_calificacion_final(hist):
    assert "final" in hist.vista._valores and "final10" in hist.vista._valores


def test_la_tarjeta_muestra_la_final_entera_y_la_equivalencia_de_0_a_10(hist):
    _con_todo(hist)  # 5 décimas = 50 pts: 5 + 21 + 18 + 34 = 78
    assert _valor(hist, "final") == "78" and _valor(hist, "final10") == "= 7.8 de 10"


def test_el_desglose_lista_cada_componente_con_su_aporte(hist):
    _con_todo(hist)
    assert hist.vista._desglose.cget("text") == (
        "Participaciones 50 × 10 % = 5  ·  Exámenes 70 × 30 % = 21  ·  Tareas 90 × 20 % = 18  ·  Proyecto final 85 × 40 % = 34"
    )


def test_con_las_ponderaciones_de_omision_los_examenes_no_aportan(hist):
    srv, cid, aid = hist.srv, hist.curso.id, hist.alumno.id
    srv.establecer_tareas(cid, aid, 90, date(2026, 10, 9))
    hist.vista.recargar()
    assert "Exámenes 0 × 0 % = 0" in hist.vista._desglose.cget("text")
    assert _valor(hist, "final") == "23"  # 5 (participaciones) + 18 (tareas)


def test_sin_nada_capturado_las_participaciones_son_lo_unico(hist):
    assert _valor(hist, "final") == "5"  # 50 puntos × 10 %
    assert _valor(hist, "final10") == "= 0.5 de 10"


def test_la_tarjeta_coincide_con_la_tabla_del_curso(hist):
    _con_todo(hist)
    fila = next(r for r in hist.srv.resumen_curso(hist.curso.id) if r.alumno.id == hist.alumno.id)
    assert _valor(hist, "final") == str(redondear(fila.final))
    assert _valor(hist, "final10") == f"= {sobre_diez(fila.final):.1f} de 10"


def test_los_aportes_del_desglose_suman_la_final_exacta(hist):
    _con_todo(hist, examen=66.666)
    d = hist.srv.desglose_final(hist.curso.id, hist.alumno.id)
    assert sum(c.aporte for c in d.componentes) == pytest.approx(d.final)
    assert _valor(hist, "final") == str(redondear(d.final))


def test_cambiar_las_ponderaciones_cambia_la_tarjeta(hist):
    _con_todo(hist)
    hist.srv.establecer_ponderaciones(hist.curso.id, 10, 30, 20, 50)  # 110 %: puntos extra
    hist.vista.recargar()
    assert _valor(hist, "final") == str(redondear(5 + 21 + 18 + 42.5))  # 86.5 → 87


def test_editar_una_calificacion_actualiza_la_final(hist):
    _con_todo(hist)
    hist.srv.establecer_proyecto(hist.curso.id, hist.alumno.id, 100, date(2026, 10, 11))
    hist.vista.recargar()
    assert _valor(hist, "final") == "84"  # 5 + 21 + 18 + 40


def test_el_desglose_no_cambia_las_demas_secciones_del_historial(hist_ex):
    v = hist_ex.vista
    antes = _filas_examenes(v)
    hist_ex.srv.establecer_ponderaciones(hist_ex.curso.id, 10, 30, 20, 40)
    v.recargar()
    assert _filas_examenes(v) == antes
    assert v._valores["total"].cget("text") == "5" and v._valores["registros"].cget("text") == "3"


def test_el_piso_de_0_se_respeta_en_la_participacion(hist):
    # el historial de la fixture ya toca el piso (10, -25, +5 → 5): el total es 5, no -10
    assert hist.vista._desglose.cget("text").startswith("Participaciones 50 × 10 % = 5")
