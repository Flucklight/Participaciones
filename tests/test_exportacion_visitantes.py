"""Visitantes (R21): exportación del grupo que visita y del origen (datos ficticios)."""

import csv
from datetime import date
from types import SimpleNamespace

import pytest

from core.errores import ErrorDominio
from core.models import TipoInscripcion
from exporters.curso import exportar_curso
from tests.test_exportacion import _hoja, _tabla_resumen

REGULAR = TipoInscripcion.REGULAR
HOY = date(2027, 3, 1)


@pytest.fixture
def g(servicio):
    """Ana: regular en 3001 (con datos), visitante en 3002 donde Luis es regular."""
    a = servicio.crear_curso("2027-I", "Redes", "3001")
    b = servicio.crear_curso("2027-I", "Redes", "3002")
    ana = servicio.crear_alumno_en_curso(a.id, "Prueba Ana", REGULAR, "100000001")
    luis = servicio.crear_alumno_en_curso(b.id, "Prueba Luis", REGULAR, "100000002")
    servicio.inscribir_visitante(b.id, ana.id, a.id)
    servicio.establecer_ponderaciones(a.id, 10, 0, 20, 40)
    servicio.establecer_ponderaciones(b.id, 100, 0, 0, 0)
    servicio.registrar_para_alumno(b.id, ana.id, 5, HOY, "preguntó")
    servicio.establecer_tareas(b.id, ana.id, 80, HOY)
    servicio.registrar_para_alumno(b.id, luis.id, 2, HOY)
    return SimpleNamespace(a=a, b=b, ana=ana, luis=luis, srv=servicio)


def test_por_defecto_el_visitante_no_sale_del_grupo_que_visita(g, tmp_path):
    ruta = tmp_path / "b.xlsx"
    r = exportar_curso(g.srv, g.b.id, ruta)
    _t, datos = _tabla_resumen(_hoja(ruta, "Resumen"))
    assert r.alumnos == 1 and [f[2] for f in datos] == ["PRUEBA LUIS"]


def test_con_la_opcion_sale_como_visitante_con_los_numeros_del_origen(g, tmp_path):
    ruta = tmp_path / "b.xlsx"
    exportar_curso(g.srv, g.b.id, ruta, incluir_oyentes=True)
    titulos, datos = _tabla_resumen(_hoja(ruta, "Resumen"))
    por_nombre = {f[2]: f for f in datos}
    ana = por_nombre["PRUEBA ANA"]
    assert ana[titulos.index("Tipo")] == "Visitante"
    assert ana[titulos.index("Décimas")] == 5 and ana[titulos.index("Tareas")] == 80
    # la final es la del origen (10 % de 50 puntos + 20 % de 80), no la del grupo que visita (100 % de décimas)
    assert ana[titulos.index("Calificación final")] == 21
    assert por_nombre["PRUEBA LUIS"][titulos.index("Tipo")] == "Regular"
    assert por_nombre["PRUEBA LUIS"][titulos.index("Calificación final")] == 20  # 100 % de 20 puntos


def test_la_nota_aclara_las_ponderaciones_de_los_visitantes(g, tmp_path):
    ruta = tmp_path / "b.xlsx"
    exportar_curso(g.srv, g.b.id, ruta, incluir_oyentes=True)
    assert "visitantes usa las ponderaciones de su grupo de origen" in _hoja(ruta, "Resumen")["A5"].value
    sin = tmp_path / "sin.xlsx"
    exportar_curso(g.srv, g.b.id, sin)
    assert "visitantes" not in _hoja(sin, "Resumen")["A5"].value


def test_la_hoja_de_participaciones_trae_los_eventos_del_origen_con_su_nota(g, tmp_path):
    ruta = tmp_path / "b.xlsx"
    exportar_curso(g.srv, g.b.id, ruta, incluir_oyentes=True)
    filas = list(_hoja(ruta, "Participaciones").iter_rows(values_only=True))
    ana = [f for f in filas if f[1] == "PRUEBA ANA"]
    assert len(ana) == 1 and ana[0][6] == "Grupo 3002 · preguntó" and ana[0][7] == "Visitante"


def test_el_origen_exporta_al_alumno_como_regular_sin_cambios(g, tmp_path):
    ruta = tmp_path / "a.xlsx"
    exportar_curso(g.srv, g.a.id, ruta)
    titulos, datos = _tabla_resumen(_hoja(ruta, "Resumen"))
    assert [f[2] for f in datos] == ["PRUEBA ANA"] and "Tipo" not in titulos
    assert datos[0][titulos.index("Calificación final")] == 21
    assert "visitantes" not in _hoja(ruta, "Resumen")["A5"].value


def test_csv_con_visitante(g, tmp_path):
    ruta = tmp_path / "b.csv"
    exportar_curso(g.srv, g.b.id, ruta, incluir_oyentes=True)
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        filas = list(csv.reader(f))
    assert filas[0][-1] == "Tipo" and {r[-1] for r in filas[1:]} == {"Regular", "Visitante"}


def test_si_solo_hay_visitantes_el_aviso_los_menciona(servicio):
    a = servicio.crear_curso("2027-I", "Redes", "3001")
    b = servicio.crear_curso("2027-I", "Redes", "3002")
    ana = servicio.crear_alumno_en_curso(a.id, "Prueba Ana", REGULAR, "100000001")
    servicio.inscribir_visitante(b.id, ana.id, a.id)
    with pytest.raises(ErrorDominio, match="oyentes y visitantes"):
        exportar_curso(servicio, b.id, "no_importa.xlsx")


def test_las_columnas_de_examen_del_grupo_que_visita_llevan_la_nota_del_origen(g, tmp_path):
    ea, eb = g.srv.crear_examen(g.a.id, "Parcial 1"), g.srv.crear_examen(g.b.id, "Parcial 1")
    g.srv.establecer_calificacion(g.b.id, eb.id, g.ana.id, 70, HOY)
    ruta = tmp_path / "b.xlsx"
    exportar_curso(g.srv, g.b.id, ruta, incluir_oyentes=True)
    titulos, datos = _tabla_resumen(_hoja(ruta, "Resumen"))
    por_nombre = {f[2]: f for f in datos}
    assert por_nombre["PRUEBA ANA"][titulos.index("Examen - Parcial 1")] == 70
    assert por_nombre["PRUEBA LUIS"][titulos.index("Examen - Parcial 1")] == 0
