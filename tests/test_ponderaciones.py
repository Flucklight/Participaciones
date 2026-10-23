"""Ponderaciones por curso y calificación final en el resumen (servicio, datos ficticios)."""

import sqlite3

import pytest

from core.calificacion_final import POR_OMISION, Ponderaciones
from core.database import conectar
from core.errores import ErrorDominio
from core.models import FilaLista, ListaInscripcion
from tests.test_equipos import ids


def final(servicio, curso, cuenta):
    return next(r.final for r in servicio.resumen_curso(curso.id) if r.alumno.num_cuenta == cuenta)


def capturar(servicio, curso, cuenta="100000001", decimas=8, examen=70, tareas=90, proyecto=85):
    """Deja a un alumno con todos los componentes (examen: un solo examen con esa calificación)."""
    cid = curso.id
    if decimas:
        servicio.registrar(cid, cuenta, decimas)
    if examen is not None:
        e = servicio.listar_examenes(cid)[0] if servicio.listar_examenes(cid) else servicio.crear_examen(cid, "Parcial 1")
        servicio.registrar_calificacion(cid, e.id, cuenta, examen)
    servicio.registrar_tareas(cid, cuenta, tareas)
    servicio.registrar_proyecto(cid, cuenta, proyecto)


# ---------------- esquema ----------------
def test_la_tabla_se_crea_en_una_base_nueva_y_en_una_existente(tmp_path):
    con = conectar(":memory:")
    assert "ponderacion" in {f[0] for f in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    con.close()
    ruta = tmp_path / "vieja.db"
    viejo = sqlite3.connect(ruta)
    viejo.executescript(
        "CREATE TABLE curso (id INTEGER PRIMARY KEY, ciclo TEXT NOT NULL, carrera TEXT NOT NULL DEFAULT '',"
        " materia TEXT NOT NULL, grupo TEXT NOT NULL, archivado INTEGER NOT NULL DEFAULT 0);"
        "INSERT INTO curso (ciclo, materia, grupo) VALUES ('2027-I', 'REDES', '3001');"
    )
    viejo.commit()
    viejo.close()
    con = conectar(ruta)
    assert con.execute("SELECT COUNT(*) FROM curso").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM ponderacion").fetchone()[0] == 0
    con.close()


def test_borrar_el_curso_borra_sus_ponderaciones(servicio, curso_importado):
    servicio.establecer_ponderaciones(curso_importado.id, 10, 30, 20, 40)
    servicio.eliminar_curso(curso_importado.id)
    assert servicio._repo._db.execute("SELECT COUNT(*) FROM ponderacion").fetchone()[0] == 0


def test_no_existe_ningun_lugar_donde_se_guarde_la_final(servicio):
    columnas = {
        (t[0], c["name"])
        for t in servicio._repo._db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        for c in servicio._repo._db.execute(f"PRAGMA table_info({t[0]})")
    }
    assert not any("final" in nombre.lower() for _tabla, nombre in columnas)  # se calcula siempre


# ---------------- ponderaciones ----------------
def test_sin_ponderaciones_guardadas_se_usan_las_de_omision(servicio, curso_importado):
    assert servicio.ponderaciones_de(curso_importado.id) == POR_OMISION == Ponderaciones(10, 0, 20, 40)


def test_guardar_y_leer(servicio, curso_importado):
    r = servicio.establecer_ponderaciones(curso_importado.id, 10, 30, 20, 40)
    assert r == Ponderaciones(10, 30, 20, 40) == servicio.ponderaciones_de(curso_importado.id)
    servicio.establecer_ponderaciones(curso_importado.id, 5.5, 25, 20, 49.5)
    assert servicio.ponderaciones_de(curso_importado.id) == Ponderaciones(5.5, 25, 20, 49.5)


def test_las_ponderaciones_son_por_curso(servicio, curso_importado):
    otro = servicio.importar_lista(ListaInscripcion("2027-I", "ING", "BASES", "3002", [FilaLista(1, "100000009", "OTRO ALUMNO")])).curso
    servicio.establecer_ponderaciones(curso_importado.id, 50, 0, 25, 25)
    assert servicio.ponderaciones_de(otro.id) == POR_OMISION


def test_la_suma_puede_pasar_de_100_o_quedarse_corta(servicio, curso_importado):
    assert servicio.establecer_ponderaciones(curso_importado.id, 20, 40, 30, 50).suma == 140
    assert servicio.establecer_ponderaciones(curso_importado.id, 10, 10, 10, 10).suma == 40
    assert servicio.establecer_ponderaciones(curso_importado.id, 0, 0, 0, 0).suma == 0


@pytest.mark.parametrize("valor", [-1, -0.01, 100.01, 101, float("nan"), float("inf"), "abc", None])
def test_valores_invalidos_se_rechazan_y_no_cambian_nada(servicio, curso_importado, valor):
    servicio.establecer_ponderaciones(curso_importado.id, 10, 30, 20, 40)
    with pytest.raises(ErrorDominio, match="entre 0 y 100"):
        servicio.establecer_ponderaciones(curso_importado.id, 10, valor, 20, 40)
    assert servicio.ponderaciones_de(curso_importado.id) == Ponderaciones(10, 30, 20, 40)


def test_los_limites_0_y_100_se_aceptan(servicio, curso_importado):
    assert servicio.establecer_ponderaciones(curso_importado.id, 0, 100, 0, 100) == Ponderaciones(0, 100, 0, 100)


def test_curso_inexistente(servicio):
    with pytest.raises(ErrorDominio):
        servicio.establecer_ponderaciones(999, 10, 30, 20, 40)


# ---------------- la final en el resumen ----------------
def test_la_final_se_calcula_con_las_ponderaciones_del_curso(servicio, curso_importado):
    capturar(servicio, curso_importado)
    servicio.establecer_ponderaciones(curso_importado.id, 10, 30, 20, 40)
    assert final(servicio, curso_importado, "100000001") == pytest.approx(81)


def test_con_las_de_omision_los_examenes_no_pesan(servicio, curso_importado):
    capturar(servicio, curso_importado)
    assert final(servicio, curso_importado, "100000001") == pytest.approx(8 + 18 + 34)


def test_cambiar_las_ponderaciones_recalcula_de_inmediato(servicio, curso_importado):
    capturar(servicio, curso_importado)
    servicio.establecer_ponderaciones(curso_importado.id, 10, 30, 20, 40)
    antes = final(servicio, curso_importado, "100000001")
    servicio.establecer_ponderaciones(curso_importado.id, 10, 30, 20, 50)  # 110 %: puntos extra
    assert final(servicio, curso_importado, "100000001") == pytest.approx(antes + 8.5)


@pytest.mark.parametrize("cambio", ["decimas", "examen", "tareas", "proyecto"])
def test_la_final_cambia_al_cambiar_cualquier_componente(servicio, curso_importado, cambio):
    capturar(servicio, curso_importado)
    servicio.establecer_ponderaciones(curso_importado.id, 10, 30, 20, 40)
    antes = final(servicio, curso_importado, "100000001")
    cid = curso_importado.id
    if cambio == "decimas":
        servicio.registrar(cid, "100000001", 2)
    elif cambio == "examen":
        servicio.registrar_calificacion(cid, servicio.listar_examenes(cid)[0].id, "100000001", 100, reemplazar=True)
    elif cambio == "tareas":
        servicio.registrar_tareas(cid, "100000001", 100, reemplazar=True)
    else:
        servicio.registrar_proyecto(cid, "100000001", 100, reemplazar=True)
    assert final(servicio, curso_importado, "100000001") > antes


def test_el_piso_de_0_de_las_decimas_se_respeta(servicio, curso_importado):
    servicio.registrar(curso_importado.id, "100000001", -5)
    assert final(servicio, curso_importado, "100000001") == 0  # el total con piso es 0, no -5


def test_las_decimas_extra_suman_sin_tope(servicio, curso_importado):
    servicio.establecer_ponderaciones(curso_importado.id, 10, 0, 0, 0)
    servicio.registrar(curso_importado.id, "100000001", 12)
    assert final(servicio, curso_importado, "100000001") == pytest.approx(12)


def test_sin_examenes_la_final_usa_0_en_ese_componente(servicio, curso_importado):
    servicio.establecer_ponderaciones(curso_importado.id, 10, 30, 20, 40)
    servicio.registrar_tareas(curso_importado.id, "100000001", 100)
    servicio.registrar_proyecto(curso_importado.id, "100000001", 100)
    assert final(servicio, curso_importado, "100000001") == pytest.approx(60)


def test_un_alumno_sin_nada_tiene_final_0_y_los_oyentes_tambien_la_tienen(servicio, curso_importado):
    oyente = servicio.crear_alumno_en_curso(curso_importado.id, "OYENTE UNO")
    servicio.registrar_tareas_para_alumno(curso_importado.id, oyente.id, 50)
    resumen = {r.alumno.nombre_completo: r.final for r in servicio.resumen_curso(curso_importado.id)}
    assert resumen["ABREU SOLANO MARCOS"] == 0 and resumen["OYENTE UNO"] == pytest.approx(10)


def test_calcular_la_final_no_cambia_ningun_componente(servicio, curso_importado):
    capturar(servicio, curso_importado)
    antes = [(r.total, r.prom_examenes, r.tareas, r.proyecto) for r in servicio.resumen_curso(curso_importado.id)]
    servicio.establecer_ponderaciones(curso_importado.id, 30, 30, 20, 40)
    despues = [(r.total, r.prom_examenes, r.tareas, r.proyecto) for r in servicio.resumen_curso(curso_importado.id)]
    assert antes == despues


# ---------------- desglose ----------------
def test_el_desglose_coincide_con_la_final(servicio, curso_importado):
    capturar(servicio, curso_importado)
    servicio.establecer_ponderaciones(curso_importado.id, 10, 30, 20, 40)
    alumno = ids(servicio, curso_importado)["100000001"]
    d = servicio.desglose_final(curso_importado.id, alumno)
    assert [c.nombre for c in d.componentes] == ["Participaciones", "Exámenes", "Tareas", "Proyecto final"]
    assert [c.valor for c in d.componentes] == [80, 70, 90, 85]
    assert [c.ponderacion for c in d.componentes] == [10, 30, 20, 40]
    assert d.final == pytest.approx(final(servicio, curso_importado, "100000001")) == pytest.approx(81)


def test_el_desglose_de_un_alumno_no_inscrito_se_rechaza(servicio, curso_importado):
    with pytest.raises(ErrorDominio, match="no está inscrito"):
        servicio.desglose_final(curso_importado.id, 99999)


# ---------------- ponderación de exámenes pendiente ----------------
def test_pendiente_solo_si_hay_examenes_y_nunca_se_guardo(servicio, curso_importado):
    cid = curso_importado.id
    assert servicio.ponderacion_examenes_pendiente(cid) is False  # sin exámenes
    servicio.crear_examen(cid, "Parcial 1")
    assert servicio.ponderacion_examenes_pendiente(cid) is True
    servicio.establecer_ponderaciones(cid, 10, 30, 20, 40)
    assert servicio.ponderacion_examenes_pendiente(cid) is False


def test_guardar_0_explicito_en_examenes_tambien_la_da_por_asignada(servicio, curso_importado):
    cid = curso_importado.id
    servicio.crear_examen(cid, "Parcial 1")
    servicio.establecer_ponderaciones(cid, 10, 0, 20, 40)
    assert servicio.ponderacion_examenes_pendiente(cid) is False  # la persona decidió que no pesan


def test_pendiente_en_un_curso_inexistente(servicio):
    with pytest.raises(ErrorDominio):
        servicio.ponderacion_examenes_pendiente(999)
