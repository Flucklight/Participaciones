"""Equipos de proyecto: esquema y servicio (datos ficticios)."""

import sqlite3

import pytest

from core.database import conectar
from core.errores import ErrorDominio
from core.models import EstadoEquipo, FilaLista, ListaInscripcion, TipoInscripcion


def ids(servicio, curso):
    """{cuenta: alumno_id} de los alumnos del curso."""
    return {r.alumno.num_cuenta: r.alumno.id for r in servicio.resumen_curso(curso.id)}


def equipo_de(servicio, curso, cuenta):
    return next(r.equipo for r in servicio.resumen_curso(curso.id) if r.alumno.num_cuenta == cuenta)


# ---------------- esquema ----------------
def test_las_tablas_se_crean_en_una_base_nueva():
    con = conectar(":memory:")
    tablas = {f[0] for f in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"equipo", "miembro_equipo"} <= tablas
    con.close()


def test_las_tablas_se_crean_en_una_base_existente_sin_perder_datos(tmp_path):
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
    assert con.execute("SELECT COUNT(*) FROM equipo").fetchone()[0] == 0
    con.close()


def test_un_alumno_no_puede_estar_en_dos_equipos_del_mismo_curso(servicio, curso_importado):
    repo = servicio._repo
    a = ids(servicio, curso_importado)["100000001"]
    repo.crear_equipo(curso_importado.id, 1)
    repo.crear_equipo(curso_importado.id, 2)
    repo.agregar_miembro_equipo(curso_importado.id, a, 1)
    with pytest.raises(sqlite3.IntegrityError):
        repo.agregar_miembro_equipo(curso_importado.id, a, 2)


def test_borrar_el_curso_borra_sus_equipos(servicio, curso_importado):
    a = ids(servicio, curso_importado)["100000001"]
    servicio.formar_equipo(curso_importado.id, [a])
    servicio.eliminar_curso(curso_importado.id)
    assert servicio._repo._db.execute("SELECT COUNT(*) FROM equipo").fetchone()[0] == 0
    assert servicio._repo._db.execute("SELECT COUNT(*) FROM miembro_equipo").fetchone()[0] == 0


# ---------------- formar ----------------
def test_forma_un_equipo_con_varios_alumnos(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    r = servicio.formar_equipo(curso_importado.id, [n["100000001"], n["100000002"]])
    assert r.estado == EstadoEquipo.FORMADO and r.numero == 1
    assert {a.num_cuenta for a in r.miembros} == {"100000001", "100000002"}
    assert equipo_de(servicio, curso_importado, "100000001") == 1
    assert equipo_de(servicio, curso_importado, "100000003") is None


def test_un_equipo_puede_ser_de_un_solo_alumno(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    r = servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    assert r.estado == EstadoEquipo.FORMADO and len(r.miembros) == 1


def test_lista_vacia_se_rechaza(servicio, curso_importado):
    with pytest.raises(ErrorDominio, match="al menos un alumno"):
        servicio.formar_equipo(curso_importado.id, [])


def test_un_alumno_repetido_en_la_lista_cuenta_una_vez(servicio, curso_importado):
    a = ids(servicio, curso_importado)["100000001"]
    assert len(servicio.formar_equipo(curso_importado.id, [a, a]).miembros) == 1


def test_alumno_no_inscrito_se_rechaza(servicio, curso_importado):
    otro = servicio.crear_curso("2027-I", "Otra materia", "9999")
    ajeno = servicio.crear_alumno_en_curso(otro.id, "AJENO UNO", TipoInscripcion.OYENTE)
    with pytest.raises(ErrorDominio, match="no está inscrito"):
        servicio.formar_equipo(curso_importado.id, [ajeno.id])


def test_alumno_inexistente_se_rechaza(servicio, curso_importado):
    with pytest.raises(ErrorDominio):
        servicio.formar_equipo(curso_importado.id, [99999])


def test_curso_inexistente(servicio):
    with pytest.raises(ErrorDominio):
        servicio.formar_equipo(999, [1])


def test_los_oyentes_tambien_forman_equipo(servicio, curso_importado):
    oyente = servicio.crear_alumno_en_curso(curso_importado.id, "OYENTE UNO", TipoInscripcion.OYENTE)
    assert servicio.formar_equipo(curso_importado.id, [oyente.id]).estado == EstadoEquipo.FORMADO


# ---------------- numeración ----------------
def test_la_numeracion_es_incremental_por_curso(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    numeros = [
        servicio.formar_equipo(curso_importado.id, [n[c]]).numero
        for c in ("100000001", "100000002", "100000003")
    ]
    assert numeros == [1, 2, 3]


def test_la_numeracion_es_independiente_entre_cursos(servicio, curso_importado):
    otro = servicio.importar_lista(ListaInscripcion("2027-I", "ING", "BASES", "3002",
                                                    [FilaLista(1, "100000009", "OTRO ALUMNO")])).curso
    servicio.formar_equipo(curso_importado.id, [ids(servicio, curso_importado)["100000001"]])
    r = servicio.formar_equipo(otro.id, [ids(servicio, otro)["100000009"]])
    assert r.numero == 1


def test_el_numero_no_se_reutiliza_aunque_el_equipo_se_quede_vacio(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])  # equipo 1
    servicio.formar_equipo(curso_importado.id, [n["100000002"]])  # equipo 2
    servicio.separar_de_equipo(curso_importado.id, [n["100000002"]])  # el 2 queda vacío
    assert servicio.formar_equipo(curso_importado.id, [n["100000003"]]).numero == 3
    servicio.separar_de_equipo(curso_importado.id, [n["100000001"]])
    servicio.separar_de_equipo(curso_importado.id, [n["100000003"]])
    assert servicio.formar_equipo(curso_importado.id, [n["100000004"]]).numero == 4


# ---------------- alguien ya tiene equipo ----------------
def test_si_alguien_ya_tiene_equipo_no_se_crea_ni_se_mueve_nada(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    r = servicio.formar_equipo(curso_importado.id, [n["100000001"], n["100000002"]])
    assert r.estado == EstadoEquipo.YA_TIENEN_EQUIPO and r.numero is None
    assert [(a.num_cuenta, num) for a, num in r.con_equipo] == [("100000001", 1)]
    assert equipo_de(servicio, curso_importado, "100000001") == 1
    assert equipo_de(servicio, curso_importado, "100000002") is None
    assert [e.numero for e in servicio.equipos_del_curso(curso_importado.id)] == [1]
    # y el número 2 sigue libre: el rechazo no lo gastó
    assert servicio.formar_equipo(curso_importado.id, [n["100000002"]]).numero == 2


def test_informa_a_todos_los_que_ya_tenian_equipo(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    servicio.formar_equipo(curso_importado.id, [n["100000002"]])
    r = servicio.formar_equipo(curso_importado.id, [n["100000001"], n["100000002"], n["100000003"]])
    assert sorted((a.num_cuenta, num) for a, num in r.con_equipo) == [("100000001", 1), ("100000002", 2)]


# ---------------- separar ----------------
def test_separar_uno_o_varios(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"], n["100000002"], n["100000003"]])
    sep = servicio.separar_de_equipo(curso_importado.id, [n["100000001"], n["100000002"]])
    assert sep == {n["100000001"]: 1, n["100000002"]: 1}
    assert equipo_de(servicio, curso_importado, "100000003") == 1  # sigue en el equipo


def test_separar_a_quien_no_tiene_equipo_no_falla_ni_cambia_nada(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    assert servicio.separar_de_equipo(curso_importado.id, [n["100000004"]]) == {}


def test_deshacer_la_separacion_devuelve_a_cada_uno_a_su_equipo(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"], n["100000002"]])
    servicio.formar_equipo(curso_importado.id, [n["100000003"]])
    sep = servicio.separar_de_equipo(curso_importado.id, [n["100000001"], n["100000003"]])
    servicio.deshacer_separacion(curso_importado.id, sep)
    assert (equipo_de(servicio, curso_importado, "100000001"), equipo_de(servicio, curso_importado, "100000003")) == (1, 2)


def test_deshacer_la_separacion_no_mueve_a_quien_ya_esta_en_otro_equipo(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    sep = servicio.separar_de_equipo(curso_importado.id, [n["100000001"]])
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])  # equipo 2
    servicio.deshacer_separacion(curso_importado.id, sep)
    assert equipo_de(servicio, curso_importado, "100000001") == 2


def test_deshacer_la_formacion_libera_a_los_miembros_pero_gasta_el_numero(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    r = servicio.formar_equipo(curso_importado.id, [n["100000001"], n["100000002"]])
    servicio.deshacer_equipo(curso_importado.id, r.numero)
    assert equipo_de(servicio, curso_importado, "100000001") is None
    assert servicio.equipos_del_curso(curso_importado.id) == []
    assert servicio.formar_equipo(curso_importado.id, [n["100000001"]]).numero == 2


# ---------------- consultas ----------------
def test_equipos_del_curso_trae_miembros_por_nombre_y_omite_vacios(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000003"], n["100000001"]])
    servicio.formar_equipo(curso_importado.id, [n["100000002"]])
    servicio.separar_de_equipo(curso_importado.id, [n["100000002"]])  # equipo 2 vacío
    equipos = servicio.equipos_del_curso(curso_importado.id)
    assert [e.numero for e in equipos] == [1]
    assert [a.nombre_completo for a in equipos[0].miembros] == ["ABREU SOLANO MARCOS", "GARCIA LOPEZ ANA"]


def test_equipo_de_un_alumno(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    assert servicio.equipo_de(curso_importado.id, n["100000001"]) == 1
    assert servicio.equipo_de(curso_importado.id, n["100000002"]) is None


def test_los_equipos_no_alteran_decimas_examenes_ni_tareas(servicio, curso_importado):
    servicio.registrar(curso_importado.id, "100000001", 7)
    servicio.registrar_tareas(curso_importado.id, "100000001", 85)
    examen = servicio.crear_examen(curso_importado.id, "Parcial 1")
    servicio.registrar_calificacion(curso_importado.id, examen.id, "100000001", 60)
    antes = [(r.total, r.tareas, r.prom_examenes) for r in servicio.resumen_curso(curso_importado.id)]
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"], n["100000002"]])
    servicio.separar_de_equipo(curso_importado.id, [n["100000002"]])
    assert antes == [(r.total, r.tareas, r.prom_examenes) for r in servicio.resumen_curso(curso_importado.id)]
