"""Calificación del proyecto final: esquema, un alumno y un equipo (datos ficticios)."""

import sqlite3
from datetime import date

import pytest

from core.database import conectar
from core.errores import ErrorDominio
from core.models import EstadoRegistro, TipoInscripcion
from tests.test_equipos import ids


def nota(servicio, curso, cuenta):
    alumno = next(r.alumno for r in servicio.resumen_curso(curso.id) if r.alumno.num_cuenta == cuenta)
    return servicio.proyecto_de(curso.id, alumno.id)


def notas(servicio, curso):
    """{cuenta: proyecto} de todos los alumnos (0 si no hay captura)."""
    return {r.alumno.num_cuenta: r.proyecto for r in servicio.resumen_curso(curso.id)}


def equipo(servicio, curso, *cuentas):
    n = ids(servicio, curso)
    return servicio.formar_equipo(curso.id, [n[c] for c in cuentas]).numero


# ---------------- esquema ----------------
def test_la_tabla_se_crea_en_una_base_nueva():
    con = conectar(":memory:")
    tablas = {f[0] for f in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "calificacion_proyecto" in tablas
    con.close()


def test_la_tabla_se_crea_en_una_base_existente_sin_perder_datos(tmp_path):
    ruta = tmp_path / "vieja.db"
    con = sqlite3.connect(ruta)
    con.executescript(
        "CREATE TABLE curso (id INTEGER PRIMARY KEY, ciclo TEXT NOT NULL, carrera TEXT NOT NULL DEFAULT '',"
        " materia TEXT NOT NULL, grupo TEXT NOT NULL, archivado INTEGER NOT NULL DEFAULT 0);"
        "INSERT INTO curso (ciclo, materia, grupo) VALUES ('2027-I', 'REDES', '3001');"
    )
    con.commit()
    con.close()
    con = conectar(ruta)
    assert con.execute("SELECT COUNT(*) FROM curso").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM calificacion_proyecto").fetchone()[0] == 0
    con.close()


def test_una_sola_calificacion_por_alumno_y_curso(servicio, curso_importado):
    alumno = next(iter(ids(servicio, curso_importado).values()))
    servicio.registrar_proyecto_para_alumno(curso_importado.id, alumno, 8)
    servicio.registrar_proyecto_para_alumno(curso_importado.id, alumno, 9, reemplazar=True)
    cuenta = servicio._repo._db.execute("SELECT COUNT(*) FROM calificacion_proyecto").fetchone()[0]
    assert cuenta == 1


def test_borrar_el_curso_borra_las_calificaciones(servicio, curso_importado):
    alumno = next(iter(ids(servicio, curso_importado).values()))
    servicio.registrar_proyecto_para_alumno(curso_importado.id, alumno, 8)
    assert servicio.resumen_eliminacion_proyecto(curso_importado.id) == 1
    servicio.eliminar_curso(curso_importado.id)
    assert servicio._repo._db.execute("SELECT COUNT(*) FROM calificacion_proyecto").fetchone()[0] == 0


# ---------------- un alumno ----------------
def test_guarda_la_calificacion_de_un_alumno_por_cuenta(servicio, curso_importado):
    r = servicio.registrar_proyecto(curso_importado.id, "100000001", 9.5, date(2027, 3, 9))
    assert r.estado == EstadoRegistro.GUARDADO and r.equipo is None
    assert [a.num_cuenta for a in r.alumnos] == ["100000001"]
    guardada = nota(servicio, curso_importado, "100000001")
    assert guardada.puntos == 9.5 and guardada.fecha == date(2027, 3, 9)


def test_identifica_por_nombre_parcial(servicio, curso_importado):
    r = servicio.registrar_proyecto(curso_importado.id, "abreu", 7)
    assert r.estado == EstadoRegistro.GUARDADO and nota(servicio, curso_importado, "100000001").puntos == 7


def test_ambiguo_y_no_existe_no_guardan_nada(servicio, curso_importado):
    r = servicio.registrar_proyecto(curso_importado.id, "garcia ana", 7)
    assert r.estado == EstadoRegistro.AMBIGUO and len(r.candidatos) == 2
    assert servicio.registrar_proyecto(curso_importado.id, "zzz", 7).estado == EstadoRegistro.NO_EXISTE
    assert set(notas(servicio, curso_importado).values()) == {0.0}


@pytest.mark.parametrize("valor", [-1, float("nan"), float("inf"), "abc", None])
def test_valores_invalidos_se_rechazan(servicio, curso_importado, valor):
    with pytest.raises(ErrorDominio):
        servicio.registrar_proyecto(curso_importado.id, "100000001", valor)


def test_cero_y_puntos_extra_se_aceptan(servicio, curso_importado):
    servicio.registrar_proyecto(curso_importado.id, "100000001", 0)
    servicio.registrar_proyecto(curso_importado.id, "100000002", 105.5)
    assert notas(servicio, curso_importado)["100000002"] == 105.5
    assert nota(servicio, curso_importado, "100000001").puntos == 0


def test_reemplazar_pide_confirmar_y_no_guarda_hasta_entonces(servicio, curso_importado):
    servicio.registrar_proyecto(curso_importado.id, "100000001", 8)
    r = servicio.registrar_proyecto(curso_importado.id, "100000001", 9)
    assert r.estado == EstadoRegistro.CONFIRMAR_REEMPLAZO and r.con_otra == 1
    assert next(iter(r.anteriores.values())).puntos == 8  # la advertencia puede decir «Ya tiene 8»
    assert nota(servicio, curso_importado, "100000001").puntos == 8
    r = servicio.registrar_proyecto(curso_importado.id, "100000001", 9, reemplazar=True)
    assert r.estado == EstadoRegistro.GUARDADO and nota(servicio, curso_importado, "100000001").puntos == 9


def test_repetir_la_misma_nota_no_pide_confirmar(servicio, curso_importado):
    servicio.registrar_proyecto(curso_importado.id, "100000001", 8)
    assert servicio.registrar_proyecto(curso_importado.id, "100000001", 8).estado == EstadoRegistro.GUARDADO


def test_deshacer_restaura_la_anterior_o_elimina(servicio, curso_importado):
    r = servicio.registrar_proyecto(curso_importado.id, "100000001", 8, date(2027, 1, 1))
    servicio.deshacer_proyecto(curso_importado.id, r.anteriores)  # no había nada: se elimina
    assert nota(servicio, curso_importado, "100000001") is None
    servicio.registrar_proyecto(curso_importado.id, "100000001", 8, date(2027, 1, 1))
    r = servicio.registrar_proyecto(curso_importado.id, "100000001", 9, date(2027, 2, 2), reemplazar=True)
    servicio.deshacer_proyecto(curso_importado.id, r.anteriores)
    previa = nota(servicio, curso_importado, "100000001")
    assert previa.puntos == 8 and previa.fecha == date(2027, 1, 1)


def test_alumno_no_inscrito_se_rechaza(servicio, curso_importado):
    otro = servicio.crear_curso("2027-I", "Otra materia", "9999")
    ajeno = servicio.crear_alumno_en_curso(otro.id, "AJENO UNO", TipoInscripcion.OYENTE)
    with pytest.raises(ErrorDominio, match="no está inscrito"):
        servicio.registrar_proyecto_para_alumno(curso_importado.id, ajeno.id, 8)


def test_establecer_y_eliminar_desde_el_historial(servicio, curso_importado):
    alumno = ids(servicio, curso_importado)["100000001"]
    servicio.registrar_proyecto_para_alumno(curso_importado.id, alumno, 8)
    c = servicio.establecer_proyecto(curso_importado.id, alumno, 6.5, date(2027, 4, 4))
    assert c.puntos == 6.5 and c.fecha == date(2027, 4, 4)
    servicio.eliminar_proyecto(curso_importado.id, alumno)
    assert servicio.proyecto_de(curso_importado.id, alumno) is None
    with pytest.raises(ErrorDominio, match="no tiene calificación"):
        servicio.eliminar_proyecto(curso_importado.id, alumno)


def test_el_resumen_trae_proyecto_y_no_toca_lo_demas(servicio, curso_importado):
    servicio.registrar(curso_importado.id, "100000001", 7)
    servicio.registrar_tareas(curso_importado.id, "100000001", 85)
    examen = servicio.crear_examen(curso_importado.id, "Parcial 1")
    servicio.registrar_calificacion(curso_importado.id, examen.id, "100000001", 60)
    antes = [(r.total, r.tareas, r.prom_examenes) for r in servicio.resumen_curso(curso_importado.id)]
    assert set(notas(servicio, curso_importado).values()) == {0.0}  # sin captura vale 0
    servicio.registrar_proyecto(curso_importado.id, "100000001", 9)
    assert notas(servicio, curso_importado)["100000001"] == 9
    assert antes == [(r.total, r.tareas, r.prom_examenes) for r in servicio.resumen_curso(curso_importado.id)]


def test_curso_inexistente(servicio):
    with pytest.raises(ErrorDominio):
        servicio.registrar_proyecto(999, "100000001", 8)


# ---------------- un equipo ----------------
@pytest.mark.parametrize("texto", ["equipo 1", "Equipo 1", "EQUIPO 1", " equipo  1 ", "e 1", "E1", "e1"])
def test_equipo_n_y_e_n_califican_a_todo_el_equipo(servicio, curso_importado, texto):
    equipo(servicio, curso_importado, "100000001", "100000002", "100000003")
    r = servicio.registrar_proyecto(curso_importado.id, texto, 9.5)
    assert r.estado == EstadoRegistro.GUARDADO and r.equipo == 1 and len(r.alumnos) == 3
    n = notas(servicio, curso_importado)
    assert [n["100000001"], n["100000002"], n["100000003"], n["100000004"]] == [9.5, 9.5, 9.5, 0.0]


def test_un_numero_solo_sigue_siendo_cuenta_y_no_equipo(servicio, curso_importado):
    equipo(servicio, curso_importado, "100000001", "100000002")
    servicio.registrar_proyecto(curso_importado.id, "100000003", 7)  # cuenta
    n = notas(servicio, curso_importado)
    assert n["100000003"] == 7 and n["100000001"] == 0


def test_un_nombre_que_empieza_con_e_no_es_un_equipo(servicio, curso_importado):
    r = servicio.registrar_proyecto(curso_importado.id, "elena", 7)  # ACOSTA ORTEGA ELENA
    assert r.equipo is None and notas(servicio, curso_importado)["100000002"] == 7


def test_equipo_inexistente_o_sin_miembros_se_rechaza(servicio, curso_importado):
    with pytest.raises(ErrorDominio, match="no existe o no tiene miembros"):
        servicio.registrar_proyecto(curso_importado.id, "equipo 5", 9)
    numero = equipo(servicio, curso_importado, "100000001")
    servicio.separar_de_equipo(curso_importado.id, [ids(servicio, curso_importado)["100000001"]])
    with pytest.raises(ErrorDominio, match="no existe o no tiene miembros"):
        servicio.registrar_proyecto(curso_importado.id, f"equipo {numero}", 9)
    assert set(notas(servicio, curso_importado).values()) == {0.0}


def test_un_equipo_de_un_alumno_califica_solo_a_ese_alumno(servicio, curso_importado):
    equipo(servicio, curso_importado, "100000004")
    r = servicio.registrar_proyecto(curso_importado.id, "equipo 1", 8)
    assert len(r.alumnos) == 1 and notas(servicio, curso_importado)["100000004"] == 8


def test_los_oyentes_tambien_reciben_la_nota_del_equipo(servicio, curso_importado):
    oyente = servicio.crear_alumno_en_curso(curso_importado.id, "OYENTE UNO", TipoInscripcion.OYENTE)
    servicio.formar_equipo(curso_importado.id, [oyente.id, ids(servicio, curso_importado)["100000001"]])
    servicio.registrar_proyecto(curso_importado.id, "equipo 1", 8)
    assert servicio.proyecto_de(curso_importado.id, oyente.id).puntos == 8


def test_sin_miembros_con_otra_nota_se_guarda_de_inmediato(servicio, curso_importado):
    equipo(servicio, curso_importado, "100000001", "100000002")
    r = servicio.registrar_proyecto(curso_importado.id, "equipo 1", 9)
    assert r.estado == EstadoRegistro.GUARDADO and r.con_otra == 0


def test_si_algun_miembro_tiene_otra_nota_pide_confirmar_con_el_conteo(servicio, curso_importado):
    equipo(servicio, curso_importado, "100000001", "100000002", "100000003", "100000004")
    servicio.registrar_proyecto(curso_importado.id, "100000001", 5)
    servicio.registrar_proyecto(curso_importado.id, "100000002", 6)
    servicio.registrar_proyecto(curso_importado.id, "100000003", 9.5)  # igual a la nueva: no cuenta
    r = servicio.registrar_proyecto(curso_importado.id, "equipo 1", 9.5)
    assert r.estado == EstadoRegistro.CONFIRMAR_REEMPLAZO
    assert (r.con_otra, len(r.alumnos)) == (2, 4)  # «2 de 4 miembros ya tienen calificación»
    n = notas(servicio, curso_importado)
    assert [n["100000001"], n["100000002"], n["100000003"], n["100000004"]] == [5, 6, 9.5, 0]  # nada cambió


def test_confirmado_el_reemplazo_todos_quedan_con_la_nota_del_equipo(servicio, curso_importado):
    equipo(servicio, curso_importado, "100000001", "100000002")
    servicio.registrar_proyecto(curso_importado.id, "100000001", 5)
    r = servicio.registrar_proyecto(curso_importado.id, "equipo 1", 9.5, reemplazar=True)
    assert r.estado == EstadoRegistro.GUARDADO
    assert nota(servicio, curso_importado, "100000001").puntos == 9.5
    assert nota(servicio, curso_importado, "100000002").puntos == 9.5


def test_deshacer_devuelve_a_todos_sus_notas_previas(servicio, curso_importado):
    equipo(servicio, curso_importado, "100000001", "100000002", "100000003")
    servicio.registrar_proyecto(curso_importado.id, "100000001", 5, date(2027, 1, 1))
    antes = notas(servicio, curso_importado)
    r = servicio.registrar_proyecto(curso_importado.id, "equipo 1", 9.5, reemplazar=True)
    assert set(r.anteriores) == {a.id for a in r.alumnos}
    servicio.deshacer_proyecto(curso_importado.id, r.anteriores)
    assert notas(servicio, curso_importado) == antes  # 5, y las demás vuelven a no tener nota
    assert nota(servicio, curso_importado, "100000002") is None
    assert nota(servicio, curso_importado, "100000001").fecha == date(2027, 1, 1)


def test_corregir_a_un_alumno_no_cambia_al_resto_del_equipo(servicio, curso_importado):
    equipo(servicio, curso_importado, "100000001", "100000002")
    servicio.registrar_proyecto(curso_importado.id, "equipo 1", 9)
    servicio.registrar_proyecto(curso_importado.id, "100000002", 7, reemplazar=True)
    n = notas(servicio, curso_importado)
    assert (n["100000001"], n["100000002"]) == (9, 7)


def test_la_nota_no_se_sincroniza_con_el_equipo(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    equipo(servicio, curso_importado, "100000001", "100000002")
    servicio.registrar_proyecto(curso_importado.id, "equipo 1", 9)
    servicio.separar_de_equipo(curso_importado.id, [n["100000002"]])  # sacar no quita la nota
    assert notas(servicio, curso_importado)["100000002"] == 9
    servicio.agregar_a_equipo(curso_importado.id, 1, [n["100000003"]])  # agregar no la da
    assert notas(servicio, curso_importado)["100000003"] == 0
    servicio.registrar_proyecto(curso_importado.id, "equipo 1", 6, reemplazar=True)
    assert notas(servicio, curso_importado)["100000002"] == 9  # el que salió no se entera


def test_calificar_equipos_no_toca_otros_equipos_ni_las_demas_calificaciones(servicio, curso_importado):
    equipo(servicio, curso_importado, "100000001")
    equipo(servicio, curso_importado, "100000002")
    servicio.registrar_tareas(curso_importado.id, "100000001", 85)
    servicio.registrar(curso_importado.id, "100000001", 4)
    antes = [(r.total, r.tareas) for r in servicio.resumen_curso(curso_importado.id)]
    servicio.registrar_proyecto(curso_importado.id, "equipo 1", 9)
    n = notas(servicio, curso_importado)
    assert n["100000001"] == 9 and n["100000002"] == 0
    assert antes == [(r.total, r.tareas) for r in servicio.resumen_curso(curso_importado.id)]
