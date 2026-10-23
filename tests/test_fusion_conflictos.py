"""Fusionar (T5): valores distintos son conflictos a elegir y los oyentes dudosos nunca se unen solos."""

import pytest

from core.models import TipoInscripcion
from tests.fusion import D1, alumno, lista, poblar_completo, servicio


@pytest.fixture
def bases(tmp_path):
    laptop, c1 = servicio(tmp_path / "laptop.db")
    poblar_completo(laptop)
    laptop.exportar_base(tmp_path / "viaje.db")
    aqui, c2 = servicio(tmp_path / "aqui.db")
    yield laptop, aqui, tmp_path
    c1.close()
    c2.close()


def _con_valores_distintos(aqui):
    curso = aqui.importar_lista(lista()).curso
    a, b = alumno(aqui, curso, "100000001"), alumno(aqui, curso, "100000002")
    aqui.establecer_tareas(curso.id, a.id, 5, D1)  # el archivo trae 9
    aqui.establecer_proyecto(curso.id, a.id, 8, D1)  # igual: no cuenta
    examen = aqui.crear_examen(curso.id, "Parcial 1")
    aqui.establecer_calificacion(curso.id, examen.id, a.id, 6, D1)  # el archivo trae 7.5
    aqui.establecer_ponderaciones(curso.id, 20, 20, 20, 40)  # el archivo trae 10/30/20/40
    aqui.cambiar_tipo(curso.id, b.id, TipoInscripcion.OYENTE)  # el archivo trae regular
    return curso


def test_los_valores_distintos_son_conflicto_y_los_iguales_no(bases):
    _, aqui, tmp = bases
    _con_valores_distintos(aqui)
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    por_entidad = {c.entidad: c for c in plan.conflictos}
    assert set(por_entidad) == {"Tareas", "Examen «Parcial 1»", "Ponderaciones", "Tipo de inscripción"}
    assert (por_entidad["Tareas"].antes, por_entidad["Tareas"].despues) == ("5", "9")
    examen = por_entidad["Examen «Parcial 1»"]
    assert (examen.antes, examen.despues) == ("6", "7.5")
    tipo = por_entidad["Tipo de inscripción"]
    assert (tipo.antes, tipo.despues) == ("oyente", "regular")


def test_sin_confirmar_no_se_sobrescribe_lo_local(bases):
    _, aqui, tmp = bases
    curso = _con_valores_distintos(aqui)
    a = alumno(aqui, curso, "100000001")
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    assert aqui.tareas_de(curso.id, a.id).puntos == 5
    assert aqui.ponderaciones_de(curso.id).participaciones == 20


def test_con_confirmacion_se_toma_el_valor_importado(bases):
    _, aqui, tmp = bases
    curso = _con_valores_distintos(aqui)
    a = alumno(aqui, curso, "100000001")
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    elegidos = frozenset(c.id for c in plan.conflictos if c.entidad in ("Tareas", "Ponderaciones"))
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp", usar_importado=elegidos)
    assert aqui.tareas_de(curso.id, a.id).puntos == 9
    assert aqui.ponderaciones_de(curso.id).participaciones == 10
    assert aqui.calificacion_de(aqui.listar_examenes(curso.id)[0].id, a.id).puntos == 6  # no elegido


def test_un_oyente_sin_cuenta_con_el_mismo_nombre_es_dudoso_y_no_se_une_solo(tmp_path):
    laptop, c1 = servicio(tmp_path / "l.db")
    curso_l = laptop.importar_lista(lista()).curso
    oy_l = laptop.crear_alumno_en_curso(curso_l.id, "Pérez  Gómez Juan")
    laptop.registrar_para_alumno(curso_l.id, oy_l.id, 4, D1)
    laptop.exportar_base(tmp_path / "viaje.db")
    aqui, c2 = servicio(tmp_path / "a.db")
    curso = aqui.importar_lista(lista()).curso
    oy = aqui.crear_alumno_en_curso(curso.id, "PEREZ GOMEZ JUAN")
    aqui.registrar_para_alumno(curso.id, oy.id, 1, D1)

    plan = aqui.previsualizar_fusion(tmp_path / "viaje.db")
    assert len(plan.dudosos) == 1 and not plan.dudosos[0].unir
    assert plan.omitidos == 1 and "alumnos" not in plan.agregan
    aqui.fusionar_base(tmp_path / "viaje.db", tmp_path / "resp")
    assert aqui.total_alumno(curso.id, oy.id) == 1  # no se fusionó ni se importó

    unir = frozenset({plan.dudosos[0].id})
    plan2 = aqui.previsualizar_fusion(tmp_path / "viaje.db", unir)
    assert plan2.dudosos[0].unir and plan2.omitidos == 0
    aqui.fusionar_base(tmp_path / "viaje.db", tmp_path / "resp", unir=unir)
    assert aqui.total_alumno(curso.id, oy.id) == 5  # +1 local y +4 importado, en un solo alumno
    assert len([f for f in aqui.resumen_curso(curso.id) if f.tipo == TipoInscripcion.OYENTE]) == 1
    c1.close()
    c2.close()


def test_unir_un_oyente_local_con_un_alumno_del_archivo_con_cuenta_le_asigna_la_cuenta(tmp_path):
    laptop, c1 = servicio(tmp_path / "l.db")
    laptop.importar_lista(lista(alumnos=(("100000001", "ABREU SOLANO MARCOS"), ("100000003", "PEREZ GOMEZ JUAN"))))
    laptop.exportar_base(tmp_path / "viaje.db")
    aqui, c2 = servicio(tmp_path / "a.db")
    curso = aqui.importar_lista(lista(alumnos=(("100000001", "ABREU SOLANO MARCOS"),))).curso
    oy = aqui.crear_alumno_en_curso(curso.id, "Perez Gomez Juan")
    plan = aqui.previsualizar_fusion(tmp_path / "viaje.db")
    unir = frozenset(d.id for d in plan.dudosos)
    aqui.fusionar_base(tmp_path / "viaje.db", tmp_path / "resp", unir=unir)
    assert aqui.obtener_alumno(oy.id).num_cuenta == "100000003"
    assert aqui.resumen_base_local().alumnos == 2
    c1.close()
    c2.close()
