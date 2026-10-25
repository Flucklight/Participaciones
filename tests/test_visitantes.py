"""Visitantes de otro grupo (R21): esquema, migración y alta (datos ficticios)."""

import hashlib
import sqlite3
from types import SimpleNamespace

import pytest

from core.database import abrir_base_externa, conectar
from core.errores import ErrorDominio
from core.models import TipoInscripcion

REGULAR, OYENTE, VISITANTE = TipoInscripcion.REGULAR, TipoInscripcion.OYENTE, TipoInscripcion.VISITANTE


@pytest.fixture
def grupos(servicio):
    """Dos grupos de la misma materia y ciclo: Ana es regular en el 3001 y Luis en el 3002."""
    a = servicio.crear_curso("2027-I", "Redes", "3001")
    b = servicio.crear_curso("2027-I", "Redes", "3002")
    ana = servicio.crear_alumno_en_curso(a.id, "Prueba Ana", REGULAR, "100000001")
    luis = servicio.crear_alumno_en_curso(b.id, "Prueba Luis", REGULAR, "100000002")
    return SimpleNamespace(a=a, b=b, ana=ana, luis=luis)


# ---------------- esquema ----------------
def test_una_base_nueva_acepta_visitantes_con_origen():
    con = conectar(":memory:")
    assert "curso_origen_id" in {f[1] for f in con.execute("PRAGMA table_info(inscripcion)")}
    con.execute("INSERT INTO curso (ciclo, materia, grupo) VALUES ('2027-I', 'REDES', '1')")
    con.execute("INSERT INTO curso (ciclo, materia, grupo) VALUES ('2027-I', 'REDES', '2')")
    con.execute("INSERT INTO alumno (nombre_completo, nombre_norm) VALUES ('X', 'X')")
    con.execute("INSERT INTO inscripcion VALUES (1, 1, 'visitante', 2)")
    con.close()


@pytest.mark.parametrize("fila", [
    "(2, 1, 'visitante', NULL)",   # un visitante sin origen
    "(2, 1, 'regular', 1)",        # un regular con origen
    "(2, 1, 'visitante', 2)",      # de origen, el mismo curso
])
def test_el_esquema_rechaza_visitas_incoherentes(fila):
    con = conectar(":memory:")
    con.execute("INSERT INTO curso (ciclo, materia, grupo) VALUES ('2027-I', 'REDES', '1')")
    con.execute("INSERT INTO curso (ciclo, materia, grupo) VALUES ('2027-I', 'REDES', '2')")
    con.execute("INSERT INTO alumno (nombre_completo, nombre_norm) VALUES ('X', 'X')")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(f"INSERT INTO inscripcion VALUES {fila}")
    con.close()


# ---------------- migración de bases anteriores ----------------
def _base_vieja(ruta):
    """Una base 1.6.x: `inscripcion` sin `curso_origen_id` y con el CHECK anterior."""
    con = sqlite3.connect(ruta)
    con.executescript(
        "CREATE TABLE alumno (id INTEGER PRIMARY KEY AUTOINCREMENT, num_cuenta TEXT UNIQUE,"
        " nombre_completo TEXT NOT NULL, nombre_norm TEXT NOT NULL);"
        "CREATE TABLE curso (id INTEGER PRIMARY KEY AUTOINCREMENT, ciclo TEXT NOT NULL,"
        " carrera TEXT NOT NULL DEFAULT '', materia TEXT NOT NULL, grupo TEXT NOT NULL,"
        " archivado INTEGER NOT NULL DEFAULT 0, UNIQUE (ciclo, materia, grupo));"
        "CREATE TABLE inscripcion (curso_id INTEGER NOT NULL REFERENCES curso(id) ON DELETE CASCADE,"
        " alumno_id INTEGER NOT NULL REFERENCES alumno(id) ON DELETE CASCADE,"
        " tipo TEXT NOT NULL CHECK (tipo IN ('regular', 'oyente')), PRIMARY KEY (curso_id, alumno_id));"
        "CREATE TABLE participacion (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " curso_id INTEGER NOT NULL REFERENCES curso(id) ON DELETE CASCADE,"
        " alumno_id INTEGER NOT NULL REFERENCES alumno(id) ON DELETE CASCADE,"
        " decimas REAL NOT NULL, fecha TEXT NOT NULL, nota TEXT NOT NULL DEFAULT '');"
        "INSERT INTO curso (ciclo, materia, grupo) VALUES ('2027-I', 'REDES', '3001');"
        "INSERT INTO alumno (num_cuenta, nombre_completo, nombre_norm) VALUES ('100000001', 'PRUEBA ANA', 'PRUEBA ANA');"
        "INSERT INTO alumno (nombre_completo, nombre_norm) VALUES ('PRUEBA OYENTE', 'PRUEBA OYENTE');"
        "INSERT INTO inscripcion VALUES (1, 1, 'regular'), (1, 2, 'oyente');"
    )
    con.commit()
    con.close()
    return ruta


def test_una_base_anterior_se_migra_sin_perder_datos_y_deja_respaldo(tmp_path):
    ruta = _base_vieja(tmp_path / "vieja.db")
    con = conectar(ruta)
    assert [tuple(f) for f in con.execute("SELECT curso_id, alumno_id, tipo, curso_origen_id FROM inscripcion ORDER BY alumno_id")] == [
        (1, 1, "regular", None), (1, 2, "oyente", None)
    ]
    assert con.execute("SELECT COUNT(*) FROM alumno").fetchone()[0] == 2
    assert len(list(tmp_path.glob("antes_migracion_*.db"))) == 1
    con.execute("INSERT INTO curso (ciclo, materia, grupo) VALUES ('2027-I', 'REDES', '3002')")
    con.execute("INSERT INTO inscripcion VALUES (2, 1, 'visitante', 1)")  # ya acepta visitantes
    con.close()


def test_migrar_dos_veces_no_cambia_nada_ni_crea_otro_respaldo(tmp_path):
    ruta = _base_vieja(tmp_path / "vieja.db")
    conectar(ruta).close()
    con = conectar(ruta)
    assert con.execute("SELECT COUNT(*) FROM inscripcion").fetchone()[0] == 2
    assert len(list(tmp_path.glob("antes_migracion_*.db"))) == 1
    con.close()


def test_el_respaldo_previo_conserva_el_esquema_viejo(tmp_path):
    ruta = _base_vieja(tmp_path / "vieja.db")
    conectar(ruta).close()
    respaldo = next(tmp_path.glob("antes_migracion_*.db"))
    con = sqlite3.connect(respaldo)
    assert "curso_origen_id" not in {f[1] for f in con.execute("PRAGMA table_info(inscripcion)")}
    assert con.execute("SELECT COUNT(*) FROM inscripcion").fetchone()[0] == 2
    con.close()


def test_un_archivo_ajeno_anterior_se_migra_en_memoria_sin_tocar_el_archivo(tmp_path):
    ruta = _base_vieja(tmp_path / "vieja.db")
    antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
    con = abrir_base_externa(ruta)
    assert "curso_origen_id" in {f[1] for f in con.execute("PRAGMA table_info(inscripcion)")}
    assert con.execute("SELECT COUNT(*) FROM inscripcion").fetchone()[0] == 2
    con.close()
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == antes
    assert list(tmp_path.glob("antes_migracion_*.db")) == []


# ---------------- candidatos ----------------
def test_candidatos_por_cuenta_y_por_nombre_parcial(servicio, grupos):
    por_cuenta = servicio.candidatos_visitante(grupos.b.id, "100000001")
    assert [(a.id, c.id) for a, c in por_cuenta] == [(grupos.ana.id, grupos.a.id)]
    por_nombre = servicio.candidatos_visitante(grupos.b.id, "ana")
    assert [(a.id, c.grupo) for a, c in por_nombre] == [(grupos.ana.id, "3001")]


def test_candidatos_ignoran_acentos_y_mayusculas(servicio, grupos):
    otro = servicio.crear_alumno_en_curso(grupos.a.id, "Gómez Peña José", REGULAR, "100000010")
    assert [a.id for a, _ in servicio.candidatos_visitante(grupos.b.id, "gomez pena")] == [otro.id]


def test_candidatos_solo_de_la_misma_materia_y_ciclo(servicio, grupos):
    otra_materia = servicio.crear_curso("2027-I", "Bases de Datos", "3001")
    otro_ciclo = servicio.crear_curso("2027-II", "Redes", "3001")
    servicio.crear_alumno_en_curso(otra_materia.id, "Prueba Marta", REGULAR, "100000020")
    servicio.crear_alumno_en_curso(otro_ciclo.id, "Prueba Pedro", REGULAR, "100000021")
    assert servicio.candidatos_visitante(grupos.b.id, "prueba") != []
    nombres = {a.nombre_completo for a, _ in servicio.candidatos_visitante(grupos.b.id, "prueba")}
    assert nombres == {"PRUEBA ANA"}  # ni Marta (otra materia) ni Pedro (otro ciclo) ni Luis (ya está aquí)


def test_la_carrera_no_cuenta_para_ser_la_misma_materia(servicio):
    a = servicio.crear_curso("2027-I", "Redes", "3001", "Ingeniería en Computación")
    b = servicio.crear_curso("2027-I", "Redes", "3002", "Ingeniería Eléctrica")
    ana = servicio.crear_alumno_en_curso(a.id, "Prueba Ana", REGULAR, "100000001")
    assert [x.id for x, _ in servicio.candidatos_visitante(b.id, "ana")] == [ana.id]


def test_candidatos_excluye_oyentes_y_a_quien_ya_esta_inscrito(servicio, grupos):
    servicio.crear_alumno_en_curso(grupos.a.id, "Prueba Oyente", OYENTE)
    assert servicio.candidatos_visitante(grupos.b.id, "oyente") == []
    assert servicio.candidatos_visitante(grupos.b.id, "100000002") == []  # Luis ya está en el 3002
    servicio.inscribir_visitante(grupos.b.id, grupos.ana.id, grupos.a.id)
    assert servicio.candidatos_visitante(grupos.b.id, "ana") == []


def test_varias_coincidencias_se_devuelven_todas(servicio, grupos):
    otra = servicio.crear_alumno_en_curso(grupos.a.id, "Prueba Ana María", REGULAR, "100000011")
    ids = {a.id for a, _ in servicio.candidatos_visitante(grupos.b.id, "prueba ana")}
    assert ids == {grupos.ana.id, otra.id}


def test_consulta_vacia(servicio, grupos):
    with pytest.raises(ErrorDominio, match="Escribe"):
        servicio.candidatos_visitante(grupos.b.id, "  ")


# ---------------- inscribir ----------------
def test_inscribir_visitante_no_toca_la_inscripcion_de_origen(servicio, grupos):
    servicio.inscribir_visitante(grupos.b.id, grupos.ana.id, grupos.a.id)
    assert servicio.tipo_inscripcion(grupos.b.id, grupos.ana.id) == VISITANTE
    assert servicio.tipo_inscripcion(grupos.a.id, grupos.ana.id) == REGULAR
    assert servicio.curso_de_datos(grupos.b.id, grupos.ana.id).id == grupos.a.id
    assert servicio.curso_de_datos(grupos.a.id, grupos.ana.id).id == grupos.a.id
    assert servicio.curso_de_datos(grupos.b.id, grupos.luis.id).id == grupos.b.id


def test_puede_ser_visitante_en_varios_grupos(servicio, grupos):
    c = servicio.crear_curso("2027-I", "Redes", "3003")
    servicio.inscribir_visitante(grupos.b.id, grupos.ana.id, grupos.a.id)
    servicio.inscribir_visitante(c.id, grupos.ana.id, grupos.a.id)
    assert servicio.curso_de_datos(c.id, grupos.ana.id).id == grupos.a.id


def test_rechaza_un_origen_de_otra_materia_ciclo_o_el_mismo_grupo(servicio, grupos):
    otra = servicio.crear_curso("2027-I", "Bases de Datos", "3001")
    ajena = servicio.crear_alumno_en_curso(otra.id, "Prueba Marta", REGULAR, "100000020")
    with pytest.raises(ErrorDominio, match="misma materia y ciclo"):
        servicio.inscribir_visitante(grupos.b.id, ajena.id, otra.id)
    with pytest.raises(ErrorDominio, match="misma materia y ciclo"):
        servicio.inscribir_visitante(grupos.b.id, grupos.luis.id, grupos.b.id)


def test_rechaza_si_no_es_regular_en_el_origen(servicio, grupos):
    oyente = servicio.crear_alumno_en_curso(grupos.a.id, "Prueba Oyente", OYENTE)
    with pytest.raises(ErrorDominio, match="no es alumno regular"):
        servicio.inscribir_visitante(grupos.b.id, oyente.id, grupos.a.id)
    with pytest.raises(ErrorDominio, match="no es alumno regular"):
        servicio.inscribir_visitante(grupos.b.id, grupos.luis.id, grupos.a.id)  # Luis no está en el 3001


def test_rechaza_si_ya_esta_inscrito_en_el_grupo_que_visita(servicio, grupos):
    servicio.inscribir_visitante(grupos.b.id, grupos.ana.id, grupos.a.id)
    with pytest.raises(ErrorDominio, match="ya está en este curso"):
        servicio.inscribir_visitante(grupos.b.id, grupos.ana.id, grupos.a.id)
    with pytest.raises(ErrorDominio, match="no es alumno regular"):  # Ana solo visita el 3002: no es su origen
        servicio.inscribir_visitante(grupos.a.id, grupos.ana.id, grupos.b.id)


def test_rechaza_a_quien_ya_esta_en_el_grupo_como_oyente(servicio, grupos):
    servicio.inscribir_alumno_existente(grupos.b.id, grupos.ana.id, OYENTE)
    with pytest.raises(ErrorDominio, match="ya está en este curso"):
        servicio.inscribir_visitante(grupos.b.id, grupos.ana.id, grupos.a.id)


def test_un_visitante_no_se_crea_ni_se_cambia_por_las_vias_manuales(servicio, grupos):
    with pytest.raises(ErrorDominio, match="Visitante de otro grupo"):
        servicio.crear_alumno_en_curso(grupos.b.id, "Prueba Nuevo", VISITANTE)
    with pytest.raises(ErrorDominio, match="Visitante de otro grupo"):
        servicio.inscribir_alumno_existente(grupos.b.id, grupos.ana.id, VISITANTE)
    with pytest.raises(ErrorDominio, match="Visitante de otro grupo"):
        servicio.cambiar_tipo(grupos.a.id, grupos.ana.id, VISITANTE)
    servicio.inscribir_visitante(grupos.b.id, grupos.ana.id, grupos.a.id)
    with pytest.raises(ErrorDominio, match="no cambia de tipo"):
        servicio.cambiar_tipo(grupos.b.id, grupos.ana.id, REGULAR)
    assert servicio.tipo_inscripcion(grupos.b.id, grupos.ana.id) == VISITANTE


def test_los_cursos_del_historial_no_incluyen_los_grupos_que_solo_visita(servicio, grupos):
    servicio.inscribir_visitante(grupos.b.id, grupos.ana.id, grupos.a.id)
    assert [c.id for c in servicio.cursos_de_alumno(grupos.ana.id)] == [grupos.a.id]


def test_eliminar_el_origen_borra_las_visitas_por_cascada(servicio, grupos):
    servicio.inscribir_visitante(grupos.b.id, grupos.ana.id, grupos.a.id)
    servicio.eliminar_curso(grupos.a.id)
    assert [f.alumno.id for f in servicio.resumen_curso(grupos.b.id)] == [grupos.luis.id]
