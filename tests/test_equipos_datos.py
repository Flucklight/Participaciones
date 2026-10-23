"""Nombre del equipo y título del proyecto: esquema, migración y servicio (datos ficticios)."""

import sqlite3

import pytest

from core.database import conectar
from core.errores import ErrorDominio
from core.models import EstadoEquipo
from tests.test_equipos import ids


# ---------------- esquema y migración ----------------
def test_una_base_nueva_trae_las_columnas_de_nombre_y_proyecto():
    con = conectar(":memory:")
    assert {"nombre", "proyecto"} <= {f["name"] for f in con.execute("PRAGMA table_info(equipo)")}
    con.close()


def test_una_base_de_la_version_1_4_0_recibe_las_columnas_y_conserva_sus_equipos(tmp_path):
    ruta = tmp_path / "v140.db"
    viejo = sqlite3.connect(ruta)
    viejo.executescript(
        "CREATE TABLE curso (id INTEGER PRIMARY KEY, ciclo TEXT NOT NULL, carrera TEXT NOT NULL DEFAULT '',"
        " materia TEXT NOT NULL, grupo TEXT NOT NULL, archivado INTEGER NOT NULL DEFAULT 0);"
        "CREATE TABLE equipo (curso_id INTEGER NOT NULL REFERENCES curso(id) ON DELETE CASCADE,"
        " numero INTEGER NOT NULL, PRIMARY KEY (curso_id, numero));"
        "INSERT INTO curso (ciclo, materia, grupo) VALUES ('2027-I', 'REDES', '3001');"
        "INSERT INTO equipo (curso_id, numero) VALUES (1, 1), (1, 2);"
    )
    viejo.commit()
    viejo.close()
    con = conectar(ruta)
    filas = con.execute("SELECT numero, nombre, proyecto FROM equipo ORDER BY numero").fetchall()
    assert [tuple(f) for f in filas] == [(1, "", ""), (2, "", "")]
    con.close()
    conectar(ruta).close()  # abrir otra vez no falla ni repite la migración


# ---------------- formar con nombre y proyecto ----------------
def test_formar_guarda_nombre_y_proyecto(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]], "Los Cuervos", "Sistema de riego")
    e = servicio.equipos_del_curso(curso_importado.id)[0]
    assert (e.numero, e.nombre, e.proyecto) == (1, "Los Cuervos", "Sistema de riego")


def test_son_opcionales(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]])
    servicio.formar_equipo(curso_importado.id, [n["100000002"]], nombre="Solo nombre")
    servicio.formar_equipo(curso_importado.id, [n["100000003"]], proyecto="Solo proyecto")
    datos = [(e.nombre, e.proyecto) for e in servicio.equipos_del_curso(curso_importado.id)]
    assert datos == [("", ""), ("Solo nombre", ""), ("", "Solo proyecto")]


def test_se_limpian_los_espacios(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]], "  Los   Cuervos ", "\tSistema  de riego\n")
    e = servicio.equipos_del_curso(curso_importado.id)[0]
    assert (e.nombre, e.proyecto) == ("Los Cuervos", "Sistema de riego")


def test_largos_excesivos_se_rechazan_y_no_se_crea_nada(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    with pytest.raises(ErrorDominio, match="nombre del equipo"):
        servicio.formar_equipo(curso_importado.id, [n["100000001"]], "x" * 61)
    with pytest.raises(ErrorDominio, match="título del proyecto"):
        servicio.formar_equipo(curso_importado.id, [n["100000001"]], proyecto="x" * 121)
    assert servicio.equipos_del_curso(curso_importado.id) == []
    assert servicio.formar_equipo(curso_importado.id, [n["100000001"]], "x" * 60).numero == 1  # el límite pasa


def test_si_alguien_ya_tiene_equipo_no_se_guardan_ni_nombre_ni_numero(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]], "Uno")
    r = servicio.formar_equipo(curso_importado.id, [n["100000001"], n["100000002"]], "Dos")
    assert r.estado == EstadoEquipo.YA_TIENEN_EQUIPO
    assert [(e.numero, e.nombre) for e in servicio.equipos_del_curso(curso_importado.id)] == [(1, "Uno")]


# ---------------- editar ----------------
def test_editar_cambia_y_quita_nombre_y_proyecto(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]], "Uno", "Proyecto uno")
    e = servicio.editar_equipo(curso_importado.id, 1, " Nuevo nombre ", "Otro proyecto")
    assert (e.nombre, e.proyecto) == ("Nuevo nombre", "Otro proyecto")
    servicio.editar_equipo(curso_importado.id, 1, "", "")
    e = servicio.equipos_del_curso(curso_importado.id)[0]
    assert (e.nombre, e.proyecto) == ("", "")


def test_editar_un_equipo_que_no_existe_o_esta_vacio_se_rechaza(servicio, curso_importado):
    with pytest.raises(ErrorDominio, match="no existe o ya no tiene miembros"):
        servicio.editar_equipo(curso_importado.id, 9, "x", "y")
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]], "Uno")
    servicio.separar_de_equipo(curso_importado.id, [n["100000001"]])
    with pytest.raises(ErrorDominio, match="no existe o ya no tiene miembros"):
        servicio.editar_equipo(curso_importado.id, 1, "x", "y")


def test_editar_valida_largos(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]], "Uno")
    with pytest.raises(ErrorDominio):
        servicio.editar_equipo(curso_importado.id, 1, "x" * 61, "")
    assert servicio.equipos_del_curso(curso_importado.id)[0].nombre == "Uno"  # no cambió nada


def test_los_datos_viajan_con_el_equipo_aunque_cambien_sus_miembros(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]], "Uno", "Proyecto")
    servicio.agregar_a_equipo(curso_importado.id, 1, [n["100000002"]])
    servicio.separar_de_equipo(curso_importado.id, [n["100000001"]])
    e = servicio.equipos_del_curso(curso_importado.id)[0]
    assert (e.nombre, e.proyecto, [a.num_cuenta for a in e.miembros]) == ("Uno", "Proyecto", ["100000002"])


def test_los_datos_no_alteran_las_calificaciones(servicio, curso_importado):
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(curso_importado.id, [n["100000001"]], "Uno", "Proyecto")
    servicio.registrar_proyecto(curso_importado.id, "equipo 1", 9)
    servicio.editar_equipo(curso_importado.id, 1, "Otro", "Otro proyecto")
    notas = {r.alumno.num_cuenta: r.proyecto for r in servicio.resumen_curso(curso_importado.id)}
    assert notas["100000001"] == 9
