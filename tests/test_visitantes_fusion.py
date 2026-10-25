"""Visitantes (R21): exportar, reemplazar y fusionar la base con visitas (datos ficticios)."""

from datetime import date

import pytest

from core.models import TipoInscripcion
from tests.fusion import foto, servicio

REGULAR, OYENTE, VISITANTE = TipoInscripcion.REGULAR, TipoInscripcion.OYENTE, TipoInscripcion.VISITANTE
HOY = date(2027, 3, 1)


def poblar(srv):
    """3001 (origen) con Ana y Beto; 3002 con Luis y Ana de visitante, con equipo y datos capturados desde la visita."""
    a = srv.crear_curso("2027-I", "REDES", "3001")
    b = srv.crear_curso("2027-I", "REDES", "3002")
    ana = srv.crear_alumno_en_curso(a.id, "Prueba Ana", REGULAR, "100000001")
    srv.crear_alumno_en_curso(a.id, "Prueba Beto", REGULAR, "100000003")
    luis = srv.crear_alumno_en_curso(b.id, "Prueba Luis", REGULAR, "100000002")
    srv.inscribir_visitante(b.id, ana.id, a.id)
    srv.crear_examen(a.id, "Parcial 1")
    eb = srv.crear_examen(b.id, "Parcial 1")
    srv.registrar_para_alumno(b.id, ana.id, 5, HOY)
    srv.registrar_calificacion_para_alumno(b.id, eb.id, ana.id, 8.5, HOY)
    srv.establecer_tareas(b.id, ana.id, 90, HOY)
    srv.formar_equipo(b.id, [ana.id, luis.id], "Los redes", "Proyecto X")
    srv.registrar_proyecto_equipo(b.id, 1, 80, HOY)
    return a, b, ana


@pytest.fixture
def bases(tmp_path):
    laptop, c1 = servicio(tmp_path / "laptop.db")
    poblar(laptop)
    laptop.exportar_base(tmp_path / "viaje.db")
    aqui, c2 = servicio(tmp_path / "aqui.db")
    yield laptop, aqui, tmp_path
    c1.close()
    c2.close()


def tipos(srv, grupo):
    curso = next(c for c in srv.listar_cursos(True) if c.grupo == grupo)
    return {f.alumno.num_cuenta: (f.tipo, f.curso_origen_id) for f in srv.resumen_curso(curso.id)}


def test_exportar_conserva_las_visitas(bases):
    laptop, aqui, tmp = bases
    assert laptop.resumen_base_archivo(tmp / "viaje.db") == laptop.resumen_base_local()
    aqui.reemplazar_base(tmp / "viaje.db", tmp / "resp")
    assert foto(aqui) == foto(laptop)
    visita = tipos(aqui, "3002")["100000001"]
    assert visita[0] == VISITANTE and visita[1] is not None


def test_fusionar_en_una_base_vacia_deja_una_copia_fiel(bases):
    laptop, aqui, tmp = bases
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    assert not plan.conflictos and plan.avisos == [] and plan.omitidos == 0
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    assert foto(aqui) == foto(laptop)
    tipo, origen = tipos(aqui, "3002")["100000001"]
    assert tipo == VISITANTE
    assert aqui.curso_de_datos(next(c.id for c in aqui.listar_cursos() if c.grupo == "3002"),
                               aqui.buscar_alumnos_en_curso(origen, "100000001")[0].id).grupo == "3001"


def test_reimportar_el_mismo_archivo_no_cambia_nada(bases):
    _, aqui, tmp = bases
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    despues_de_una = foto(aqui)
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    assert plan.total_agregan == 0 and not plan.conflictos and plan.omitidos == 0
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    assert foto(aqui) == despues_de_una


def test_los_datos_de_la_visita_no_se_duplican_al_fusionar(bases):
    _, aqui, tmp = bases
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    b = next(c for c in aqui.listar_cursos() if c.grupo == "3002")
    ana = aqui.buscar_alumnos_en_curso(b.id, "100000001")[0]
    assert len(aqui.historial(b.id, ana.id)) == 1
    con = aqui._repo.transaccion()
    assert con.execute("SELECT COUNT(*) FROM participacion WHERE curso_id = ?", (b.id,)).fetchone()[0] == 0


def test_un_origen_distinto_es_un_conflicto_y_por_omision_se_conserva_lo_local(bases):
    laptop, aqui, tmp = bases
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    # aquí, Ana visita el 3002 desde otro grupo (3003) en vez del 3001
    c = aqui.crear_curso("2027-I", "REDES", "3003")
    b = next(x for x in aqui.listar_cursos() if x.grupo == "3002")
    a = next(x for x in aqui.listar_cursos() if x.grupo == "3001")
    ana = aqui.buscar_alumnos_en_curso(a.id, "100000001")[0]
    aqui.eliminar_alumno_oyente(b.id, ana.id)
    aqui.inscribir_alumno_existente(c.id, ana.id, REGULAR)
    aqui.cambiar_tipo(c.id, ana.id, REGULAR)
    aqui.inscribir_visitante(b.id, ana.id, c.id)
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    conflicto, = [x for x in plan.conflictos if x.entidad == "Grupo de origen del visitante"]
    assert "3003" in conflicto.antes and "3001" in conflicto.despues
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")  # sin marcar nada: se conserva lo local
    assert tipos(aqui, "3002")["100000001"][1] == c.id
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp", usar_importado=frozenset({conflicto.id}))
    assert tipos(aqui, "3002")["100000001"][1] == a.id


def test_visitante_en_el_archivo_y_regular_aqui_se_conserva_lo_local_y_se_avisa(bases):
    _, aqui, tmp = bases
    b = aqui.crear_curso("2027-I", "REDES", "3002")
    aqui.crear_alumno_en_curso(b.id, "Prueba Ana", REGULAR, "100000001")
    plan = aqui.previsualizar_fusion(tmp / "viaje.db")
    assert any("ya está inscrito como regular" in x for x in plan.avisos)
    aqui.fusionar_base(tmp / "viaje.db", tmp / "resp")
    assert tipos(aqui, "3002")["100000001"][0] == REGULAR


def test_regular_en_el_archivo_y_visitante_aqui_se_conserva_lo_local_y_se_avisa(tmp_path):
    otro, c1 = servicio(tmp_path / "otro.db")
    b = otro.crear_curso("2027-I", "REDES", "3002")
    otro.crear_alumno_en_curso(b.id, "Prueba Ana", REGULAR, "100000001")
    otro.exportar_base(tmp_path / "viaje.db")
    aqui, c2 = servicio(tmp_path / "aqui.db")
    poblar(aqui)
    plan = aqui.previsualizar_fusion(tmp_path / "viaje.db")
    assert any("es visitante aquí" in x for x in plan.avisos)
    aqui.fusionar_base(tmp_path / "viaje.db", tmp_path / "resp")
    assert tipos(aqui, "3002")["100000001"][0] == VISITANTE
    c1.close()
    c2.close()


def test_fusionar_sobre_una_base_que_ya_tiene_los_grupos_agrega_la_visita(tmp_path):
    laptop, c1 = servicio(tmp_path / "laptop.db")
    poblar(laptop)
    laptop.exportar_base(tmp_path / "viaje.db")
    aqui, c2 = servicio(tmp_path / "aqui.db")
    a = aqui.crear_curso("2027-I", "REDES", "3001")
    b = aqui.crear_curso("2027-I", "REDES", "3002")
    aqui.crear_alumno_en_curso(a.id, "Prueba Ana", REGULAR, "100000001")
    aqui.crear_alumno_en_curso(b.id, "Prueba Luis", REGULAR, "100000002")
    resultado = aqui.fusionar_base(tmp_path / "viaje.db", tmp_path / "resp")
    assert tipos(aqui, "3002")["100000001"][0] == VISITANTE
    assert resultado.omitidos == 0
    assert foto(aqui) == foto(laptop)
    c1.close()
    c2.close()


def test_una_visita_cuyo_origen_quedo_como_oyente_no_se_crea(tmp_path):
    laptop, c1 = servicio(tmp_path / "laptop.db")
    poblar(laptop)
    laptop.exportar_base(tmp_path / "viaje.db")
    aqui, c2 = servicio(tmp_path / "aqui.db")
    a = aqui.crear_curso("2027-I", "REDES", "3001")
    aqui.crear_alumno_en_curso(a.id, "Prueba Ana", OYENTE, "100000001")  # aquí es oyente en el origen
    resultado = aqui.fusionar_base(tmp_path / "viaje.db", tmp_path / "resp")  # lo local se conserva
    b = next(c for c in aqui.listar_cursos() if c.grupo == "3002")
    assert "100000001" not in tipos(aqui, "3002")
    assert aqui._repo.equipo_de(b.id, aqui.buscar_alumnos_en_curso(a.id, "100000001")[0].id) is None
    assert resultado.omitidos >= 1
    c1.close()
    c2.close()


def test_un_archivo_anterior_a_las_visitas_se_acepta(tmp_path):
    from tests.test_visitantes import _base_vieja

    ruta = _base_vieja(tmp_path / "vieja.db")
    aqui, c = servicio(tmp_path / "aqui.db")
    resumen = aqui.resumen_base_archivo(ruta)
    assert resumen.cursos == 1
    aqui.fusionar_base(ruta, tmp_path / "resp")
    assert len(aqui.listar_cursos()) == 1
    c.close()
