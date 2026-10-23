"""Fusionar (T7): aplicar es idempotente, atómico, no borra nada local y se puede deshacer."""

import pytest

from core.errores import ErrorDominio
from tests.fusion import D1, alumno, foto, lista, poblar_completo, servicio


@pytest.fixture
def bases(tmp_path):
    laptop, c1 = servicio(tmp_path / "laptop.db")
    poblar_completo(laptop)
    laptop.exportar_base(tmp_path / "viaje.db")
    aqui, c2 = servicio(tmp_path / "aqui.db")
    yield laptop, aqui, tmp_path
    c1.close()
    c2.close()


def test_fusionar_en_una_base_vacia_deja_una_copia_fiel(bases):
    laptop, aqui, tmp = bases
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    assert foto(aqui) == foto(laptop)


def test_reimportar_el_mismo_archivo_no_cambia_nada_la_segunda_vez(bases):
    _, aqui, tmp = bases
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    despues_de_una = foto(aqui)
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    assert plan.total_agregan == 0 and not plan.conflictos and plan.omitidos == 0
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    assert foto(aqui) == despues_de_una


def test_no_borra_nada_de_lo_local(bases):
    _, aqui, tmp = bases
    otro = aqui.importar_lista(lista("BASES", "2002", (("100000009", "OTRO ALUMNO"),))).curso
    aqui.registrar_para_alumno(otro.id, alumno(aqui, otro, "100000009").id, 4, D1)
    antes = foto(aqui)
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    despues = foto(aqui)
    clave = ("2027-I", "BASES", "2002")
    assert despues[clave] == antes[clave]
    assert len(despues) == 2


def test_los_ids_distintos_no_confunden_a_los_alumnos(bases):
    laptop, aqui, tmp = bases
    aqui.importar_lista(lista("OTRA", "1111", (("100000008", "ALUMNO UNO"), ("100000007", "ALUMNO DOS"))))
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    assert foto(aqui)[("2027-I", "REDES", "3001")] == foto(laptop)[("2027-I", "REDES", "3001")]


def test_una_falla_a_mitad_no_deja_cambios(bases, monkeypatch):
    _, aqui, tmp = bases
    aqui.importar_lista(lista("BASES", "2002", (("100000009", "OTRO ALUMNO"),)))
    antes = foto(aqui)

    def falla(*args, **kwargs):
        raise RuntimeError("falla simulada")

    monkeypatch.setattr(type(aqui._repo), "guardar_tareas", falla)
    with pytest.raises(RuntimeError):
        aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    monkeypatch.undo()
    assert foto(aqui) == antes
    assert not aqui.hay_importacion_por_deshacer


def test_deshacer_importacion_restaura_la_base_de_antes_de_fusionar(bases):
    _, aqui, tmp = bases
    aqui.importar_lista(lista("BASES", "2002", (("100000009", "OTRO ALUMNO"),)))
    antes = foto(aqui)
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    assert foto(aqui) != antes
    aqui.deshacer_importacion()
    assert foto(aqui) == antes


def test_un_archivo_invalido_no_se_fusiona(bases):
    _, aqui, tmp = bases
    malo = tmp / "malo.db"
    malo.write_text("no soy una base " * 40)
    with pytest.raises(ErrorDominio):
        aqui.fusionar_base(malo, tmp / "resp")
    assert not (tmp / "resp").exists()


def test_el_archivo_importado_no_cambia(bases):
    _, aqui, tmp = bases
    antes = (tmp / "viaje.db").read_bytes()
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    assert (tmp / "viaje.db").read_bytes() == antes
