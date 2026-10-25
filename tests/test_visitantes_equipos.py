"""Visitantes (R21): un solo equipo entre el grupo de origen y los que visita (datos ficticios)."""

from datetime import date
from types import SimpleNamespace

import pytest

from core.models import EstadoEquipo, TipoInscripcion

REGULAR = TipoInscripcion.REGULAR
HOY = date(2027, 3, 1)


@pytest.fixture
def g(servicio):
    """3001 (origen), 3002 y 3003 (visitas). Ana: regular en 3001 y visitante en 3002 y 3003."""
    a = servicio.crear_curso("2027-I", "Redes", "3001")
    b = servicio.crear_curso("2027-I", "Redes", "3002")
    c = servicio.crear_curso("2027-I", "Redes", "3003")
    ana = servicio.crear_alumno_en_curso(a.id, "Prueba Ana", REGULAR, "100000001")
    beto = servicio.crear_alumno_en_curso(a.id, "Prueba Beto", REGULAR, "100000003")
    luis = servicio.crear_alumno_en_curso(b.id, "Prueba Luis", REGULAR, "100000002")
    servicio.inscribir_visitante(b.id, ana.id, a.id)
    servicio.inscribir_visitante(c.id, ana.id, a.id)
    return SimpleNamespace(a=a, b=b, c=c, ana=ana, beto=beto, luis=luis, srv=servicio)


def test_con_equipo_en_la_visita_no_puede_formar_otro_en_el_origen(g):
    assert g.srv.formar_equipo(g.b.id, [g.ana.id, g.luis.id]).estado == EstadoEquipo.FORMADO
    r = g.srv.formar_equipo(g.a.id, [g.ana.id, g.beto.id])
    assert r.estado == EstadoEquipo.YA_TIENEN_EQUIPO
    assert [(a.id, n) for a, n in r.con_equipo] == [(g.ana.id, 1)]
    assert r.grupo_de == {g.ana.id: "3002"}
    assert g.srv.equipos_del_curso(g.a.id) == []  # no se creó ni se movió nada
    assert g.srv.equipo_de(g.a.id, g.beto.id) is None


def test_con_equipo_en_el_origen_no_puede_formar_otro_en_la_visita(g):
    g.srv.formar_equipo(g.a.id, [g.ana.id])
    r = g.srv.formar_equipo(g.b.id, [g.ana.id, g.luis.id])
    assert r.estado == EstadoEquipo.YA_TIENEN_EQUIPO and r.grupo_de == {g.ana.id: "3001"}
    assert g.srv.equipos_del_curso(g.b.id) == []
    assert g.srv.equipo_de(g.b.id, g.luis.id) is None


def test_tampoco_en_otra_visita(g):
    g.srv.formar_equipo(g.b.id, [g.ana.id])
    r = g.srv.formar_equipo(g.c.id, [g.ana.id])
    assert r.estado == EstadoEquipo.YA_TIENEN_EQUIPO and r.grupo_de == {g.ana.id: "3002"}


def test_agregar_a_un_equipo_tambien_se_rechaza(g):
    g.srv.formar_equipo(g.a.id, [g.beto.id])
    g.srv.formar_equipo(g.b.id, [g.ana.id])
    r = g.srv.agregar_a_equipo(g.a.id, 1, [g.ana.id])
    assert r.estado == EstadoEquipo.YA_TIENEN_EQUIPO and r.grupo_de == {g.ana.id: "3002"}
    assert [a.id for a in g.srv.equipos_del_curso(g.a.id)[0].miembros] == [g.beto.id]


def test_el_mensaje_dice_quien_en_que_equipo_y_en_que_grupo(g):
    g.srv.formar_equipo(g.b.id, [g.ana.id])
    g.srv.formar_equipo(g.b.id, [g.luis.id])
    r = g.srv.formar_equipo(g.a.id, [g.ana.id])
    (alumno, numero), = r.con_equipo
    assert (alumno.nombre_completo, numero, r.grupo_de[alumno.id]) == ("PRUEBA ANA", 1, "3002")


def test_sacarlo_de_uno_lo_libera_para_el_otro(g):
    g.srv.formar_equipo(g.b.id, [g.ana.id])
    g.srv.separar_de_equipo(g.b.id, [g.ana.id])
    assert g.srv.formar_equipo(g.a.id, [g.ana.id]).estado == EstadoEquipo.FORMADO


def test_deshacer_la_separacion_no_la_devuelve_si_ya_esta_en_el_otro_grupo(g):
    g.srv.formar_equipo(g.b.id, [g.ana.id, g.luis.id])
    separados = g.srv.separar_de_equipo(g.b.id, [g.ana.id])
    g.srv.formar_equipo(g.a.id, [g.ana.id])
    g.srv.deshacer_separacion(g.b.id, separados)
    assert g.srv.equipo_de(g.b.id, g.ana.id) is None
    assert g.srv.equipo_de(g.a.id, g.ana.id) == 1


def test_deshacer_la_separacion_la_devuelve_si_sigue_libre(g):
    g.srv.formar_equipo(g.b.id, [g.ana.id, g.luis.id])
    separados = g.srv.separar_de_equipo(g.b.id, [g.ana.id])
    g.srv.deshacer_separacion(g.b.id, separados)
    assert g.srv.equipo_de(g.b.id, g.ana.id) == 1


def test_deshacer_formar_el_equipo_libera_a_todos(g):
    r = g.srv.formar_equipo(g.b.id, [g.ana.id, g.luis.id])
    g.srv.deshacer_equipo(g.b.id, r.numero)
    assert g.srv.formar_equipo(g.a.id, [g.ana.id]).estado == EstadoEquipo.FORMADO


def test_quien_no_tiene_visitas_no_se_ve_afectado(g):
    g.srv.formar_equipo(g.b.id, [g.ana.id])
    r = g.srv.formar_equipo(g.a.id, [g.beto.id])  # Beto solo está en el 3001
    assert r.estado == EstadoEquipo.FORMADO and r.grupo_de == {}
    assert g.srv.formar_equipo(g.b.id, [g.luis.id]).estado == EstadoEquipo.FORMADO


def test_una_regular_de_otra_materia_no_se_confunde(g):
    otra = g.srv.crear_curso("2027-I", "Bases", "3001")
    ana2 = g.srv.crear_alumno_en_curso(otra.id, "Prueba Ana", REGULAR, "100000001")  # misma persona (cuenta)
    assert ana2.id == g.ana.id
    g.srv.formar_equipo(g.b.id, [g.ana.id])
    assert g.srv.formar_equipo(otra.id, [g.ana.id]).estado == EstadoEquipo.FORMADO  # otra materia: sin relación


def test_la_nota_del_equipo_del_grupo_que_visita_queda_en_el_origen_y_deshacer_restaura(g):
    g.srv.formar_equipo(g.b.id, [g.ana.id, g.luis.id])
    g.srv.registrar_proyecto_para_alumno(g.a.id, g.ana.id, 50, HOY)
    r = g.srv.registrar_proyecto_equipo(g.b.id, 1, 90, HOY, reemplazar=True)
    assert g.srv._repo.obtener_proyecto(g.a.id, g.ana.id).puntos == 90
    assert g.srv._repo.obtener_proyecto(g.b.id, g.luis.id).puntos == 90
    g.srv.deshacer_proyecto(g.b.id, r.anteriores)
    assert g.srv._repo.obtener_proyecto(g.a.id, g.ana.id).puntos == 50
    assert g.srv._repo.obtener_proyecto(g.b.id, g.luis.id) is None
