import sqlite3
from datetime import date

import pytest

from core.database import conectar
from core.errores import ErrorDominio
from core.models import EstadoRegistro


def _tablas(conexion) -> set[str]:
    return {f["name"] for f in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _curso_y_alumno(conexion) -> tuple[int, int]:
    curso = conexion.execute(
        "INSERT INTO curso (ciclo, materia, grupo) VALUES ('2027-I', 'Algoritmos', '1510')"
    ).lastrowid
    alumno = conexion.execute(
        "INSERT INTO alumno (num_cuenta, nombre_completo, nombre_norm)"
        " VALUES ('100000001', 'ABREU SOLANO MARCOS', 'ABREU SOLANO MARCOS')"
    ).lastrowid
    return curso, alumno


# ---------------- esquema ----------------
def test_el_esquema_crea_la_tabla_de_tareas():
    assert "calificacion_tareas" in _tablas(conectar(":memory:"))


def test_base_existente_gana_la_tabla_sin_perder_datos(tmp_path):
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
    assert "calificacion_tareas" in _tablas(conexion)
    assert conexion.execute("SELECT materia FROM curso").fetchone()["materia"] == "Redes"


def test_una_calificacion_de_tareas_por_alumno_y_curso():
    conexion = conectar(":memory:")
    curso, alumno = _curso_y_alumno(conexion)
    insertar = "INSERT INTO calificacion_tareas (curso_id, alumno_id, puntos, fecha) VALUES (?, ?, 80, '2027-05-01')"
    conexion.execute(insertar, (curso, alumno))
    with pytest.raises(sqlite3.IntegrityError):
        conexion.execute(insertar, (curso, alumno))


def test_borrar_el_curso_borra_sus_calificaciones_de_tareas():
    conexion = conectar(":memory:")
    curso, alumno = _curso_y_alumno(conexion)
    conexion.execute(
        "INSERT INTO calificacion_tareas (curso_id, alumno_id, puntos, fecha) VALUES (?, ?, 80, '2027-05-01')",
        (curso, alumno),
    )
    conexion.execute("DELETE FROM curso WHERE id = ?", (curso,))
    assert conexion.execute("SELECT COUNT(*) FROM calificacion_tareas").fetchone()[0] == 0


# ---------------- servicio ----------------
def _alumno(servicio, curso, cuenta):
    return servicio._repo.buscar_alumno_en_curso_por_cuenta(curso.id, cuenta)


def test_registra_por_numero_de_cuenta(servicio, curso_importado):
    r = servicio.registrar_tareas(curso_importado.id, "100000001", 84.5)
    assert r.estado == EstadoRegistro.GUARDADO
    assert r.alumno.nombre_completo == "ABREU SOLANO MARCOS"
    assert (r.puntos, r.anterior) == (84.5, None)
    assert servicio.tareas_de(curso_importado.id, r.alumno.id).puntos == 84.5


def test_registra_por_nombre_parcial(servicio, curso_importado):
    r = servicio.registrar_tareas(curso_importado.id, "acosta", 70)
    assert r.estado == EstadoRegistro.GUARDADO and r.alumno.num_cuenta == "100000002"


def test_nombre_ambiguo_pide_elegir_y_no_guarda(servicio, curso_importado):
    r = servicio.registrar_tareas(curso_importado.id, "garcia ana", 90)
    assert r.estado == EstadoRegistro.AMBIGUO and len(r.candidatos) == 2
    assert servicio.resumen_eliminacion_tareas(curso_importado.id) == 0


def test_alumno_inexistente(servicio, curso_importado):
    r = servicio.registrar_tareas(curso_importado.id, "999999999", 90)
    assert r.estado == EstadoRegistro.NO_EXISTE
    assert servicio.resumen_eliminacion_tareas(curso_importado.id) == 0


def test_cero_y_valores_sobre_cien_son_validos(servicio, curso_importado):
    assert servicio.registrar_tareas(curso_importado.id, "100000001", 0).estado == EstadoRegistro.GUARDADO
    r = servicio.registrar_tareas(curso_importado.id, "100000002", 115)
    assert r.estado == EstadoRegistro.GUARDADO and r.puntos == 115


@pytest.mark.parametrize("valor", [-1, float("nan"), float("inf"), "abc", None])
def test_calificacion_invalida_se_rechaza(servicio, curso_importado, valor):
    with pytest.raises(ErrorDominio):
        servicio.registrar_tareas(curso_importado.id, "100000001", valor)


def test_consulta_vacia_se_rechaza(servicio, curso_importado):
    with pytest.raises(ErrorDominio):
        servicio.registrar_tareas(curso_importado.id, "  ", 5)


def test_alumno_no_inscrito_se_rechaza(servicio, curso_importado):
    otro = servicio.crear_curso("2027-I", "Redes", "1401")
    alumno = _alumno(servicio, curso_importado, "100000001")
    with pytest.raises(ErrorDominio):
        servicio.registrar_tareas_para_alumno(otro.id, alumno.id, 80)


def test_reemplazo_pide_confirmar_y_no_guarda(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000001", 70)
    r = servicio.registrar_tareas(curso_importado.id, "100000001", 90)
    assert r.estado == EstadoRegistro.CONFIRMAR_REEMPLAZO
    assert (r.anterior.puntos, r.puntos) == (70, 90)
    assert servicio.tareas_de(curso_importado.id, r.alumno.id).puntos == 70


def test_reemplazo_confirmado_guarda_y_devuelve_la_anterior(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000001", 70)
    r = servicio.registrar_tareas(curso_importado.id, "100000001", 90, reemplazar=True)
    assert r.estado == EstadoRegistro.GUARDADO and r.anterior.puntos == 70
    assert servicio.tareas_de(curso_importado.id, r.alumno.id).puntos == 90


def test_deshacer_un_reemplazo_restaura_la_anterior(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000001", 70, fecha=date(2027, 3, 1))
    r = servicio.registrar_tareas(curso_importado.id, "100000001", 90, reemplazar=True)
    servicio.deshacer_tareas(curso_importado.id, r.alumno.id, r.anterior)
    restaurada = servicio.tareas_de(curso_importado.id, r.alumno.id)
    assert restaurada.puntos == 70 and restaurada.fecha == date(2027, 3, 1)


def test_deshacer_el_primer_registro_elimina_la_calificacion(servicio, curso_importado):
    r = servicio.registrar_tareas(curso_importado.id, "100000001", 70)
    servicio.deshacer_tareas(curso_importado.id, r.alumno.id, r.anterior)
    assert servicio.tareas_de(curso_importado.id, r.alumno.id) is None


def test_el_resumen_trae_las_tareas_y_0_si_no_hay(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000001", 84.5)
    por_cuenta = {f.alumno.num_cuenta: f for f in servicio.resumen_curso(curso_importado.id)}
    assert por_cuenta["100000001"].tareas == 84.5
    assert por_cuenta["100000002"].tareas == 0


def test_las_tareas_no_alteran_decimas_ni_promedio_de_examenes(servicio, curso_importado):
    alumno = _alumno(servicio, curso_importado, "100000001")
    servicio.registrar(curso_importado.id, "100000001", 5)
    parcial = servicio.crear_examen(curso_importado.id, "Parcial 1")
    servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 60)
    antes = {f.alumno.id: (f.total, f.prom_examenes) for f in servicio.resumen_curso(curso_importado.id)}
    servicio.registrar_tareas(curso_importado.id, "100000001", 95)
    despues = {f.alumno.id: (f.total, f.prom_examenes) for f in servicio.resumen_curso(curso_importado.id)}
    assert antes == despues
    assert servicio.total_alumno(curso_importado.id, alumno.id) == 5


def test_oyente_puede_tener_tareas(servicio, curso_importado):
    servicio.crear_alumno_en_curso(curso_importado.id, "Oyente Ficticio Uno")
    r = servicio.registrar_tareas(curso_importado.id, "oyente ficticio", 60)
    assert r.estado == EstadoRegistro.GUARDADO
    assert servicio.tareas_de(curso_importado.id, r.alumno.id).puntos == 60


def test_establecer_crea_y_corrige_con_fecha(servicio, curso_importado):
    alumno = _alumno(servicio, curso_importado, "100000001")
    c = servicio.establecer_tareas(curso_importado.id, alumno.id, 40, date(2027, 3, 1))
    assert (c.puntos, c.fecha) == (40, date(2027, 3, 1))
    servicio.establecer_tareas(curso_importado.id, alumno.id, 47.5, date(2027, 3, 2))
    assert servicio.tareas_de(curso_importado.id, alumno.id).puntos == 47.5
    assert servicio.resumen_eliminacion_tareas(curso_importado.id) == 1  # corrige, no duplica


@pytest.mark.parametrize("valor", [-1, float("nan"), "abc"])
def test_establecer_invalida(servicio, curso_importado, valor):
    alumno = _alumno(servicio, curso_importado, "100000001")
    with pytest.raises(ErrorDominio):
        servicio.establecer_tareas(curso_importado.id, alumno.id, valor, date.today())


def test_eliminar_vuelve_a_valer_cero(servicio, curso_importado):
    alumno = _alumno(servicio, curso_importado, "100000001")
    servicio.registrar_tareas(curso_importado.id, "100000001", 70)
    servicio.eliminar_tareas(curso_importado.id, alumno.id)
    assert servicio.tareas_de(curso_importado.id, alumno.id) is None
    assert {f.alumno.id: f.tareas for f in servicio.resumen_curso(curso_importado.id)}[alumno.id] == 0


def test_eliminar_sin_calificacion(servicio, curso_importado):
    alumno = _alumno(servicio, curso_importado, "100000001")
    with pytest.raises(ErrorDominio):
        servicio.eliminar_tareas(curso_importado.id, alumno.id)


def test_eliminar_el_curso_cuenta_y_borra_las_tareas(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000001", 70)
    servicio.registrar_tareas(curso_importado.id, "100000002", 80)
    assert servicio.resumen_eliminacion_tareas(curso_importado.id) == 2
    servicio.eliminar_curso(curso_importado.id)
    assert servicio._repo.contar_tareas_curso(curso_importado.id) == 0
    with pytest.raises(ErrorDominio):
        servicio.resumen_eliminacion_tareas(curso_importado.id)
