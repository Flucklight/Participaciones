"""Fusionar (T6): equipos nuevos se agregan; con miembros distintos son un conflicto a elegir."""

import pytest

from tests.fusion import alumno, lista, poblar_completo, servicio


@pytest.fixture
def bases(tmp_path):
    laptop, c1 = servicio(tmp_path / "laptop.db")
    poblar_completo(laptop)
    laptop.exportar_base(tmp_path / "viaje.db")
    aqui, c2 = servicio(tmp_path / "aqui.db")
    yield laptop, aqui, tmp_path
    c1.close()
    c2.close()


def test_un_equipo_nuevo_se_agrega_con_nombre_proyecto_y_miembros(bases):
    _, aqui, tmp = bases
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    curso = aqui.listar_cursos()[0]
    (equipo,) = aqui.equipos_del_curso(curso.id)
    assert (equipo.numero, equipo.nombre, equipo.proyecto) == (1, "Los redes", "Proyecto X")
    assert len(aqui.resumen_curso(curso.id)) == 2
    assert {f.equipo for f in aqui.resumen_curso(curso.id)} == {1}


def test_el_mismo_equipo_en_ambas_bases_no_es_conflicto(bases):
    _, aqui, tmp = bases
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    assert not plan.conflictos and "equipos" not in plan.agregan


def test_miembros_distintos_con_el_mismo_numero_son_conflicto_y_por_omision_gana_lo_local(bases):
    _, aqui, tmp = bases
    curso = aqui.importar_lista(lista()).curso
    a = alumno(aqui, curso, "100000001")
    aqui.formar_equipo(curso.id, [a.id], "Solo yo", "")  # el equipo 1 de aquí tiene otro miembro
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    (conflicto,) = [c for c in plan.conflictos if c.entidad == "Equipo"]
    assert "Solo yo" in conflicto.antes and "Los redes" in conflicto.despues
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    assert [e.nombre for e in aqui.equipos_del_curso(curso.id)] == ["Solo yo"]
    assert aqui.equipo_de(curso.id, alumno(aqui, curso, "100000002").id) is None


def test_al_elegir_el_equipo_importado_se_reemplaza_su_nombre_y_miembros(bases):
    _, aqui, tmp = bases
    curso = aqui.importar_lista(lista()).curso
    a, b = alumno(aqui, curso, "100000001"), alumno(aqui, curso, "100000002")
    aqui.formar_equipo(curso.id, [a.id], "Solo yo", "")
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp", usar_importado=frozenset(c.id for c in plan.conflictos))
    assert [e.nombre for e in aqui.equipos_del_curso(curso.id)] == ["Los redes"]
    assert aqui.equipo_de(curso.id, a.id) == aqui.equipo_de(curso.id, b.id) == 1


def test_nunca_se_mueve_a_quien_ya_tiene_otro_equipo(bases):
    _, aqui, tmp = bases
    curso = aqui.importar_lista(lista()).curso
    a, b = alumno(aqui, curso, "100000001"), alumno(aqui, curso, "100000002")
    aqui.formar_equipo(curso.id, [b.id], "Del 1", "")
    aqui.formar_equipo(curso.id, [a.id], "Del 2", "")
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")  # el archivo: equipo 1 = a y b
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp", usar_importado=frozenset(c.id for c in plan.conflictos))
    assert aqui.equipo_de(curso.id, a.id) == 2  # sigue en el suyo
