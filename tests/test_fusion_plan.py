"""Fusionar (T4): lo que solo agrega y no cambia nada al previsualizar (R19; datos ficticios)."""

import pytest

from tests.fusion import alumno, curso_de, foto, lista, poblar_completo, servicio


@pytest.fixture
def bases(tmp_path):
    laptop, c1 = servicio(tmp_path / "laptop.db")
    poblar_completo(laptop)
    laptop.exportar_base(tmp_path / "viaje.db")
    aqui, c2 = servicio(tmp_path / "aqui.db")
    yield laptop, aqui, tmp_path
    c1.close()
    c2.close()


def test_en_una_base_vacia_todo_se_agrega(bases):
    _, aqui, tmp = bases
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    assert plan.agregan == {
        "cursos": 1, "alumnos": 2, "inscripciones": 2, "participaciones": 2, "exámenes": 1,
        "calificaciones": 1, "tareas": 1, "proyecto": 1, "ponderaciones": 1, "equipos": 1,
    }
    assert not plan.conflictos and not plan.duplicados and not plan.dudosos
    assert plan.omitidos == 0


def test_previsualizar_no_cambia_la_base_local(bases):
    _, aqui, tmp = bases
    aqui.importar_lista(lista("BASES", "2002", (("100000009", "OTRO ALUMNO"),)))
    antes = foto(aqui)
    aqui.previsualizar_fusion(tmp / "viaje.db")
    assert foto(aqui) == antes


def test_los_cursos_se_identifican_por_ciclo_materia_y_grupo_no_por_id(bases):
    _, aqui, tmp = bases
    aqui.importar_lista(lista("OTRA", "1111", (("100000008", "ALUMNO UNO"),)))  # ocupa el id 1 aquí
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    assert plan.agregan["cursos"] == 1 and plan.agregan["alumnos"] == 2


def test_un_curso_existente_se_reutiliza_y_solo_agrega_lo_que_falta(bases):
    _, aqui, tmp = bases
    curso = aqui.importar_lista(lista()).curso  # mismo curso y mismos alumnos, sin datos
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    assert "cursos" not in plan.agregan and "alumnos" not in plan.agregan
    assert plan.agregan["participaciones"] == 2 and plan.agregan["tareas"] == 1
    assert aqui.resumen_base_local().cursos == 1 and curso.id


def test_los_cursos_archivados_tambien_viajan_conservando_su_estado(bases):
    laptop, aqui, tmp = bases
    laptop.archivar_curso(curso_de(laptop).id)
    laptop.exportar_base(tmp / "archivado.db")
    plan = aqui.previsualizar_fusion(tmp / "archivado.db")
    assert plan.agregan["cursos"] == 1
    assert plan._cursos[0][2] is True
