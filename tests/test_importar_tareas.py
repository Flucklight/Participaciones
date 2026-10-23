"""Lector de calificaciones de otra plataforma (.xlsx y .csv) con datos ficticios."""

import os
from pathlib import Path

import pytest

from core.errores import ErrorImportacion
from importers.calificaciones_plataforma import leer_calificaciones
from tests.conftest import crear_excel
from tests.plataforma import crear_csv_plataforma, crear_excel_plataforma

ALUMNOS = [
    ("ABREU SOLANO", "MARCOS", [80, 90, 100]),
    ("PEÑA RUIZ", "MARÍA JOSÉ", [50, None, 100]),
    ("ACOSTA ORTEGA", "ELENA", [100, 100, 100]),
]


@pytest.fixture
def xlsx(tmp_path):
    return crear_excel_plataforma(tmp_path / "p.xlsx", ALUMNOS)


@pytest.fixture
def csv(tmp_path):
    return crear_csv_plataforma(tmp_path / "p.csv", ALUMNOS)


def _claves(archivo):
    return [c.clave for c in archivo.columnas]


# ---------------- disposición del xlsx ----------------
def test_xlsx_lee_alumnos_sin_la_fila_de_media(xlsx):
    archivo = leer_calificaciones(xlsx)
    assert [f.nombre_completo for f in archivo.filas] == [
        "ABREU SOLANO MARCOS", "PEÑA RUIZ MARÍA JOSÉ", "ACOSTA ORTEGA ELENA"]
    assert archivo.filas[0].apellidos == "ABREU SOLANO" and archivo.filas[0].nombres == "MARCOS"


def test_xlsx_lista_columnas_numericas_con_su_rotulo(xlsx):
    archivo = leer_calificaciones(xlsx)
    assert _claves(archivo) == ["D", "E", "F", "G", "H"]
    rotulos = {c.clave: c.rotulo for c in archivo.columnas}
    assert rotulos["E"] == "Tarea 1: Introducción" and rotulos["G"] == "Tarea 3: Gramáticas"
    assert rotulos["D"] == "" and rotulos["H"] == ""
    assert archivo.columnas[-1].descripcion == "Columna H (sin encabezado)"
    assert archivo.columnas[1].descripcion == "Tarea 1: Introducción (columna E)"


def test_xlsx_sugiere_la_columna_de_mas_a_la_derecha(xlsx):
    archivo = leer_calificaciones(xlsx)
    assert archivo.columna_sugerida.clave == "H"
    assert archivo.filas[0].valores["H"] == 90
    assert archivo.filas[0].valores["D"] == pytest.approx(0.9)


def test_xlsx_celda_vacia_es_sin_dato(xlsx):
    assert leer_calificaciones(xlsx).filas[1].valores["F"] is None


def test_xlsx_lee_grupo_y_ciclo(tmp_path):
    ruta = crear_excel_plataforma(tmp_path / "p.xlsx", ALUMNOS, grupo="1509", ciclo="2027-II")
    archivo = leer_calificaciones(ruta)
    assert (archivo.grupo, archivo.ciclo) == ("1509", "2027-II")


def test_xlsx_formula_sin_valor_guardado_es_sin_dato(tmp_path):
    ruta = crear_excel_plataforma(tmp_path / "p.xlsx", ALUMNOS, formula=True)  # nunca se calculó
    archivo = leer_calificaciones(ruta)
    assert all(f.valores.get("H") is None for f in archivo.filas)
    assert "H" not in _claves(archivo)  # ninguna fila trae valor: la columna no es candidata
    assert archivo.columna_sugerida.clave == "G"


# ---------------- disposición del csv ----------------
def test_csv_lee_alumnos_sin_filas_de_fecha_ni_puntos(csv):
    archivo = leer_calificaciones(csv)
    assert [f.nombre_completo for f in archivo.filas] == [
        "ABREU SOLANO MARCOS", "PEÑA RUIZ MARÍA JOSÉ", "ACOSTA ORTEGA ELENA"]
    assert (archivo.grupo, archivo.ciclo) == ("", "")  # el csv no trae datos del curso


def test_csv_columnas_con_rotulo_y_promedio_al_final(csv):
    archivo = leer_calificaciones(csv)
    assert _claves(archivo) == ["D", "E", "F", "G"]
    assert archivo.columnas[0].rotulo == "Tarea 1: Introducción"
    assert archivo.columna_sugerida.descripcion == "Columna G (sin encabezado)"
    assert archivo.filas[0].valores["G"] == 90
    assert archivo.filas[1].valores["E"] is None and archivo.filas[1].valores["G"] == 75


@pytest.mark.parametrize("bom", [False, True])
def test_csv_con_y_sin_bom(tmp_path, bom):
    ruta = crear_csv_plataforma(tmp_path / "p.csv", ALUMNOS, bom=bom)
    assert len(leer_calificaciones(ruta).filas) == 3


def test_csv_con_punto_y_coma_y_coma_decimal(tmp_path):
    ruta = crear_csv_plataforma(tmp_path / "p.csv", ALUMNOS, delimitador=";", decimal=",")
    archivo = leer_calificaciones(ruta)
    assert len(archivo.filas) == 3
    assert archivo.filas[1].valores["G"] == 75  # (50 + 100) / 2


def test_csv_con_acentos_en_windows_1252(tmp_path):
    ruta = crear_csv_plataforma(tmp_path / "p.csv", ALUMNOS)
    Path(ruta).write_bytes(Path(ruta).read_text(encoding="utf-8").encode("cp1252"))
    assert leer_calificaciones(ruta).filas[1].nombres == "MARÍA JOSÉ"


def test_valor_no_numerico_se_conserva_como_texto(tmp_path):
    ruta = crear_csv_plataforma(tmp_path / "p.csv", ALUMNOS)
    texto = Path(ruta).read_text(encoding="utf-8").replace("alumno1@ejemplo.mx,80,90,100,90.0",
                                                           "alumno1@ejemplo.mx,80,90,100,Sin entrega")
    Path(ruta).write_text(texto, encoding="utf-8", newline="")
    assert leer_calificaciones(ruta).filas[0].valores["G"] == "Sin entrega"


# ---------------- cuenta opcional ----------------
def test_si_trae_columna_de_cuenta_la_lee_y_no_es_calificacion(tmp_path):
    ruta = crear_csv_plataforma(tmp_path / "p.csv", ALUMNOS, cuentas=["100000001", "100000002", "100000003"])
    archivo = leer_calificaciones(ruta)
    assert [f.cuenta for f in archivo.filas] == ["100000001", "100000002", "100000003"]
    assert "H" not in _claves(archivo)
    assert archivo.columna_sugerida.clave == "G"


def test_sin_columna_de_cuenta_queda_vacia(csv):
    assert all(f.cuenta == "" for f in leer_calificaciones(csv).filas)


# ---------------- errores ----------------
def test_archivo_inexistente(tmp_path):
    with pytest.raises(ErrorImportacion, match="abrir"):
        leer_calificaciones(tmp_path / "nada.xlsx")


def test_extension_no_soportada(tmp_path):
    ruta = tmp_path / "datos.txt"
    ruta.write_text("hola")
    with pytest.raises(ErrorImportacion, match="xlsx"):
        leer_calificaciones(ruta)


def test_excel_que_no_es_de_la_plataforma(tmp_path):
    ruta = crear_excel(tmp_path / "lista.xlsx", [("100000001", "ABREU SOLANO MARCOS")])
    with pytest.raises(ErrorImportacion, match="alumnos"):
        leer_calificaciones(ruta)


def test_archivo_con_encabezados_pero_sin_alumnos(tmp_path):
    ruta = crear_csv_plataforma(tmp_path / "p.csv", [])
    with pytest.raises(ErrorImportacion, match="alumnos"):
        leer_calificaciones(ruta)


def test_alumnos_sin_ninguna_columna_con_calificaciones(tmp_path):
    ruta = tmp_path / "p.csv"
    ruta.write_text("Apellidos,Nombre,Dirección de correo\r\nABREU,MARCOS,a@ejemplo.mx\r\n", encoding="utf-8")
    with pytest.raises(ErrorImportacion, match="calificaciones"):
        leer_calificaciones(ruta)


# ---------------- muestras reales (opcionales) ----------------
@pytest.mark.skipif(not os.environ.get("PLATAFORMA_REAL"), reason="define PLATAFORMA_REAL con un .xlsx real")
def test_muestra_real_xlsx():
    archivo = leer_calificaciones(os.environ["PLATAFORMA_REAL"])
    assert archivo.filas and archivo.columna_sugerida.rotulo == ""
    assert archivo.grupo


@pytest.mark.skipif(not os.environ.get("PLATAFORMA_REAL_CSV"), reason="define PLATAFORMA_REAL_CSV con un .csv real")
def test_muestra_real_csv():
    archivo = leer_calificaciones(os.environ["PLATAFORMA_REAL_CSV"])
    assert archivo.filas and archivo.columna_sugerida.rotulo == ""
