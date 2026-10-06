from datetime import date

import pytest

from core.errores import ErrorDominio
from core.models import TipoInscripcion


def test_historial_detallado_calcula_efecto_real_y_acumulado(servicio, curso_importado):
    cid = curso_importado.id
    r = servicio.registrar(cid, "100000001", 10)
    aid = r.alumno.id
    servicio.agregar_participacion(cid, aid, -25, date.today())  # toca el piso
    servicio.agregar_participacion(cid, aid, 5, date.today())

    lineas = servicio.historial_detallado(cid, aid)  # más reciente primero
    assert [l.participacion.decimas for l in lineas] == [5, -25, 10]
    assert [l.acumulado for l in lineas] == [5, 0, 10]
    assert [l.aplicado for l in lineas] == [5, -10, 10]
    assert [l.toco_el_piso for l in lineas] == [False, True, False]
    assert lineas[0].acumulado == servicio.total_alumno(cid, aid)


def test_historial_detallado_respeta_el_orden_cronologico_no_el_de_captura(servicio, curso_importado):
    cid = curso_importado.id
    r = servicio.registrar(cid, "100000001", 10)  # hoy
    servicio.agregar_participacion(cid, r.alumno.id, -10, date(2020, 1, 1))  # ocurrió antes
    lineas = servicio.historial_detallado(cid, r.alumno.id)
    assert [l.participacion.decimas for l in lineas] == [10, -10]
    assert [l.acumulado for l in lineas] == [10, 0]
    assert lineas[1].toco_el_piso  # la resta de 2020 se aplicó con total 0


def test_historial_vacio(servicio, curso_importado):
    aid = servicio.registrar(curso_importado.id, "100000001", 1).alumno.id
    servicio.deshacer(servicio.historial(curso_importado.id, aid)[0].id)
    assert servicio.historial_detallado(curso_importado.id, aid) == []


def test_tipo_inscripcion(servicio, curso):
    oyente = servicio.crear_alumno_en_curso(curso.id, "Oyente")
    assert servicio.tipo_inscripcion(curso.id, oyente.id) == TipoInscripcion.OYENTE
    otro = servicio.crear_curso("2027-II", "Otra", "2")
    with pytest.raises(ErrorDominio):
        servicio.tipo_inscripcion(otro.id, oyente.id)
