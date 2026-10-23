"""Calificación final: función pura (datos ficticios)."""

import pytest

from core.calificacion_final import (
    POR_OMISION,
    Ponderaciones,
    calificacion_final,
    desglose_final,
    redondear,
    sobre_diez,
)

PESOS = Ponderaciones(10, 30, 20, 40)


def test_por_omision_los_examenes_pesan_0():
    assert (POR_OMISION.participaciones, POR_OMISION.examenes, POR_OMISION.tareas, POR_OMISION.proyecto) == (10, 0, 20, 40)
    assert POR_OMISION.suma == 70


def test_ejemplo_base_da_81():
    # 8 décimas = 80 puntos; 80×10 % + 70×30 % + 90×20 % + 85×40 % = 8 + 21 + 18 + 34
    assert calificacion_final(8, 70, 90, 85, PESOS) == pytest.approx(81)


def test_cada_decima_vale_10_puntos():
    solo_participaciones = Ponderaciones(100, 0, 0, 0)
    assert calificacion_final(1, None, 0, 0, solo_participaciones) == pytest.approx(10)
    assert calificacion_final(10, None, 0, 0, solo_participaciones) == pytest.approx(100)  # 10 décimas = 100 = calificación 10


def test_las_participaciones_no_tienen_tope():
    assert calificacion_final(12, None, 0, 0, PESOS) == pytest.approx(12)  # 120 puntos × 10 %


def test_sin_examenes_ese_componente_aporta_0_y_no_se_redistribuye():
    con = calificacion_final(0, 0.0, 100, 100, PESOS)
    sin = calificacion_final(0, None, 100, 100, PESOS)
    assert con == sin == pytest.approx(60)  # 20 + 40: el 30 % de exámenes no pasa a los demás


def test_todo_en_cero_da_cero():
    assert calificacion_final(0, None, 0, 0, PESOS) == 0
    assert calificacion_final(0, 0, 0, 0, POR_OMISION) == 0


def test_ponderaciones_que_suman_mas_de_100_pasan_de_100():
    pesos = Ponderaciones(10, 30, 20, 50)  # 110 %
    assert pesos.suma == 110
    assert calificacion_final(10, 100, 100, 100, pesos) == pytest.approx(110)


def test_ponderaciones_que_suman_menos_de_100_tambien_valen():
    assert calificacion_final(10, 100, 100, 100, POR_OMISION) == pytest.approx(70)  # 10 + 0 + 20 + 40


def test_una_ponderacion_en_0_anula_su_componente():
    pesos = Ponderaciones(0, 30, 20, 40)
    assert calificacion_final(99, 70, 90, 85, pesos) == pytest.approx(21 + 18 + 34)


def test_por_omision_es_la_ponderacion_de_los_cursos_nuevos():
    # sin exámenes asignados: 10 % de 80 + 20 % de 90 + 40 % de 85
    assert calificacion_final(8, 70, 90, 85) == pytest.approx(8 + 18 + 34)


def test_el_desglose_suma_la_final_exacta():
    d = desglose_final(8, 70, 90, 85, PESOS)
    assert [c.clave for c in d.componentes] == ["participaciones", "examenes", "tareas", "proyecto"]
    assert [c.valor for c in d.componentes] == [80, 70, 90, 85]
    assert [c.aporte for c in d.componentes] == pytest.approx([8, 21, 18, 34])
    assert d.final == pytest.approx(calificacion_final(8, 70, 90, 85, PESOS)) == pytest.approx(81)


def test_el_desglose_sin_examenes_muestra_0_en_ese_componente():
    d = desglose_final(8, None, 90, 85, PESOS)
    assert d.componentes[1].valor == 0 and d.componentes[1].aporte == 0


def test_con_decimales_se_conserva_el_valor_exacto():
    assert calificacion_final(0, 66.666, 0, 0, Ponderaciones(0, 100, 0, 0)) == pytest.approx(66.666)


# ---------------- redondeo ----------------
@pytest.mark.parametrize("valor, esperado", [
    (87.5, 88), (87.49, 87), (87.51, 88), (2.5, 3), (0.5, 1), (0.49, 0), (1.5, 2), (0, 0), (100, 100),
    (110.5, 111), (-0.5, -1),
])
def test_redondeo_a_entero_mitad_hacia_arriba(valor, esperado):
    assert redondear(valor) == esperado  # round() daría 2.5 → 2 y 0.5 → 0


def test_el_error_binario_no_cambia_el_redondeo():
    assert redondear(0.1 + 0.2 + 87.2) == 88  # suma 87.5 con error binario: sigue siendo la mitad
    assert redondear(87.49999999999999) == 88  # es 87.5 con error binario
    assert redondear(1.005 * 100) == 101  # 100.49999999999999 es 100.5


@pytest.mark.parametrize("valor, esperado", [
    (81, 8.1), (87.49, 8.7), (87.5, 8.8), (100, 10.0), (0, 0.0), (110, 11.0), (4.95, 0.5), (4.94, 0.5), (4.5, 0.5),
])
def test_equivalencia_de_0_a_10_con_un_decimal(valor, esperado):
    assert sobre_diez(valor) == esperado


def test_la_equivalencia_sale_del_valor_exacto_no_del_entero_mostrado():
    # 84.46 se muestra como 84 de 100, pero su equivalencia exacta es 8.446 → 8.4; 84.54 se muestra 85 → 8.5
    assert redondear(84.46) == 84 and sobre_diez(84.46) == 8.4
    assert redondear(84.54) == 85 and sobre_diez(84.54) == 8.5
    assert redondear(84.5) == 85 and sobre_diez(84.5) == 8.5  # 8.45 → 8.5 (mitad hacia arriba)
