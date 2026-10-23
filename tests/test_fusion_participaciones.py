"""Fusionar (T6): participaciones como eventos; las idénticas a las locales las decide la persona."""

import pytest

from tests.fusion import D1, D2, alumno, lista, poblar_completo, servicio


@pytest.fixture
def bases(tmp_path):
    laptop, c1 = servicio(tmp_path / "laptop.db")
    poblar_completo(laptop)
    laptop.exportar_base(tmp_path / "viaje.db")
    aqui, c2 = servicio(tmp_path / "aqui.db")
    yield laptop, aqui, tmp_path
    c1.close()
    c2.close()


def _historial(srv, curso, cuenta):
    return sorted((p.fecha, p.decimas, p.nota) for p in srv.historial(curso.id, alumno(srv, curso, cuenta).id))


def test_las_participaciones_distintas_se_agregan_y_las_identicas_las_elige_la_persona(bases):
    _, aqui, tmp = bases
    curso = aqui.importar_lista(lista()).curso
    a = alumno(aqui, curso, "100000001")
    aqui.registrar_para_alumno(curso.id, a.id, 8, D1)  # idéntica a una del archivo
    aqui.registrar_para_alumno(curso.id, a.id, 2, D2)  # propia
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    assert plan.agregan["participaciones"] == 1  # solo la de -3 es nueva
    assert [d.cantidad for d in plan.duplicados] == [1]


def test_por_omision_se_descartan_las_importadas_que_ya_estaban(bases):
    _, aqui, tmp = bases
    curso = aqui.importar_lista(lista()).curso
    a = alumno(aqui, curso, "100000001")
    aqui.registrar_para_alumno(curso.id, a.id, 8, D1)
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    assert _historial(aqui, curso, "100000001") == [(D1, 8, ""), (D2, -3, "corrección")]


def test_mantener_ambas_conserva_las_dos(bases):
    _, aqui, tmp = bases
    curso = aqui.importar_lista(lista()).curso
    a = alumno(aqui, curso, "100000001")
    aqui.registrar_para_alumno(curso.id, a.id, 8, D1)
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp", mantener_ambas=frozenset(d.id for d in plan.duplicados))
    assert _historial(aqui, curso, "100000001") == [(D1, 8, ""), (D1, 8, ""), (D2, -3, "corrección")]


def test_el_total_se_recalcula_con_el_minimo_de_cero(bases):
    _, aqui, tmp = bases
    curso = aqui.importar_lista(lista()).curso
    a = alumno(aqui, curso, "100000001")
    aqui.registrar_para_alumno(curso.id, a.id, 2, D1)
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")  # +2 y +8 (D1), -3 (D2) en orden cronológico
    assert aqui.total_alumno(curso.id, a.id) == 7
