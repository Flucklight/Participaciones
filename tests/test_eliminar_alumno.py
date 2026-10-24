"""Eliminar un oyente de un curso (R20): borrado, límites y deshacer (datos ficticios)."""

from datetime import date

import pytest

from core.errores import ErrorDominio
from core.models import TipoInscripcion

HOY = date(2027, 3, 1)


def ids(servicio, curso):
    """{cuenta: alumno_id} de los alumnos del curso que tienen cuenta."""
    return {r.alumno.num_cuenta: r.alumno.id for r in servicio.resumen_curso(curso.id) if r.alumno.num_cuenta}


def oyente_completo(servicio, curso, cuenta=None):
    """Oyente con participaciones, examen, tareas, proyecto y equipo (con otro alumno)."""
    oyente = servicio.crear_alumno_en_curso(curso.id, "Oyente Prueba", TipoInscripcion.OYENTE, cuenta)
    servicio.agregar_participacion(curso.id, oyente.id, 5, date(2027, 2, 1))
    servicio.agregar_participacion(curso.id, oyente.id, -10, date(2027, 2, 2))
    servicio.agregar_participacion(curso.id, oyente.id, 5, date(2027, 2, 3), "al final")
    examen = servicio.crear_examen(curso.id, "Parcial 1")
    servicio.establecer_calificacion(curso.id, examen.id, oyente.id, 8.5, HOY)
    servicio.establecer_tareas(curso.id, oyente.id, 9, HOY)
    servicio.establecer_proyecto(curso.id, oyente.id, 7, HOY)
    regular = ids(servicio, curso)["100000001"]
    equipo = servicio.formar_equipo(curso.id, [oyente.id, regular], "Los Cuatro", "Proyecto X")
    return oyente, examen, equipo.numero


def fila(servicio, curso, alumno_id):
    return next((r for r in servicio.resumen_curso(curso.id) if r.alumno.id == alumno_id), None)


# ---------------- límites ----------------
def test_un_regular_no_se_puede_eliminar(servicio, curso_importado):
    regular = ids(servicio, curso_importado)["100000001"]
    servicio.agregar_participacion(curso_importado.id, regular, 5, HOY)
    with pytest.raises(ErrorDominio, match="solo se pueden eliminar oyentes"):
        servicio.eliminar_alumno_oyente(curso_importado.id, regular)
    with pytest.raises(ErrorDominio):
        servicio.resumen_eliminacion_alumno(curso_importado.id, regular)
    assert fila(servicio, curso_importado, regular).total == 5


def test_alumno_no_inscrito_en_el_curso(servicio, curso_importado):
    otro = servicio.crear_curso("2027-I", "Redes", "3001")
    ajeno = servicio.crear_alumno_en_curso(otro.id, "Ajeno Prueba")
    with pytest.raises(ErrorDominio, match="no está inscrito"):
        servicio.eliminar_alumno_oyente(curso_importado.id, ajeno.id)
    assert fila(servicio, otro, ajeno.id) is not None


def test_curso_inexistente(servicio):
    with pytest.raises(ErrorDominio, match="curso no existe"):
        servicio.eliminar_alumno_oyente(999, 1)


# ---------------- resumen para confirmar ----------------
def test_el_resumen_cuenta_lo_que_se_pierde(servicio, curso_importado):
    oyente, _, numero = oyente_completo(servicio, curso_importado, "100000099")
    r = servicio.resumen_eliminacion_alumno(curso_importado.id, oyente.id)
    assert (r.participaciones, r.calificaciones_examen, r.tareas, r.proyecto) == (3, 1, True, True)
    assert r.equipo == numero
    assert r.alumno_borrado is True
    assert r.alumno.nombre_completo == "OYENTE PRUEBA"


def test_el_resumen_de_un_oyente_sin_datos(servicio, curso):
    oyente = servicio.crear_alumno_en_curso(curso.id, "Oyente Vacio")
    r = servicio.resumen_eliminacion_alumno(curso.id, oyente.id)
    assert (r.participaciones, r.calificaciones_examen, r.tareas, r.proyecto, r.equipo) == (0, 0, False, False, None)


# ---------------- eliminar ----------------
def test_elimina_todo_lo_del_oyente_en_ese_curso(servicio, curso_importado):
    oyente, examen, _ = oyente_completo(servicio, curso_importado)
    servicio.eliminar_alumno_oyente(curso_importado.id, oyente.id)
    assert fila(servicio, curso_importado, oyente.id) is None
    assert servicio.contar_alumnos(curso_importado.id) == 4
    assert servicio.calificacion_de(examen.id, oyente.id) is None
    assert servicio.tareas_de(curso_importado.id, oyente.id) is None
    assert servicio.proyecto_de(curso_importado.id, oyente.id) is None
    assert servicio.equipo_de(curso_importado.id, oyente.id) is None
    assert servicio.historial(curso_importado.id, oyente.id) == []


def test_si_no_esta_en_otro_curso_se_borra_tambien_la_persona(servicio, curso_importado):
    oyente, _, _ = oyente_completo(servicio, curso_importado, "100000099")
    servicio.eliminar_alumno_oyente(curso_importado.id, oyente.id)
    with pytest.raises(ErrorDominio):
        servicio.obtener_alumno(oyente.id)


def test_si_esta_en_otro_curso_se_conserva_la_persona_y_sus_datos_de_alla(servicio, curso_importado):
    otro = servicio.crear_curso("2027-I", "Redes", "3001")
    oyente, _, _ = oyente_completo(servicio, curso_importado, "100000099")
    servicio.inscribir_alumno_existente(otro.id, oyente.id, TipoInscripcion.OYENTE)
    servicio.agregar_participacion(otro.id, oyente.id, 7, HOY)
    servicio.establecer_tareas(otro.id, oyente.id, 6, HOY)
    assert servicio.resumen_eliminacion_alumno(curso_importado.id, oyente.id).alumno_borrado is False

    servicio.eliminar_alumno_oyente(curso_importado.id, oyente.id)

    assert servicio.obtener_alumno(oyente.id).num_cuenta == "100000099"
    allá = fila(servicio, otro, oyente.id)
    assert allá.total == 7
    assert servicio.tareas_de(otro.id, oyente.id).puntos == 6
    assert fila(servicio, curso_importado, oyente.id) is None


def test_el_equipo_sobrevive_vacio_y_su_numero_no_se_reutiliza(servicio, curso_importado):
    oyente = servicio.crear_alumno_en_curso(curso_importado.id, "Oyente Solo")
    equipo = servicio.formar_equipo(curso_importado.id, [oyente.id])
    servicio.eliminar_alumno_oyente(curso_importado.id, oyente.id)
    assert servicio.equipos_del_curso(curso_importado.id) == []
    regular = ids(servicio, curso_importado)["100000001"]
    nuevo = servicio.formar_equipo(curso_importado.id, [regular])
    assert nuevo.numero == equipo.numero + 1


def test_no_cambia_nada_de_los_demas_alumnos(servicio, curso_importado):
    regular = ids(servicio, curso_importado)["100000001"]
    servicio.agregar_participacion(curso_importado.id, regular, 8, HOY)
    servicio.establecer_tareas(curso_importado.id, regular, 9, HOY)
    antes = fila(servicio, curso_importado, regular)
    oyente, _, _ = oyente_completo(servicio, curso_importado)
    servicio.eliminar_alumno_oyente(curso_importado.id, oyente.id)
    despues = fila(servicio, curso_importado, regular)
    assert (despues.total, despues.tareas, despues.final) == (antes.total, antes.tareas, antes.final)
    # el regular sigue en el equipo que compartía con el oyente, ahora solo con él
    assert [m.id for m in servicio.equipos_del_curso(curso_importado.id)[0].miembros] == [regular]


def test_la_exportacion_de_la_base_sigue_funcionando(servicio, curso_importado, tmp_path):
    oyente, _, _ = oyente_completo(servicio, curso_importado, "100000099")
    servicio.eliminar_alumno_oyente(curso_importado.id, oyente.id)
    destino = servicio.exportar_base(tmp_path / "base.db")
    assert servicio.resumen_base_archivo(destino).alumnos == servicio.resumen_base_local().alumnos


# ---------------- deshacer ----------------
def test_deshacer_devuelve_todo_y_el_total_es_igual(servicio, curso_importado):
    oyente, examen, numero = oyente_completo(servicio, curso_importado, "100000099")
    antes = fila(servicio, curso_importado, oyente.id)
    assert antes.total == 5  # +5, -10, +5 con piso en 0
    eliminado = servicio.eliminar_alumno_oyente(curso_importado.id, oyente.id)

    restaurado = servicio.deshacer_eliminacion_alumno(eliminado)

    despues = fila(servicio, curso_importado, restaurado.id)
    assert (despues.alumno.nombre_completo, despues.alumno.num_cuenta) == ("OYENTE PRUEBA", "100000099")
    assert despues.tipo == TipoInscripcion.OYENTE
    assert (despues.total, despues.tareas, despues.proyecto, despues.final) == (
        antes.total, antes.tareas, antes.proyecto, antes.final
    )
    assert despues.equipo == numero
    assert servicio.calificacion_de(examen.id, restaurado.id).puntos == 8.5
    notas = [(p.decimas, p.fecha, p.nota) for p in servicio.historial(curso_importado.id, restaurado.id)]
    assert sorted(notas, key=lambda n: n[1]) == [
        (5, date(2027, 2, 1), ""), (-10, date(2027, 2, 2), ""), (5, date(2027, 2, 3), "al final")
    ]


def test_deshacer_conserva_a_la_persona_si_estaba_en_otro_curso(servicio, curso_importado):
    otro = servicio.crear_curso("2027-I", "Redes", "3001")
    oyente, _, _ = oyente_completo(servicio, curso_importado)
    servicio.inscribir_alumno_existente(otro.id, oyente.id, TipoInscripcion.OYENTE)
    eliminado = servicio.eliminar_alumno_oyente(curso_importado.id, oyente.id)
    assert servicio.deshacer_eliminacion_alumno(eliminado).id == oyente.id
    assert fila(servicio, curso_importado, oyente.id).total == 5


def test_deshacer_con_la_cuenta_ocupada_no_restaura_nada(servicio, curso_importado):
    oyente, examen, _ = oyente_completo(servicio, curso_importado, "100000099")
    eliminado = servicio.eliminar_alumno_oyente(curso_importado.id, oyente.id)
    servicio.crear_alumno_en_curso(curso_importado.id, "Otra Persona", TipoInscripcion.OYENTE, "100000099")
    cursos_antes = servicio.contar_alumnos(curso_importado.id)
    with pytest.raises(ErrorDominio, match="ya pertenece"):
        servicio.deshacer_eliminacion_alumno(eliminado)
    assert servicio.contar_alumnos(curso_importado.id) == cursos_antes


def test_deshacer_con_el_alumno_ya_reinscrito_no_duplica(servicio, curso_importado):
    otro = servicio.crear_curso("2027-I", "Redes", "3001")
    oyente, _, _ = oyente_completo(servicio, curso_importado)
    servicio.inscribir_alumno_existente(otro.id, oyente.id, TipoInscripcion.OYENTE)
    eliminado = servicio.eliminar_alumno_oyente(curso_importado.id, oyente.id)
    servicio.inscribir_alumno_existente(curso_importado.id, oyente.id, TipoInscripcion.OYENTE)
    with pytest.raises(ErrorDominio, match="ya está en este curso"):
        servicio.deshacer_eliminacion_alumno(eliminado)
    assert servicio.historial(curso_importado.id, oyente.id) == []


def test_deshacer_si_el_curso_ya_no_existe(servicio):
    curso = servicio.crear_curso("2027-I", "Redes", "3001")
    oyente = servicio.crear_alumno_en_curso(curso.id, "Oyente Solo")
    eliminado = servicio.eliminar_alumno_oyente(curso.id, oyente.id)
    servicio.eliminar_curso(curso.id)
    with pytest.raises(ErrorDominio, match="curso no existe"):
        servicio.deshacer_eliminacion_alumno(eliminado)


def test_reimportar_la_lista_tras_eliminar_a_un_oyente_no_lo_trae_de_vuelta(servicio, lista, curso_importado):
    oyente, _, _ = oyente_completo(servicio, curso_importado)
    servicio.eliminar_alumno_oyente(curso_importado.id, oyente.id)
    servicio.importar_lista(lista)
    assert servicio.contar_alumnos(curso_importado.id) == 4
