import sqlite3

import pytest

from datetime import date

from core.database import conectar
from core.models import Calificacion


def _tablas(conexion) -> set[str]:
    filas = conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {f["name"] for f in filas}


def _curso_y_alumno(conexion) -> tuple[int, int]:
    curso = conexion.execute(
        "INSERT INTO curso (ciclo, materia, grupo) VALUES ('2027-I', 'Algoritmos', '1510')"
    ).lastrowid
    alumno = conexion.execute(
        "INSERT INTO alumno (num_cuenta, nombre_completo, nombre_norm)"
        " VALUES ('100000001', 'ABREU SOLANO MARCOS', 'ABREU SOLANO MARCOS')"
    ).lastrowid
    return curso, alumno


def test_el_esquema_crea_las_tablas_de_examenes():
    conexion = conectar(":memory:")
    assert {"examen", "calificacion"} <= _tablas(conexion)


def test_base_existente_gana_las_tablas_sin_perder_datos(tmp_path):
    ruta = tmp_path / "vieja.db"
    antigua = sqlite3.connect(ruta)
    antigua.executescript(
        """
        CREATE TABLE curso (id INTEGER PRIMARY KEY AUTOINCREMENT, ciclo TEXT NOT NULL,
            carrera TEXT NOT NULL DEFAULT '', materia TEXT NOT NULL, grupo TEXT NOT NULL,
            archivado INTEGER NOT NULL DEFAULT 0, UNIQUE (ciclo, materia, grupo));
        INSERT INTO curso (ciclo, materia, grupo) VALUES ('2026-II', 'Redes', '1401');
        """
    )
    antigua.commit()
    antigua.close()

    conexion = conectar(ruta)
    assert {"examen", "calificacion"} <= _tablas(conexion)
    assert conexion.execute("SELECT materia FROM curso").fetchone()["materia"] == "Redes"


def test_nombre_de_examen_unico_por_curso():
    conexion = conectar(":memory:")
    curso, _ = _curso_y_alumno(conexion)
    conexion.execute("INSERT INTO examen (curso_id, nombre, nombre_norm) VALUES (?, 'Parcial 1', 'PARCIAL 1')", (curso,))
    with pytest.raises(sqlite3.IntegrityError):
        conexion.execute(
            "INSERT INTO examen (curso_id, nombre, nombre_norm) VALUES (?, 'parcial 1', 'PARCIAL 1')", (curso,)
        )


def test_borrar_curso_borra_examenes_y_calificaciones():
    conexion = conectar(":memory:")
    curso, alumno = _curso_y_alumno(conexion)
    examen = conexion.execute(
        "INSERT INTO examen (curso_id, nombre, nombre_norm) VALUES (?, 'Final', 'FINAL')", (curso,)
    ).lastrowid
    conexion.execute(
        "INSERT INTO calificacion (examen_id, alumno_id, puntos, fecha) VALUES (?, ?, 95, '2027-05-01')",
        (examen, alumno),
    )
    conexion.execute("DELETE FROM curso WHERE id = ?", (curso,))
    assert conexion.execute("SELECT COUNT(*) FROM examen").fetchone()[0] == 0
    assert conexion.execute("SELECT COUNT(*) FROM calificacion").fetchone()[0] == 0


def test_una_calificacion_por_alumno_y_examen():
    conexion = conectar(":memory:")
    curso, alumno = _curso_y_alumno(conexion)
    examen = conexion.execute(
        "INSERT INTO examen (curso_id, nombre, nombre_norm) VALUES (?, 'Final', 'FINAL')", (curso,)
    ).lastrowid
    insertar = "INSERT INTO calificacion (examen_id, alumno_id, puntos, fecha) VALUES (?, ?, 80, '2027-05-01')"
    conexion.execute(insertar, (examen, alumno))
    with pytest.raises(sqlite3.IntegrityError):
        conexion.execute(insertar, (examen, alumno))


# ---------------- servicio: CRUD de examenes ----------------
from core.errores import ErrorDominio  # noqa: E402


def test_crear_y_listar_examenes_en_orden_de_creacion(servicio, curso):
    servicio.crear_examen(curso.id, "Parcial 1")
    servicio.crear_examen(curso.id, "  Final ")
    assert [e.nombre for e in servicio.listar_examenes(curso.id)] == ["Parcial 1", "Final"]


def test_nombre_vacio_se_rechaza(servicio, curso):
    with pytest.raises(ErrorDominio):
        servicio.crear_examen(curso.id, "   ")


def test_nombre_duplicado_normalizado_se_rechaza(servicio, curso):
    servicio.crear_examen(curso.id, "Parcial Único")
    with pytest.raises(ErrorDominio):
        servicio.crear_examen(curso.id, "  parcial   unico ")


def test_mismo_nombre_en_otro_curso_es_valido(servicio, curso):
    otro = servicio.crear_curso("2027-I", "Redes", "1401")
    servicio.crear_examen(curso.id, "Final")
    assert servicio.crear_examen(otro.id, "Final").id is not None


def test_examen_de_curso_inexistente(servicio):
    with pytest.raises(ErrorDominio):
        servicio.crear_examen(999, "Final")


def test_renombrar_examen(servicio, curso):
    examen = servicio.crear_examen(curso.id, "Parcial 1")
    assert servicio.renombrar_examen(examen.id, "Primer parcial").nombre == "Primer parcial"
    assert [e.nombre for e in servicio.listar_examenes(curso.id)] == ["Primer parcial"]


def test_renombrar_con_el_mismo_nombre_normalizado_es_valido(servicio, curso):
    examen = servicio.crear_examen(curso.id, "parcial 1")
    assert servicio.renombrar_examen(examen.id, "Parcial 1").nombre == "Parcial 1"


def test_renombrar_a_un_nombre_existente_se_rechaza(servicio, curso):
    servicio.crear_examen(curso.id, "Parcial 1")
    otro = servicio.crear_examen(curso.id, "Final")
    with pytest.raises(ErrorDominio):
        servicio.renombrar_examen(otro.id, "PARCIAL 1")


def test_eliminar_examen_informa_cuantas_calificaciones_se_pierden(servicio, curso_importado):
    examen = servicio.crear_examen(curso_importado.id, "Final")
    alumnos = servicio.resumen_curso(curso_importado.id)
    for fila in alumnos[:2]:
        servicio._repo.guardar_calificacion(
            Calificacion(examen.id, fila.alumno.id, 90, date(2027, 5, 1))
        )
    assert servicio.resumen_eliminacion_examen(examen.id) == 2
    servicio.eliminar_examen(examen.id)
    assert servicio.listar_examenes(curso_importado.id) == []
    assert servicio._repo.contar_calificaciones_examen(examen.id) == 0


def test_eliminar_examen_inexistente(servicio):
    with pytest.raises(ErrorDominio):
        servicio.eliminar_examen(999)
