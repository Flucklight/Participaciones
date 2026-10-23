from datetime import date

import pytest

from core.errores import ErrorDominio
from core.models import EstadoRegistro


@pytest.fixture
def parcial(servicio, curso_importado):
    return servicio.crear_examen(curso_importado.id, "Parcial 1")


def _alumno(servicio, curso, cuenta):
    return servicio._repo.buscar_alumno_en_curso_por_cuenta(curso.id, cuenta)


def test_registra_por_numero_de_cuenta(servicio, curso_importado, parcial):
    r = servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 42)
    assert r.estado == EstadoRegistro.GUARDADO
    assert r.alumno.nombre_completo == "ABREU SOLANO MARCOS"
    assert r.puntos == 42
    assert r.calificacion_anterior is None


def test_registra_por_nombre_parcial(servicio, curso_importado, parcial):
    r = servicio.registrar_calificacion(curso_importado.id, parcial.id, "acosta", 7.5)
    assert r.estado == EstadoRegistro.GUARDADO
    assert r.alumno.num_cuenta == "100000002"


def test_nombre_ambiguo_pide_elegir_y_no_guarda(servicio, curso_importado, parcial):
    r = servicio.registrar_calificacion(curso_importado.id, parcial.id, "garcia ana", 9)
    assert r.estado == EstadoRegistro.AMBIGUO
    assert len(r.candidatos) == 2
    assert servicio._repo.contar_calificaciones_examen(parcial.id) == 0


def test_alumno_inexistente(servicio, curso_importado, parcial):
    r = servicio.registrar_calificacion(curso_importado.id, parcial.id, "999999999", 9)
    assert r.estado == EstadoRegistro.NO_EXISTE
    assert servicio._repo.contar_calificaciones_examen(parcial.id) == 0


def test_cero_y_puntos_extra_son_validos(servicio, curso_importado, parcial):
    assert servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 0).estado == EstadoRegistro.GUARDADO
    r = servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000002", 115)
    assert r.estado == EstadoRegistro.GUARDADO and r.puntos == 115


@pytest.mark.parametrize("valor", [-1, float("nan"), float("inf"), "abc", None])
def test_calificacion_invalida_se_rechaza(servicio, curso_importado, parcial, valor):
    with pytest.raises(ErrorDominio):
        servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", valor)


def test_consulta_vacia_se_rechaza(servicio, curso_importado, parcial):
    with pytest.raises(ErrorDominio):
        servicio.registrar_calificacion(curso_importado.id, parcial.id, "  ", 5)


def test_examen_de_otro_curso_se_rechaza(servicio, curso_importado, parcial):
    otro = servicio.crear_curso("2027-I", "Redes", "1401")
    with pytest.raises(ErrorDominio):
        servicio.registrar_calificacion(otro.id, parcial.id, "100000001", 5)


def test_reemplazo_pide_confirmar_y_no_guarda(servicio, curso_importado, parcial):
    servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 35)
    r = servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 42)
    assert r.estado == EstadoRegistro.CONFIRMAR_REEMPLAZO
    assert r.calificacion_anterior.puntos == 35 and r.puntos == 42
    alumno = _alumno(servicio, curso_importado, "100000001")
    assert servicio.calificacion_de(parcial.id, alumno.id).puntos == 35


def test_reemplazo_confirmado_guarda_y_devuelve_la_anterior(servicio, curso_importado, parcial):
    servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 35)
    r = servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 42, reemplazar=True)
    assert r.estado == EstadoRegistro.GUARDADO
    assert r.calificacion_anterior.puntos == 35
    assert servicio.calificacion_de(parcial.id, r.alumno.id).puntos == 42


def test_deshacer_reemplazo_restaura_la_anterior(servicio, curso_importado, parcial):
    servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 35, fecha=date(2027, 3, 1))
    r = servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 42, reemplazar=True)
    servicio.deshacer_calificacion(parcial.id, r.alumno.id, r.calificacion_anterior)
    restaurada = servicio.calificacion_de(parcial.id, r.alumno.id)
    assert restaurada.puntos == 35 and restaurada.fecha == date(2027, 3, 1)


def test_deshacer_primer_registro_elimina_la_calificacion(servicio, curso_importado, parcial):
    r = servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 42)
    servicio.deshacer_calificacion(parcial.id, r.alumno.id, r.calificacion_anterior)
    assert servicio.calificacion_de(parcial.id, r.alumno.id) is None


def test_promedio_cuenta_examenes_sin_capturar_como_cero(servicio, curso_importado, parcial):
    servicio.crear_examen(curso_importado.id, "Final")
    r = servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 80)
    assert r.promedio == 40  # (80 + 0) / 2


def test_resumen_trae_promedio_de_examenes(servicio, curso_importado, parcial):
    final = servicio.crear_examen(curso_importado.id, "Final")
    servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 42)
    servicio.registrar_calificacion(curso_importado.id, final.id, "100000001", 70)
    por_cuenta = {f.alumno.num_cuenta: f for f in servicio.resumen_curso(curso_importado.id)}
    assert por_cuenta["100000001"].prom_examenes == 56
    assert por_cuenta["100000002"].prom_examenes == 0  # tiene examenes pero ninguno capturado


def test_curso_sin_examenes_no_tiene_promedio(servicio, curso_importado):
    assert all(f.prom_examenes is None for f in servicio.resumen_curso(curso_importado.id))


def test_las_calificaciones_no_alteran_las_decimas(servicio, curso_importado, parcial):
    alumno = _alumno(servicio, curso_importado, "100000001")
    servicio.registrar(curso_importado.id, "100000001", 5)
    servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 90)
    assert servicio.total_alumno(curso_importado.id, alumno.id) == 5


def test_oyente_puede_tener_calificacion(servicio, curso_importado, parcial):
    servicio.crear_alumno_en_curso(curso_importado.id, "Oyente Ficticio Uno")
    r = servicio.registrar_calificacion(curso_importado.id, parcial.id, "oyente ficticio", 60)
    assert r.estado == EstadoRegistro.GUARDADO
    assert servicio.calificacion_de(parcial.id, r.alumno.id).puntos == 60


def test_resumen_trae_la_calificacion_de_cada_examen(servicio, curso_importado, parcial):
    final = servicio.crear_examen(curso_importado.id, "Final")
    servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 42)
    por_cuenta = {f.alumno.num_cuenta: f for f in servicio.resumen_curso(curso_importado.id)}
    assert por_cuenta["100000001"].calificaciones == {parcial.id: 42}
    assert final.id not in por_cuenta["100000001"].calificaciones  # sin capturar: no está (vale 0)
    assert por_cuenta["100000002"].calificaciones == {}


# ---------------- historial de exámenes de un alumno ----------------
def test_historial_examenes_lista_todos_y_marca_los_capturados(servicio, curso_importado, parcial):
    final = servicio.crear_examen(curso_importado.id, "Final")
    alumno = _alumno(servicio, curso_importado, "100000001")
    servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 42, fecha=date(2027, 3, 1))
    lineas = servicio.historial_examenes(curso_importado.id, alumno.id)
    assert [l.examen.nombre for l in lineas] == ["Parcial 1", "Final"]
    assert (lineas[0].puntos, lineas[0].calificacion.fecha) == (42, date(2027, 3, 1))
    assert (lineas[1].puntos, lineas[1].calificacion) == (0, None)  # sin capturar vale 0
    assert lineas[1].examen.id == final.id


def test_historial_examenes_sin_examenes(servicio, curso_importado):
    alumno = _alumno(servicio, curso_importado, "100000001")
    assert servicio.historial_examenes(curso_importado.id, alumno.id) == []


def test_establecer_calificacion_crea_y_corrige_con_fecha(servicio, curso_importado, parcial):
    alumno = _alumno(servicio, curso_importado, "100000001")
    c = servicio.establecer_calificacion(curso_importado.id, parcial.id, alumno.id, 40, date(2027, 3, 1))
    assert (c.puntos, c.fecha) == (40, date(2027, 3, 1))
    c = servicio.establecer_calificacion(curso_importado.id, parcial.id, alumno.id, 47.5, date(2027, 3, 2))
    assert servicio.calificacion_de(parcial.id, alumno.id).puntos == 47.5
    assert servicio._repo.contar_calificaciones_examen(parcial.id) == 1  # corrige, no duplica


@pytest.mark.parametrize("valor", [-1, float("nan"), "abc"])
def test_establecer_calificacion_invalida(servicio, curso_importado, parcial, valor):
    alumno = _alumno(servicio, curso_importado, "100000001")
    with pytest.raises(ErrorDominio):
        servicio.establecer_calificacion(curso_importado.id, parcial.id, alumno.id, valor, date.today())


def test_eliminar_calificacion_vuelve_a_valer_cero(servicio, curso_importado, parcial):
    alumno = _alumno(servicio, curso_importado, "100000001")
    servicio.registrar_calificacion(curso_importado.id, parcial.id, "100000001", 42)
    servicio.eliminar_calificacion(parcial.id, alumno.id)
    assert servicio.calificacion_de(parcial.id, alumno.id) is None
    assert servicio.historial_examenes(curso_importado.id, alumno.id)[0].puntos == 0


def test_eliminar_calificacion_inexistente(servicio, curso_importado, parcial):
    alumno = _alumno(servicio, curso_importado, "100000001")
    with pytest.raises(ErrorDominio):
        servicio.eliminar_calificacion(parcial.id, alumno.id)
