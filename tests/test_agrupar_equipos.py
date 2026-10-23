"""Agrupación de la tabla por equipo (función pura)."""

from core.models import Alumno, ResumenAlumno, TipoInscripcion
from ui_desktop.agrupar import agrupar_por_equipo, es_encabezado, iid_encabezado


def fila(id_, equipo):
    return ResumenAlumno(Alumno(id_, f"ALUMNO {id_}"), TipoInscripcion.REGULAR, 0.0, 0, None, equipo=equipo)


def grupos(*equipos):
    return agrupar_por_equipo([fila(i, e) for i, e in enumerate(equipos, start=1)])


def test_agrupa_por_numero_y_deja_sin_equipo_al_final():
    g = grupos(None, 2, 1, 2, None, 1)
    assert [x.numero for x in g] == [1, 2, None]
    assert [[f.alumno.id for f in x.filas] for x in g] == [[3, 6], [2, 4], [1, 5]]


def test_conserva_el_orden_recibido_dentro_de_cada_equipo():
    g = agrupar_por_equipo([fila(9, 1), fila(3, 1), fila(5, 1)])
    assert [f.alumno.id for f in g[0].filas] == [9, 3, 5]


def test_las_bandas_alternan_por_orden_de_aparicion_aunque_falten_numeros():
    g = grupos(1, 3, 7, None)  # los equipos 2, 4, 5 y 6 no tienen miembros visibles
    assert [x.banda for x in g] == [0, 1, 0, None]


def test_sin_filas_no_hay_grupos():
    assert agrupar_por_equipo([]) == []


def test_todos_sin_equipo_es_un_solo_grupo_sin_banda():
    g = grupos(None, None)
    assert len(g) == 1 and g[0].numero is None and g[0].banda is None


def test_titulo_en_singular_y_plural():
    g = grupos(1, 2, 2)
    assert g[0].titulo == "Equipo 1 · 1 alumno" and g[1].titulo == "Equipo 2 · 2 alumnos"


def test_los_encabezados_se_distinguen_de_los_alumnos():
    assert es_encabezado(iid_encabezado(3)) and not es_encabezado("42")


def test_el_titulo_incluye_nombre_y_proyecto_si_los_hay():
    filas = [fila(1, 1), fila(2, 1), fila(3, 2), fila(4, 3)]
    g = agrupar_por_equipo(filas, {1: ("Los Cuervos", "Sistema de riego"), 2: ("Solo nombre", ""), 3: ("", "Solo proyecto")})
    assert [x.titulo for x in g] == [
        "Equipo 1 · 2 alumnos · Los Cuervos · Sistema de riego",
        "Equipo 2 · 1 alumno · Solo nombre",
        "Equipo 3 · 1 alumno · Solo proyecto",
    ]


def test_sin_datos_el_titulo_es_el_de_siempre():
    g = agrupar_por_equipo([fila(1, 1)], {})
    assert g[0].titulo == "Equipo 1 · 1 alumno"


def test_el_numero_se_recupera_del_iid():
    from ui_desktop.agrupar import numero_de_encabezado

    assert numero_de_encabezado(iid_encabezado(12)) == 12
