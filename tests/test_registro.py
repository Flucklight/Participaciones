from datetime import date

import pytest

from core.errores import ErrorDominio
from core.models import EstadoRegistro, TipoInscripcion


def test_registrar_por_numero_de_cuenta_suma_y_reporta_total(servicio, curso_importado):
    r1 = servicio.registrar(curso_importado.id, "100000001", 10)
    assert r1.estado == EstadoRegistro.GUARDADO
    assert r1.alumno.nombre_completo == "ABREU SOLANO MARCOS"
    assert (r1.decimas, r1.total) == (10, 10)
    r2 = servicio.registrar(curso_importado.id, "100000001", 5)
    assert (r2.decimas, r2.total) == (5, 15)


def test_registrar_por_nombre_ignora_acentos_mayusculas_y_orden(servicio, curso_importado):
    r = servicio.registrar(curso_importado.id, "solano  abreu", 10)
    assert r.estado == EstadoRegistro.GUARDADO
    assert r.alumno.num_cuenta == "100000001"


def test_registrar_por_nombre_parcial(servicio, curso_importado):
    r = servicio.registrar(curso_importado.id, "acosta ort", 5)
    assert r.alumno.num_cuenta == "100000002"


def test_decimas_negativas_restan(servicio, curso_importado):
    servicio.registrar(curso_importado.id, "100000001", 10)
    r = servicio.registrar(curso_importado.id, "100000001", -4)
    assert r.total == 6


def test_decimas_cero_o_invalidas_rechazadas(servicio, curso_importado):
    for valor in (0, float("nan"), float("inf"), "abc", None):
        with pytest.raises(ErrorDominio):
            servicio.registrar(curso_importado.id, "100000001", valor)


def test_consulta_vacia_rechazada(servicio, curso_importado):
    with pytest.raises(ErrorDominio):
        servicio.registrar(curso_importado.id, "   ", 10)


def test_ambiguo_no_adivina_y_no_guarda(servicio, curso_importado):
    r = servicio.registrar(curso_importado.id, "garcia ana", 10)
    assert r.estado == EstadoRegistro.AMBIGUO
    assert len(r.candidatos) == 2
    assert all(f.n_participaciones == 0 for f in servicio.resumen_curso(curso_importado.id))


def test_ambiguo_se_resuelve_con_nombre_exacto(servicio, curso_importado):
    r = servicio.registrar(curso_importado.id, "garcia perez ana", 10)
    assert r.estado == EstadoRegistro.GUARDADO
    assert r.alumno.num_cuenta == "100000004"


def test_no_existe_no_guarda_nada(servicio, curso_importado):
    r = servicio.registrar(curso_importado.id, "999999999", 10)
    assert r.estado == EstadoRegistro.NO_EXISTE
    r = servicio.registrar(curso_importado.id, "persona inexistente", 10)
    assert r.estado == EstadoRegistro.NO_EXISTE and r.candidatos == []
    assert all(f.n_participaciones == 0 for f in servicio.resumen_curso(curso_importado.id))


def test_no_existe_ofrece_alumnos_de_otros_cursos(servicio, curso_importado):
    otro = servicio.crear_curso("2027-II", "Otra materia", "1")
    r = servicio.registrar(otro.id, "100000001", 10)
    assert r.estado == EstadoRegistro.NO_EXISTE
    assert [a.num_cuenta for a in r.candidatos] == ["100000001"]
    servicio.inscribir_alumno_existente(otro.id, r.candidatos[0].id)
    assert servicio.registrar(otro.id, "100000001", 10).estado == EstadoRegistro.GUARDADO


def test_crear_oyente_sin_cuenta_y_registrar(servicio, curso_importado):
    r = servicio.registrar(curso_importado.id, "luis oyente", 10)
    assert r.estado == EstadoRegistro.NO_EXISTE
    oyente = servicio.crear_alumno_en_curso(curso_importado.id, "luis oyente", TipoInscripcion.OYENTE)
    assert oyente.num_cuenta is None
    r = servicio.registrar_para_alumno(curso_importado.id, oyente.id, 10)
    assert (r.alumno.nombre_completo, r.total) == ("LUIS OYENTE", 10)
    fila = next(f for f in servicio.resumen_curso(curso_importado.id) if f.alumno.id == oyente.id)
    assert fila.tipo == TipoInscripcion.OYENTE and fila.total == 10


def test_no_se_puede_crear_alumno_repetido_en_el_curso(servicio, curso_importado):
    with pytest.raises(ErrorDominio):
        servicio.crear_alumno_en_curso(curso_importado.id, "x", num_cuenta="100000001")


def test_cuenta_invalida_rechazada(servicio, curso):
    with pytest.raises(ErrorDominio):
        servicio.crear_alumno_en_curso(curso.id, "Nombre", num_cuenta="12ab")


def test_deshacer_quita_la_participacion(servicio, curso_importado):
    servicio.registrar(curso_importado.id, "100000001", 10)
    r = servicio.registrar(curso_importado.id, "100000001", 5)
    servicio.deshacer(r.participacion.id)
    assert servicio.total_alumno(curso_importado.id, r.alumno.id) == 10
    with pytest.raises(ErrorDominio):
        servicio.deshacer(r.participacion.id)


def test_historial_editar_y_fecha_anterior(servicio, curso_importado):
    r = servicio.registrar(curso_importado.id, "100000001", 10)
    aid = r.alumno.id
    servicio.agregar_participacion(curso_importado.id, aid, 5, date(2020, 1, 10), "dudas")
    historial = servicio.historial(curso_importado.id, aid)
    assert [p.decimas for p in historial] == [10, 5]  # más reciente primero
    servicio.editar_participacion(r.participacion.id, 20, date.today(), "corregido")
    assert servicio.total_alumno(curso_importado.id, aid) == 25
    assert servicio.historial(curso_importado.id, aid)[0].nota == "corregido"


def test_resumen_curso_incluye_alumnos_sin_participaciones(servicio, curso_importado):
    servicio.registrar(curso_importado.id, "100000001", 10)
    resumen = servicio.resumen_curso(curso_importado.id)
    assert len(resumen) == 4
    primero = next(f for f in resumen if f.alumno.num_cuenta == "100000001")
    assert (primero.total, primero.n_participaciones) == (10, 1)
    assert primero.ultima_fecha == date.today()


def test_cambiar_oyente_a_regular_conserva_historial(servicio, curso):
    oyente = servicio.crear_alumno_en_curso(curso.id, "Oyente")
    servicio.registrar_para_alumno(curso.id, oyente.id, 10)
    servicio.cambiar_tipo(curso.id, oyente.id, TipoInscripcion.REGULAR)
    fila = servicio.resumen_curso(curso.id)[0]
    assert fila.tipo == TipoInscripcion.REGULAR and fila.total == 10


def test_editar_alumno_asigna_cuenta_y_rechaza_duplicada(servicio, curso_importado):
    oyente = servicio.crear_alumno_en_curso(curso_importado.id, "Oyente")
    with pytest.raises(ErrorDominio):
        servicio.editar_alumno(oyente.id, "Oyente", "100000001")
    editado = servicio.editar_alumno(oyente.id, "Oyente Renombrado", "400000001")
    assert editado.num_cuenta == "400000001"
