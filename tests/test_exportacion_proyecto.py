"""Exportación de «Equipo» y «Proyecto», y el diálogo de eliminar curso con proyectos (datos ficticios)."""

import csv

import pytest

from exporters.curso import exportar_curso
from tests.conftest import buscar_dialogo as _dialogo, hay_pantalla
from tests.test_exportacion import _hoja, _tabla_resumen
from tests.test_equipos import ids


@pytest.fixture
def curso_con_proyecto(servicio, curso_importado):
    """Equipo 1 (Abreu y Acosta, con proyecto 9.5), García López sola con proyecto individual, sin equipo."""
    cid = curso_importado.id
    n = ids(servicio, curso_importado)
    servicio.formar_equipo(cid, [n["100000001"], n["100000002"]])
    servicio.registrar_proyecto(cid, "equipo 1", 9.5)
    servicio.registrar_proyecto(cid, "100000003", 7)  # sin equipo
    return curso_importado


def _exportar(servicio, curso, ruta, **kw):
    exportar_curso(servicio, curso.id, ruta, **kw)
    return ruta


def test_excel_trae_equipo_y_proyecto_despues_de_tareas(servicio, curso_con_proyecto, tmp_path):
    titulos, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_con_proyecto, tmp_path / "p.xlsx"), "Resumen"))
    assert titulos[:9] == ("No.", "Cuenta", "Nombre", "Décimas", "Tareas", "Equipo", "Proyecto", "Participaciones", "Última")
    por_cuenta = {f[1]: f for f in datos}
    assert (por_cuenta["100000001"][5], por_cuenta["100000001"][6]) == (1, 9.5)
    assert (por_cuenta["100000002"][5], por_cuenta["100000002"][6]) == (1, 9.5)


def test_sin_equipo_el_campo_va_vacio_y_sin_captura_el_proyecto_vale_0(servicio, curso_con_proyecto, tmp_path):
    _t, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_con_proyecto, tmp_path / "p.xlsx"), "Resumen"))
    por_cuenta = {f[1]: f for f in datos}
    assert por_cuenta["100000003"][5] in (None, "") and por_cuenta["100000003"][6] == 7
    assert por_cuenta["100000004"][5] in (None, "") and por_cuenta["100000004"][6] == 0


def test_equipo_y_proyecto_son_numeros_no_texto(servicio, curso_con_proyecto, tmp_path):
    _t, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_con_proyecto, tmp_path / "p.xlsx"), "Resumen"))
    assert all(isinstance(f[6], (int, float)) for f in datos)
    assert all(f[5] in (None, "") or isinstance(f[5], int) for f in datos)


def test_csv_trae_equipo_y_proyecto(servicio, curso_con_proyecto, tmp_path):
    ruta = _exportar(servicio, curso_con_proyecto, tmp_path / "p.csv")
    filas = list(csv.reader(ruta.read_text(encoding="utf-8-sig").splitlines()))
    assert filas[0][3:8] == ["Décimas", "Tareas", "Equipo", "Proyecto", "Participaciones"]
    por_cuenta = {f[1]: f for f in filas[1:]}
    assert por_cuenta["100000001"][5:7] == ["1", "9.5"]
    assert por_cuenta["100000003"][5:7] == ["", "7"]
    assert por_cuenta["100000004"][5:7] == ["", "0"]


def test_con_examenes_el_proyecto_va_antes_de_las_columnas_de_examen(servicio, curso_con_proyecto, tmp_path):
    servicio.crear_examen(curso_con_proyecto.id, "Parcial 1")
    titulos, _d = _tabla_resumen(_hoja(_exportar(servicio, curso_con_proyecto, tmp_path / "p.xlsx"), "Resumen"))
    assert titulos[3:9] == ("Décimas", "Tareas", "Equipo", "Proyecto", "Examen - Parcial 1", "Promedio exámenes")


def test_los_oyentes_se_excluyen_por_defecto_y_con_tipo_conservan_su_equipo(servicio, curso_con_proyecto, tmp_path):
    oyente = servicio.crear_alumno_en_curso(curso_con_proyecto.id, "ZETA OYENTE")
    servicio.formar_equipo(curso_con_proyecto.id, [oyente.id])  # equipo 2
    servicio.registrar_proyecto(curso_con_proyecto.id, "equipo 2", 8)
    _t, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_con_proyecto, tmp_path / "a.xlsx"), "Resumen"))
    assert all("OYENTE" not in f[2] for f in datos)
    titulos, datos = _tabla_resumen(_hoja(
        _exportar(servicio, curso_con_proyecto, tmp_path / "b.xlsx", incluir_oyentes=True), "Resumen"))
    fila = next(f for f in datos if "OYENTE" in f[2])
    assert (fila[5], fila[6], fila[-1]) == (2, 8, "Oyente") and titulos[-1] == "Tipo"


def test_curso_sin_datos_exporta_proyecto_0_y_equipo_vacio(servicio, curso_importado, tmp_path):
    _t, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_importado, tmp_path / "v.xlsx"), "Resumen"))
    assert all(f[6] == 0 and f[5] in (None, "") for f in datos)


def test_el_proyecto_no_cambia_el_promedio_de_examenes_ni_tareas_exportados(servicio, curso_con_proyecto, tmp_path):
    servicio.registrar_tareas(curso_con_proyecto.id, "100000001", 84.5)
    examen = servicio.crear_examen(curso_con_proyecto.id, "Parcial 1")
    servicio.registrar_calificacion(curso_con_proyecto.id, examen.id, "100000001", 42)
    _t, datos = _tabla_resumen(_hoja(_exportar(servicio, curso_con_proyecto, tmp_path / "p.xlsx"), "Resumen"))
    abreu = next(f for f in datos if f[1] == "100000001")
    assert (abreu[4], abreu[7], abreu[8]) == (84.5, 42, 42)  # tareas, examen, promedio de exámenes


# ---------------- diálogo de eliminar curso ----------------
@pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")
@pytest.mark.parametrize("cuantos, texto", [(1, "1 calificación de proyecto"), (2, "2 calificaciones de proyecto")])
def test_eliminar_curso_con_solo_proyecto_lo_dice_y_exige_confirmar(ui, cuantos, texto):
    app, srv, vista = ui.app, ui.srv, ui.vista
    curso = srv.crear_curso("2027-I", "Redes", "3001")
    for i in range(cuantos):
        alumno = srv.crear_alumno_en_curso(curso.id, f"OYENTE NUMERO {i}")
        srv.registrar_proyecto_para_alumno(curso.id, alumno.id, 88)  # sin participaciones, exámenes ni tareas
    vista.recargar()
    vista._seleccionar(curso.id)
    vistos = []

    def mirar():
        d = _dialogo(app)
        vistos.append((d._detalle.cget("text"), str(d._ok.cget("state"))))
        d.cancelar()

    app.after(300, mirar)
    vista.eliminar_seleccionado()
    detalle, estado = vistos[0]
    assert texto in detalle and estado == "disabled"
    assert curso.id in {c.id for c in srv.listar_cursos(True)}  # cancelado: sigue ahí
