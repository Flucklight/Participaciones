"""Exportación de la calificación final y de las ponderaciones usadas (datos ficticios)."""

import csv

import pytest

from core.models import TipoInscripcion
from exporters.curso import exportar_curso
from tests.test_exportacion import _hoja, _tabla_resumen


@pytest.fixture
def curso_con_final(servicio, curso_importado):
    """Abreu: 8 décimas, examen 70, tareas 90, proyecto 85 con 10/30/20/40 → 81. Acosta: nada."""
    cid = curso_importado.id
    servicio.establecer_ponderaciones(cid, 10, 30, 20, 40)
    servicio.registrar(cid, "100000001", 8)
    examen = servicio.crear_examen(cid, "Parcial 1")
    servicio.registrar_calificacion(cid, examen.id, "100000001", 70)
    servicio.registrar_tareas(cid, "100000001", 90)
    servicio.registrar_proyecto(cid, "100000001", 85)
    return curso_importado


def _exportar(servicio, curso, ruta, **kw):
    exportar_curso(servicio, curso.id, ruta, **kw)
    return ruta


def _columna(titulos, nombre):
    return titulos.index(nombre)


def test_la_columna_va_despues_de_los_examenes_y_su_promedio_y_antes_de_participaciones(servicio, curso_con_final, tmp_path):
    titulos, _d = _tabla_resumen(_hoja(_exportar(servicio, curso_con_final, tmp_path / "f.xlsx"), "Resumen"))
    assert titulos[3:] == ("Décimas", "Tareas", "Equipo", "Proyecto", "Examen - Parcial 1", "Promedio exámenes",
                           "Calificación final", "Participaciones", "Última")


def test_sin_examenes_va_justo_despues_de_proyecto(servicio, curso_importado, tmp_path):
    titulos, _d = _tabla_resumen(_hoja(_exportar(servicio, curso_importado, tmp_path / "f.xlsx"), "Resumen"))
    assert titulos[_columna(titulos, "Proyecto") + 1] == "Calificación final"


def test_el_valor_es_el_entero_redondeado_de_la_final(servicio, curso_con_final, tmp_path):
    titulos, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_con_final, tmp_path / "f.xlsx"), "Resumen"))
    por_cuenta = {f[1]: f for f in datos}
    i = _columna(titulos, "Calificación final")
    assert por_cuenta["100000001"][i] == 81 and isinstance(por_cuenta["100000001"][i], int)
    assert por_cuenta["100000002"][i] == 0


@pytest.mark.parametrize("tareas, esperado", [(87.5, 88), (87.49, 87), (0.5, 1), (2.5, 3)])
def test_se_redondea_la_mitad_hacia_arriba(servicio, curso_importado, tmp_path, tareas, esperado):
    servicio.establecer_ponderaciones(curso_importado.id, 0, 0, 100, 0)
    servicio.registrar_tareas(curso_importado.id, "100000001", tareas)
    titulos, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_importado, tmp_path / "f.xlsx"), "Resumen"))
    fila = next(f for f in datos if f[1] == "100000001")
    assert fila[_columna(titulos, "Calificación final")] == esperado


def test_refleja_ponderaciones_personalizadas_y_puntos_extra(servicio, curso_con_final, tmp_path):
    servicio.establecer_ponderaciones(curso_con_final.id, 10, 30, 20, 50)  # 110 %
    titulos, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_con_final, tmp_path / "f.xlsx"), "Resumen"))
    fila = next(f for f in datos if f[1] == "100000001")
    assert fila[_columna(titulos, "Calificación final")] == 90  # 81 + 10 % de 85 = 89.5 → 90


def test_con_las_ponderaciones_de_omision_los_examenes_no_pesan(servicio, curso_importado, tmp_path):
    cid = curso_importado.id
    servicio.registrar(cid, "100000001", 8)
    examen = servicio.crear_examen(cid, "Parcial 1")
    servicio.registrar_calificacion(cid, examen.id, "100000001", 100)
    titulos, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_importado, tmp_path / "f.xlsx"), "Resumen"))
    fila = next(f for f in datos if f[1] == "100000001")
    assert fila[_columna(titulos, "Calificación final")] == 8  # solo el 10 % de 80 puntos


def test_el_xlsx_indica_las_ponderaciones_usadas(servicio, curso_con_final, tmp_path):
    hoja = _hoja(_exportar(servicio, curso_con_final, tmp_path / "f.xlsx"), "Resumen")
    assert hoja["A5"].value == "Ponderaciones: participaciones 10 % · exámenes 30 % · tareas 20 % · proyecto 40 %"


def test_la_linea_de_ponderaciones_muestra_decimales_y_los_valores_de_omision(servicio, curso_importado, tmp_path):
    hoja = _hoja(_exportar(servicio, curso_importado, tmp_path / "a.xlsx"), "Resumen")
    assert hoja["A5"].value == "Ponderaciones: participaciones 10 % · exámenes 0 % · tareas 20 % · proyecto 40 %"
    servicio.establecer_ponderaciones(curso_importado.id, 12.5, 30, 17.25, 40.125)
    hoja = _hoja(_exportar(servicio, curso_importado, tmp_path / "b.xlsx"), "Resumen")
    assert hoja["A5"].value == "Ponderaciones: participaciones 12.5 % · exámenes 30 % · tareas 17.25 % · proyecto 40.12 %"


def test_el_csv_trae_la_columna_pero_no_la_linea_de_ponderaciones(servicio, curso_con_final, tmp_path):
    ruta = _exportar(servicio, curso_con_final, tmp_path / "f.csv")
    texto = ruta.read_text(encoding="utf-8-sig")
    assert "Ponderaciones" not in texto
    filas = list(csv.reader(texto.splitlines()))
    i = filas[0].index("Calificación final")
    assert {f[1]: f[i] for f in filas[1:]}["100000001"] == "81"


def test_los_oyentes_siguen_excluidos_por_defecto_y_con_tipo_tienen_su_final(servicio, curso_con_final, tmp_path):
    oyente = servicio.crear_alumno_en_curso(curso_con_final.id, "ZETA OYENTE", TipoInscripcion.OYENTE)
    servicio.registrar_tareas_para_alumno(curso_con_final.id, oyente.id, 50)
    _t, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_con_final, tmp_path / "a.xlsx"), "Resumen"))
    assert all("OYENTE" not in f[2] for f in datos)
    titulos, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_con_final, tmp_path / "b.xlsx", incluir_oyentes=True), "Resumen"))
    fila = next(f for f in datos if "OYENTE" in f[2])
    assert fila[_columna(titulos, "Calificación final")] == 10 and titulos[-1] == "Tipo"


def test_exportar_no_modifica_nada(servicio, curso_con_final, tmp_path):
    antes = [(r.total, r.prom_examenes, r.tareas, r.proyecto, r.final) for r in servicio.resumen_curso(curso_con_final.id)]
    _exportar(servicio, curso_con_final, tmp_path / "f.xlsx")
    despues = [(r.total, r.prom_examenes, r.tareas, r.proyecto, r.final) for r in servicio.resumen_curso(curso_con_final.id)]
    assert antes == despues
