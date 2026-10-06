from datetime import date

import pytest

from core.puntaje import total_con_piso


@pytest.mark.parametrize(
    "decimas, esperado",
    [
        ([], 0),
        ([10, 5], 15),
        ([5, -10], 0),             # no baja de 0
        ([5, -10, 5], 5),          # el piso se aplica paso a paso, no al final
        ([-5, 10], 10),            # restar con total 0 no deja "deuda"
        ([10, -4], 6),
        ([0.1, 0.2], 0.3),
    ],
)
def test_total_con_piso(decimas, esperado):
    assert total_con_piso(decimas) == pytest.approx(esperado)


def test_negativas_mayores_al_total_dejan_el_total_en_cero(servicio, curso_importado):
    cid = curso_importado.id
    servicio.registrar(cid, "100000001", 5)
    r = servicio.registrar(cid, "100000001", -10)
    assert r.total == 0
    assert r.decimas == -10 and r.decimas_aplicadas == -5  # pidió -10, se aplicó -5
    fila = next(f for f in servicio.resumen_curso(cid) if f.alumno.num_cuenta == "100000001")
    assert fila.total == 0


def test_restar_con_total_cero_no_cambia_nada(servicio, curso_importado):
    r = servicio.registrar(curso_importado.id, "100000001", -3)
    assert r.total == 0 and r.decimas_aplicadas == 0


def test_despues_de_tocar_el_piso_se_sigue_sumando_desde_cero(servicio, curso_importado):
    cid = curso_importado.id
    servicio.registrar(cid, "100000001", 5)
    servicio.registrar(cid, "100000001", -10)
    r = servicio.registrar(cid, "100000001", 3)
    assert r.total == 3 and r.decimas_aplicadas == 3


def test_deshacer_la_resta_recalcula_el_total(servicio, curso_importado):
    cid = curso_importado.id
    servicio.registrar(cid, "100000001", 5)
    resta = servicio.registrar(cid, "100000001", -10)
    servicio.registrar(cid, "100000001", 3)
    servicio.deshacer(resta.participacion.id)
    assert servicio.total_alumno(cid, resta.alumno.id) == 8


def test_editar_participacion_recalcula_con_el_piso(servicio, curso_importado):
    cid = curso_importado.id
    servicio.registrar(cid, "100000001", 10)
    resta = servicio.registrar(cid, "100000001", -4)
    assert resta.total == 6
    servicio.editar_participacion(resta.participacion.id, -50, date.today())
    assert servicio.total_alumno(cid, resta.alumno.id) == 0


def test_el_orden_cronologico_manda_no_el_de_captura(servicio, curso_importado):
    cid = curso_importado.id
    r = servicio.registrar(cid, "100000001", 10)
    # Resta capturada después pero con fecha anterior: ocurrió primero y se queda en 0.
    servicio.agregar_participacion(cid, r.alumno.id, -10, date(2020, 1, 1))
    assert servicio.total_alumno(cid, r.alumno.id) == 10


def test_el_resumen_nunca_muestra_totales_negativos(servicio, curso_importado):
    cid = curso_importado.id
    servicio.registrar(cid, "100000001", -20)
    servicio.registrar(cid, "100000002", 5)
    servicio.registrar(cid, "100000002", -99)
    assert all(f.total >= 0 for f in servicio.resumen_curso(cid))
