import csv
from datetime import date

import openpyxl
import pytest

from core.errores import ErrorDominio
from core.models import Curso
from exporters.curso import exportar_curso, nombre_sugerido


@pytest.fixture
def curso_con_datos(servicio, curso_importado):
    """Curso con 4 regulares, un oyente y participaciones (una toca el piso de 0)."""
    cid = curso_importado.id
    servicio.registrar(cid, "100000001", 10)
    servicio.agregar_participacion(cid, servicio.registrar(cid, "100000001", 5).alumno.id, -50, date.today(), "no entregó")
    servicio.registrar(cid, "100000002", 20)
    oyente = servicio.crear_alumno_en_curso(cid, "Zeta Oyente")
    servicio.registrar_para_alumno(cid, oyente.id, 7)
    return curso_importado


def _hoja(ruta, nombre):
    return openpyxl.load_workbook(ruta)[nombre]


def _tabla_resumen(hoja):
    """Filas de datos de la hoja Resumen (después de la fila de títulos)."""
    filas = list(hoja.iter_rows(values_only=True))
    inicio = next(i for i, f in enumerate(filas) if f[0] == "No.")
    return filas[inicio], filas[inicio + 1:]


def test_excel_resumen_excluye_oyentes_por_defecto(servicio, curso_con_datos, tmp_path):
    ruta = tmp_path / "curso.xlsx"
    r = exportar_curso(servicio, curso_con_datos.id, ruta)
    assert (r.alumnos, ruta.exists()) == (4, True)

    hoja = _hoja(ruta, "Resumen")
    assert hoja["A1"].value == "DISEÑO Y ANALISIS DE ALGORITMOS"
    assert "1510" in hoja["A2"].value and "2027-I" in hoja["A2"].value
    titulos, datos = _tabla_resumen(hoja)
    assert titulos == ("No.", "Cuenta", "Nombre", "Décimas", "Participaciones", "Última")
    assert [f[2] for f in datos] == sorted(f[2] for f in datos)  # orden alfabético
    assert all("OYENTE" not in f[2] for f in datos)
    abreu = next(f for f in datos if f[1] == "100000001")
    assert abreu[3] == 0 and abreu[4] == 3  # 10, +5, -50 → piso de 0
    assert next(f for f in datos if f[1] == "100000002")[3] == 20
    assert isinstance(abreu[3], int)  # número real, no texto


def test_excel_incluir_oyentes_agrega_columna_tipo(servicio, curso_con_datos, tmp_path):
    ruta = tmp_path / "con_oyentes.xlsx"
    r = exportar_curso(servicio, curso_con_datos.id, ruta, incluir_oyentes=True)
    assert r.alumnos == 5
    titulos, datos = _tabla_resumen(_hoja(ruta, "Resumen"))
    assert titulos[-1] == "Tipo"
    oyente = next(f for f in datos if "OYENTE" in f[2])
    assert (oyente[1], oyente[3], oyente[-1]) in {(None, 7, "Oyente"), ("", 7, "Oyente")}


def test_excel_cuenta_se_guarda_como_texto_y_fecha_como_fecha(servicio, curso_con_datos, tmp_path):
    ruta = tmp_path / "formatos.xlsx"
    exportar_curso(servicio, curso_con_datos.id, ruta)
    hoja = _hoja(ruta, "Resumen")
    fila = next(r for r in hoja.iter_rows(min_row=7) if r[1].value == "100000001")
    assert isinstance(fila[1].value, str) and fila[1].number_format == "@"
    assert fila[5].value.date() == date.today() and fila[5].number_format == "DD/MM/YYYY"


def test_excel_hoja_de_detalle_con_efecto_real_y_total(servicio, curso_con_datos, tmp_path):
    ruta = tmp_path / "detalle.xlsx"
    r = exportar_curso(servicio, curso_con_datos.id, ruta)
    assert r.participaciones == 4  # 3 de Abreu + 1 de Acosta (el oyente no entra)
    filas = list(_hoja(ruta, "Participaciones").iter_rows(values_only=True))
    assert filas[0] == ("Cuenta", "Nombre", "Fecha", "Décimas", "Efecto real", "Total", "Nota")
    abreu = [f for f in filas[1:] if f[0] == "100000001"]
    assert [(f[3], f[4], f[5]) for f in abreu] == [(10, 10, 10), (5, 5, 15), (-50, -15, 0)]  # cronológico
    assert abreu[2][6] == "no entregó"


def test_excel_sin_detalle_no_crea_la_segunda_hoja(servicio, curso_con_datos, tmp_path):
    ruta = tmp_path / "sin_detalle.xlsx"
    exportar_curso(servicio, curso_con_datos.id, ruta, incluir_detalle=False)
    assert openpyxl.load_workbook(ruta).sheetnames == ["Resumen"]


def test_csv_resumen_con_acentos_y_bom(servicio, curso_con_datos, tmp_path):
    ruta = tmp_path / "curso.csv"
    r = exportar_curso(servicio, curso_con_datos.id, ruta)
    assert r.alumnos == 4
    assert ruta.read_bytes().startswith(b"\xef\xbb\xbf")  # Excel detecta UTF-8
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        filas = list(csv.reader(f))
    assert filas[0] == ["No.", "Cuenta", "Nombre", "Décimas", "Participaciones", "Última"]
    assert len(filas) == 5
    assert ["ABREU SOLANO MARCOS"] == [f[2] for f in filas[1:] if f[1] == "100000001"]
    assert next(f for f in filas[1:] if f[1] == "100000002")[3] == "20"


def test_decimales_se_exportan_como_numeros(servicio, curso_importado, tmp_path):
    servicio.registrar(curso_importado.id, "100000001", 2.5)
    ruta = tmp_path / "dec.xlsx"
    exportar_curso(servicio, curso_importado.id, ruta, incluir_detalle=False)
    _t, datos = _tabla_resumen(_hoja(ruta, "Resumen"))
    assert next(f for f in datos if f[1] == "100000001")[3] == 2.5


def test_errores_de_exportacion(servicio, curso_con_datos, curso, tmp_path):
    with pytest.raises(ErrorDominio, match="Formato"):
        exportar_curso(servicio, curso_con_datos.id, tmp_path / "x.pdf")
    with pytest.raises(ErrorDominio, match="no existe"):
        exportar_curso(servicio, 999, tmp_path / "x.xlsx")
    with pytest.raises(ErrorDominio, match="No hay alumnos"):
        exportar_curso(servicio, curso.id, tmp_path / "vacio.xlsx")  # curso sin alumnos


def test_archivo_abierto_en_excel_da_mensaje_claro(servicio, curso_con_datos, tmp_path, monkeypatch):
    def bloqueado(*_a, **_k):
        raise PermissionError("en uso")

    monkeypatch.setattr(openpyxl.Workbook, "save", bloqueado)
    with pytest.raises(ErrorDominio, match="abierto en Excel"):
        exportar_curso(servicio, curso_con_datos.id, tmp_path / "x.xlsx")


def test_carpeta_inexistente_da_error_de_dominio(servicio, curso_con_datos, tmp_path):
    with pytest.raises(ErrorDominio, match="No se pudo guardar"):
        exportar_curso(servicio, curso_con_datos.id, tmp_path / "no_existe" / "x.xlsx")


def test_nombre_sugerido_sin_caracteres_invalidos():
    c = Curso(1, "2027-I", "", 'ESTRUCTURAS: "A/B" ¿qué?', "1510")
    nombre = nombre_sugerido(c)
    assert nombre.endswith(".xlsx") and nombre.startswith("2027-I - 1510 - ")
    assert not any(ch in nombre for ch in r'<>:"/\|?*')
    assert nombre_sugerido(c, "csv").endswith(".csv")
