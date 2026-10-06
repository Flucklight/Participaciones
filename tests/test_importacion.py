import os
from pathlib import Path

import pytest

from core.errores import ErrorDominio, ErrorImportacion
from core.models import TipoInscripcion
from importers.lista_aragon import leer_lista
from tests.conftest import crear_excel

# Opcional: ruta de una lista de inscripción REAL para probar el importador con un archivo auténtico.
# No se versiona ningún dato real; define la variable en tu equipo para activarla:
#   $env:LISTA_REAL = "<ruta completa a tu lista .xlsx>"
LISTA_REAL = Path(os.environ["LISTA_REAL"]) if os.environ.get("LISTA_REAL") else None


# ---------- lectura del Excel ----------
def test_leer_lista_sintetica(tmp_path):
    ruta = crear_excel(
        tmp_path / "lista.xlsx",
        [(100000001, "  abreu   solano marcos "), ("100000002", "ACOSTA ORTEGA ELENA")],
    )
    lista = leer_lista(ruta)
    assert (lista.ciclo, lista.grupo) == ("2027-I", "1510")
    assert lista.materia == "DISEÑO Y ANALISIS DE ALGORITMOS"
    assert [(a.numero, a.num_cuenta, a.nombre_completo) for a in lista.alumnos] == [
        (1, "100000001", "ABREU SOLANO MARCOS"),
        (2, "100000002", "ACOSTA ORTEGA ELENA"),
    ]


def test_grupo_numerico_se_lee_como_texto(tmp_path):
    ruta = crear_excel(tmp_path / "l.xlsx", [("1", "A")], grupo=1510)
    assert leer_lista(ruta).grupo == "1510"


def test_sin_tabla_de_alumnos(tmp_path):
    ruta = crear_excel(tmp_path / "l.xlsx", [], con_titulos=False)
    with pytest.raises(ErrorImportacion):
        leer_lista(ruta)


def test_lista_sin_alumnos(tmp_path):
    with pytest.raises(ErrorImportacion):
        leer_lista(crear_excel(tmp_path / "l.xlsx", []))


def test_cuenta_invalida_o_repetida(tmp_path):
    with pytest.raises(ErrorImportacion):
        leer_lista(crear_excel(tmp_path / "a.xlsx", [("12ab", "X")]))
    with pytest.raises(ErrorImportacion):
        leer_lista(crear_excel(tmp_path / "b.xlsx", [("1", "X"), ("1", "Y")]))


def test_archivo_inexistente_o_invalido(tmp_path):
    with pytest.raises(ErrorImportacion):
        leer_lista(tmp_path / "no_existe.xlsx")
    falso = tmp_path / "falso.xlsx"
    falso.write_text("no soy un excel")
    with pytest.raises(ErrorImportacion):
        leer_lista(falso)


@pytest.mark.skipif(
    LISTA_REAL is None or not LISTA_REAL.exists(),
    reason="define la variable de entorno LISTA_REAL con la ruta de una lista real",
)
def test_lista_real_de_inscripcion(servicio):
    lista = leer_lista(LISTA_REAL)
    assert lista.ciclo and lista.materia and lista.grupo
    assert lista.alumnos
    assert all(a.num_cuenta.isdigit() and a.nombre_completo for a in lista.alumnos)
    resultado = servicio.importar_lista(lista)
    assert resultado.curso_creado and resultado.alumnos_creados == len(lista.alumnos)
    assert servicio.contar_alumnos(resultado.curso.id) == len(lista.alumnos)


# ---------- importación al sistema ----------
def test_importar_crea_curso_alumnos_e_inscripciones(servicio, lista):
    r = servicio.importar_lista(lista)
    assert r.curso_creado and (r.alumnos_creados, r.inscripciones_nuevas) == (4, 4)
    resumen = servicio.resumen_curso(r.curso.id)
    assert len(resumen) == 4 and all(f.tipo == TipoInscripcion.REGULAR for f in resumen)


def test_reimportar_no_duplica_ni_borra_participaciones(servicio, lista):
    r = servicio.importar_lista(lista)
    servicio.registrar(r.curso.id, "100000001", 10)
    r2 = servicio.importar_lista(lista)
    assert not r2.curso_creado and (r2.alumnos_creados, r2.inscripciones_nuevas) == (0, 0)
    assert len(servicio.listar_cursos()) == 1
    assert servicio.total_alumno(r.curso.id, servicio.registrar(r.curso.id, "100000001", 1).alumno.id) == 11


def test_reimportar_con_alumnos_nuevos_solo_agrega_los_nuevos(servicio, lista):
    from core.models import FilaLista
    servicio.importar_lista(lista)
    lista.alumnos.append(FilaLista(5, "100000099", "NUEVO ALUMNO"))
    r = servicio.importar_lista(lista)
    assert (r.alumnos_creados, r.inscripciones_nuevas) == (1, 1)


def test_alumno_existente_se_reutiliza_en_otro_curso(servicio, lista):
    servicio.importar_lista(lista)
    lista.grupo = "2000"
    r = servicio.importar_lista(lista)
    assert r.alumnos_creados == 0 and r.inscripciones_nuevas == 4
    assert len(servicio.listar_cursos()) == 2


def test_coincidencia_con_oyente_se_detecta_pero_no_se_fusiona_sola(servicio, curso, lista):
    oyente = servicio.crear_alumno_en_curso(curso.id, "abreu solano marcos")
    servicio.registrar_para_alumno(curso.id, oyente.id, 10)

    vista = servicio.previsualizar_importacion(lista)
    assert [(c.fila.num_cuenta, c.oyente.id) for c in vista.coincidencias_oyentes] == [
        ("100000001", oyente.id)
    ]
    servicio.importar_lista(lista)  # sin confirmación: se crea otro alumno
    assert servicio.obtener_alumno(oyente.id).num_cuenta is None


def test_vincular_oyente_confirmado_conserva_historial_y_pasa_a_regular(servicio, curso, lista):
    lista.materia, lista.grupo, lista.ciclo = curso.materia, curso.grupo, curso.ciclo
    oyente = servicio.crear_alumno_en_curso(curso.id, "Abreu Solano Marcos")
    servicio.registrar_para_alumno(curso.id, oyente.id, 10)

    r = servicio.importar_lista(lista, vinculos={"100000001": oyente.id})
    assert r.curso.id == curso.id and r.vinculados == 1 and r.alumnos_creados == 3
    assert servicio.obtener_alumno(oyente.id).num_cuenta == "100000001"
    fila = next(f for f in servicio.resumen_curso(curso.id) if f.alumno.id == oyente.id)
    assert fila.tipo == TipoInscripcion.REGULAR and fila.total == 10
    assert len(servicio.resumen_curso(curso.id)) == 4  # sin duplicados


def test_vinculo_invalido_revierte_toda_la_importacion(servicio, lista):
    with pytest.raises(ErrorDominio):
        servicio.importar_lista(lista, vinculos={"100000001": 9999})
    assert servicio.listar_cursos(incluir_archivados=True) == []
