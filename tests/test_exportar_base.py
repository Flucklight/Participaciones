"""Exportar la base y validar un archivo a importar (R19; datos ficticios)."""

import sqlite3

import pytest

from core.database import abrir_base_externa, conectar, exportar_base
from core.errores import ErrorDominio
from core.repository import Repositorio
from core.services import ServicioParticipaciones


@pytest.fixture
def base(tmp_path, lista):
    conexion = conectar(tmp_path / "origen.db")
    servicio = ServicioParticipaciones(Repositorio(conexion))
    curso = servicio.importar_lista(lista).curso
    alumno = servicio.buscar_alumnos_en_curso(curso.id, "100000001")[0]
    servicio.registrar_para_alumno(curso.id, alumno.id, 5)
    yield servicio, conexion, tmp_path
    conexion.close()


def test_exportar_copia_todo_y_no_toca_el_origen(base):
    servicio, conexion, tmp = base
    antes = servicio.resumen_base_local()
    destino = servicio.exportar_base(tmp / "viaje.db")
    assert destino.is_file()
    assert servicio.resumen_base_local() == antes
    assert servicio.resumen_base_archivo(destino) == antes
    assert (antes.cursos, antes.alumnos, antes.participaciones) == (1, 4, 1)


def test_exportar_a_carpeta_inexistente_da_mensaje_claro(base):
    servicio, _, tmp = base
    with pytest.raises(ErrorDominio, match="no existe"):
        servicio.exportar_base(tmp / "nada" / "viaje.db")


def test_exportar_sobre_la_base_en_uso_se_rechaza(base):
    servicio, _, tmp = base
    with pytest.raises(ErrorDominio, match="en uso"):
        servicio.exportar_base(tmp / "origen.db")


def test_un_archivo_que_no_es_sqlite_se_rechaza(tmp_path):
    ruta = tmp_path / "texto.db"
    ruta.write_text("esto no es una base " * 50)
    with pytest.raises(ErrorDominio, match="no es una base"):
        abrir_base_externa(ruta)


def test_una_base_sin_las_tablas_de_la_app_se_rechaza(tmp_path):
    ruta = tmp_path / "otra.db"
    otra = sqlite3.connect(ruta)
    otra.execute("CREATE TABLE cosas (id INTEGER)")
    otra.commit()
    otra.close()
    with pytest.raises(ErrorDominio, match="faltan tablas"):
        abrir_base_externa(ruta)


def test_un_archivo_inexistente_se_rechaza(tmp_path):
    with pytest.raises(ErrorDominio, match="No se encontró"):
        abrir_base_externa(tmp_path / "no_esta.db")


def test_un_esquema_mas_nuevo_se_rechaza(base):
    servicio, _, tmp = base
    destino = servicio.exportar_base(tmp / "nueva.db")
    futura = sqlite3.connect(destino)
    futura.execute("ALTER TABLE alumno ADD COLUMN telefono TEXT")
    futura.commit()
    futura.close()
    with pytest.raises(ErrorDominio, match="más nueva"):
        abrir_base_externa(destino)


def test_una_base_de_la_version_1_4_0_se_migra_en_memoria_sin_tocar_el_archivo(base):
    servicio, _, tmp = base
    destino = servicio.exportar_base(tmp / "vieja.db")
    vieja = sqlite3.connect(destino)
    vieja.execute("DROP TABLE calificacion_proyecto")
    vieja.execute("DROP TABLE ponderacion")
    vieja.commit()
    vieja.close()
    externa = abrir_base_externa(destino)
    try:
        tablas = {f[0] for f in externa.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"calificacion_proyecto", "ponderacion"} <= tablas
    finally:
        externa.close()
    original = sqlite3.connect(destino)
    tablas = {f[0] for f in original.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    original.close()
    assert "ponderacion" not in tablas  # el archivo del usuario no se migró


def test_equipos_sin_nombre_ni_proyecto_se_migran(tmp_path):
    ruta = tmp_path / "v140.db"
    viejo = sqlite3.connect(ruta)
    base = conectar(":memory:")
    base.backup(viejo)
    base.close()
    viejo.executescript("DROP TABLE miembro_equipo; DROP TABLE equipo;"
                        "CREATE TABLE equipo (curso_id INTEGER NOT NULL, numero INTEGER NOT NULL,"
                        " PRIMARY KEY (curso_id, numero));")
    viejo.commit()
    viejo.close()
    externa = abrir_base_externa(ruta)
    try:
        columnas = {c[1] for c in externa.execute("PRAGMA table_info(equipo)")}
        assert {"nombre", "proyecto"} <= columnas
    finally:
        externa.close()
