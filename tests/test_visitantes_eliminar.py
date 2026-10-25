"""Visitantes (R21): quitar la visita y eliminar el curso de origen (datos ficticios)."""

from datetime import date
from types import SimpleNamespace

import pytest

from core.errores import ErrorDominio
from core.models import TipoInscripcion

REGULAR, OYENTE, VISITANTE = TipoInscripcion.REGULAR, TipoInscripcion.OYENTE, TipoInscripcion.VISITANTE
HOY = date(2027, 3, 1)


@pytest.fixture
def g(servicio):
    """Ana (regular en 3001, visitante en 3002) con datos en su origen y un equipo en 3002."""
    a = servicio.crear_curso("2027-I", "Redes", "3001")
    b = servicio.crear_curso("2027-I", "Redes", "3002")
    ana = servicio.crear_alumno_en_curso(a.id, "Prueba Ana", REGULAR, "100000001")
    luis = servicio.crear_alumno_en_curso(b.id, "Prueba Luis", REGULAR, "100000002")
    servicio.inscribir_visitante(b.id, ana.id, a.id)
    servicio.registrar_para_alumno(b.id, ana.id, 5, HOY)
    servicio.establecer_tareas(b.id, ana.id, 90, HOY)
    servicio.formar_equipo(b.id, [ana.id, luis.id])
    return SimpleNamespace(a=a, b=b, ana=ana, luis=luis, srv=servicio, repo=servicio._repo)


def fila(g, curso, alumno):
    return next((f for f in g.srv.resumen_curso(curso.id) if f.alumno.id == alumno.id), None)


# ---------------- quitar la visita ----------------
def test_el_resumen_de_un_visitante_dice_que_solo_se_quita_la_visita(g):
    r = g.srv.resumen_eliminacion_alumno(g.b.id, g.ana.id)
    assert r.es_visitante and r.grupo_origen == "3001"
    assert (r.participaciones, r.calificaciones_examen, r.tareas, r.proyecto) == (0, 0, False, False)
    assert r.equipo == 1 and r.alumno_borrado is False


def test_quitar_la_visita_no_toca_nada_del_origen(g):
    antes = fila(g, g.a, g.ana)
    g.srv.eliminar_alumno_oyente(g.b.id, g.ana.id)
    assert fila(g, g.b, g.ana) is None
    despues = fila(g, g.a, g.ana)
    assert (despues.total, despues.tareas, despues.final, despues.tipo) == (antes.total, antes.tareas, antes.final, REGULAR)
    assert g.srv.obtener_alumno(g.ana.id).num_cuenta == "100000001"
    assert g.srv.tipo_inscripcion(g.a.id, g.ana.id) == REGULAR


def test_el_equipo_del_grupo_que_visitaba_sobrevive_y_su_numero_no_se_reutiliza(g):
    g.srv.eliminar_alumno_oyente(g.b.id, g.ana.id)
    assert [m.id for m in g.srv.equipos_del_curso(g.b.id)[0].miembros] == [g.luis.id]
    assert g.srv.formar_equipo(g.a.id, [g.ana.id]).estado.value == "formado"  # quedó libre para el origen


def test_deshacer_restaura_la_visita_y_su_equipo(g):
    antes = fila(g, g.b, g.ana)
    eliminado = g.srv.eliminar_alumno_oyente(g.b.id, g.ana.id)
    g.srv.deshacer_eliminacion_alumno(eliminado)
    despues = fila(g, g.b, g.ana)
    assert despues.tipo == VISITANTE and despues.curso_origen_id == g.a.id and despues.equipo == 1
    assert (despues.total, despues.tareas, despues.final) == (antes.total, antes.tareas, antes.final)
    g.srv.registrar_para_alumno(g.b.id, g.ana.id, 1, HOY)  # sigue redirigiendo al origen
    assert g.srv.total_alumno(g.a.id, g.ana.id) == 6


def test_deshacer_falla_sin_restaurar_nada_si_el_origen_ya_no_existe(g):
    eliminado = g.srv.eliminar_alumno_oyente(g.b.id, g.ana.id)
    g.srv.eliminar_curso(g.a.id)
    with pytest.raises(ErrorDominio, match="origen ya no existe"):
        g.srv.deshacer_eliminacion_alumno(eliminado)
    assert fila(g, g.b, g.ana) is None


def test_deshacer_falla_si_ya_no_es_regular_en_el_origen(g):
    eliminado = g.srv.eliminar_alumno_oyente(g.b.id, g.ana.id)
    g.srv.cambiar_tipo(g.a.id, g.ana.id, OYENTE)
    with pytest.raises(ErrorDominio, match="ya no es alumno regular"):
        g.srv.deshacer_eliminacion_alumno(eliminado)
    assert fila(g, g.b, g.ana) is None


def test_deshacer_falla_si_mientras_tanto_formo_equipo_en_el_origen(g):
    eliminado = g.srv.eliminar_alumno_oyente(g.b.id, g.ana.id)
    g.srv.formar_equipo(g.a.id, [g.ana.id])
    with pytest.raises(ErrorDominio, match="ya está en un equipo del grupo 3001"):
        g.srv.deshacer_eliminacion_alumno(eliminado)
    assert fila(g, g.b, g.ana) is None


def test_un_regular_sigue_sin_poder_eliminarse(g):
    with pytest.raises(ErrorDominio, match="solo se pueden eliminar oyentes"):
        g.srv.eliminar_alumno_oyente(g.b.id, g.luis.id)
    with pytest.raises(ErrorDominio, match="solo se pueden eliminar oyentes"):
        g.srv.eliminar_alumno_oyente(g.a.id, g.ana.id)


def test_quitar_la_visita_de_un_visitante_sin_equipo(g):
    g.srv.separar_de_equipo(g.b.id, [g.ana.id])
    r = g.srv.resumen_eliminacion_alumno(g.b.id, g.ana.id)
    assert r.equipo is None
    g.srv.eliminar_alumno_oyente(g.b.id, g.ana.id)
    assert fila(g, g.b, g.ana) is None


# ---------------- eliminar el curso de origen ----------------
def test_el_resumen_cuenta_los_visitantes_que_dejan_de_aparecer(g):
    assert g.srv.resumen_eliminacion_visitantes(g.a.id) == 1
    assert g.srv.resumen_eliminacion_visitantes(g.b.id) == 0


def test_eliminar_el_origen_borra_las_visitas_y_su_pertenencia_a_equipo(g):
    g.srv.eliminar_curso(g.a.id)
    assert [f.alumno.id for f in g.srv.resumen_curso(g.b.id)] == [g.luis.id]
    assert g.repo.equipo_de(g.b.id, g.ana.id) is None
    assert [m.id for m in g.srv.equipos_del_curso(g.b.id)[0].miembros] == [g.luis.id]
    con = g.repo.transaccion()
    assert con.execute("SELECT COUNT(*) FROM miembro_equipo WHERE alumno_id = ?", (g.ana.id,)).fetchone()[0] == 0


def test_el_equipo_queda_vacio_pero_su_numero_no_se_reutiliza(g):
    g.srv.separar_de_equipo(g.b.id, [g.luis.id])  # el equipo 1 solo tenía a Ana además de Luis
    g.srv.eliminar_curso(g.a.id)
    assert g.srv.equipos_del_curso(g.b.id) == []          # un equipo vacío no aparece
    assert g.repo.siguiente_numero_equipo(g.b.id) == 2    # pero su número sigue gastado


def test_archivar_el_origen_no_cambia_nada(g):
    g.srv.archivar_curso(g.a.id)
    assert fila(g, g.b, g.ana).tipo == VISITANTE and g.srv.resumen_eliminacion_visitantes(g.a.id) == 1


def test_eliminar_el_grupo_que_visita_no_toca_el_origen(g):
    g.srv.eliminar_curso(g.b.id)
    f = fila(g, g.a, g.ana)
    assert f.total == 5 and f.tareas == 90 and f.tipo == REGULAR


def test_no_se_puede_cambiar_de_tipo_a_quien_tiene_visitas_en_otros_grupos(g):
    with pytest.raises(ErrorDominio, match="quita sus visitas"):
        g.srv.cambiar_tipo(g.a.id, g.ana.id, OYENTE)
    g.srv.cambiar_tipo(g.a.id, g.ana.id, REGULAR)  # sin cambio real: permitido
    g.srv.eliminar_alumno_oyente(g.b.id, g.ana.id)
    g.srv.cambiar_tipo(g.a.id, g.ana.id, OYENTE)    # sin visitas ya se puede
    assert g.srv.tipo_inscripcion(g.a.id, g.ana.id) == OYENTE
