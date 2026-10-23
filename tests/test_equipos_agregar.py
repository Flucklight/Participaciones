"""Agregar alumnos a un equipo que ya existe (servicio, datos ficticios)."""

import pytest

from core.errores import ErrorDominio
from core.models import EstadoEquipo, TipoInscripcion
from tests.test_equipos import equipo_de, ids


def test_agrega_alumnos_sin_equipo_a_un_equipo_existente(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    r = servicio.agregar_a_equipo(curso_importado.id, 1, [n["100000002"], n["100000003"]])
    assert r.estado == EstadoEquipo.AGREGADO and r.numero == 1
    assert {a.num_cuenta for a in r.miembros} == {"100000002", "100000003"}
    assert [equipo_de(servicio, curso_importado, c) for c in ("100000001", "100000002", "100000003")] == [1, 1, 1]
    assert [e.numero for e in servicio.equipos_del_curso(curso_importado.id)] == [1]  # no se creó otro equipo


def test_agregar_no_gasta_numeros(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    servicio.agregar_a_equipo(curso_importado.id, 1, [n["100000002"]])
    assert servicio.formar_equipo(curso_importado.id, [n["100000003"]]).numero == 2


def test_si_alguien_ya_tiene_equipo_no_se_agrega_a_nadie(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    servicio.formar_equipo(curso_importado.id, [n["100000002"]])
    r = servicio.agregar_a_equipo(curso_importado.id, 1, [n["100000002"], n["100000003"]])
    assert r.estado == EstadoEquipo.YA_TIENEN_EQUIPO
    assert [(a.num_cuenta, num) for a, num in r.con_equipo] == [("100000002", 2)]
    assert equipo_de(servicio, curso_importado, "100000003") is None  # tampoco el que sí podía
    assert equipo_de(servicio, curso_importado, "100000002") == 2  # y el que ya estaba no se movió


def test_equipo_inexistente_o_sin_miembros_se_rechaza(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    with pytest.raises(ErrorDominio, match="no existe o ya no tiene miembros"):
        servicio.agregar_a_equipo(curso_importado.id, 7, [n["100000001"]])
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    servicio.separar_de_equipo(curso_importado.id, [n["100000001"]])  # el equipo 1 queda vacío
    with pytest.raises(ErrorDominio, match="no existe o ya no tiene miembros"):
        servicio.agregar_a_equipo(curso_importado.id, 1, [n["100000002"]])
    assert equipo_de(servicio, curso_importado, "100000002") is None  # el número vacío no se revive


def test_lista_vacia_y_alumnos_invalidos(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    with pytest.raises(ErrorDominio, match="al menos un alumno"):
        servicio.agregar_a_equipo(curso_importado.id, 1, [])
    with pytest.raises(ErrorDominio):
        servicio.agregar_a_equipo(curso_importado.id, 1, [99999])
    otro = servicio.crear_curso("2027-I", "Otra materia", "9999")
    ajeno = servicio.crear_alumno_en_curso(otro.id, "AJENO UNO", TipoInscripcion.OYENTE)
    with pytest.raises(ErrorDominio, match="no está inscrito"):
        servicio.agregar_a_equipo(curso_importado.id, 1, [ajeno.id])


def test_un_alumno_repetido_cuenta_una_vez(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    r = servicio.agregar_a_equipo(curso_importado.id, 1, [n["100000002"], n["100000002"]])
    assert len(r.miembros) == 1


def test_deshacer_un_agregado_es_separar_a_esos_alumnos(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    servicio.agregar_a_equipo(curso_importado.id, 1, [n["100000002"]])
    servicio.separar_de_equipo(curso_importado.id, [n["100000002"]])
    assert equipo_de(servicio, curso_importado, "100000002") is None
    assert equipo_de(servicio, curso_importado, "100000001") == 1


def test_agregar_no_altera_calificaciones(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000002", 77)
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    servicio.agregar_a_equipo(curso_importado.id, 1, [n["100000002"]])
    tareas = {r.alumno.num_cuenta: r.tareas for r in servicio.resumen_curso(curso_importado.id)}
    assert tareas["100000002"] == 77
