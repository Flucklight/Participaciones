"""Vista previa de la importación de tareas: coincidencia por nombre y reglas (datos ficticios)."""

import pytest

from core.errores import ErrorDominio
from core.models import (
    ArchivoCalificaciones,
    ColumnaCalificaciones,
    EstadoLinea,
    FilaCalificacion,
    TipoInscripcion,
)

H = ColumnaCalificaciones("H")


def fila(apellidos, nombres, valor=90.0, cuenta=""):
    return FilaCalificacion(apellidos, nombres, {"H": valor}, cuenta)


def archivo(*filas, grupo="", ciclo=""):
    return ArchivoCalificaciones([ColumnaCalificaciones("G", "Tarea"), H], list(filas), grupo, ciclo)


def previa(servicio, curso, *filas, **kwargs):
    return servicio.previsualizar_importacion_tareas(curso.id, archivo(*filas, **kwargs), "H")


def unica(vista):
    assert len(vista.lineas) == 1
    return vista.lineas[0]


# ---------------- coincidencia por nombre ----------------
def test_coincidencia_exacta_se_aplica(servicio, curso_importado):
    linea = unica(previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 85.5)))
    assert linea.estado == EstadoLinea.APLICAR
    assert linea.alumno.nombre_completo == "ABREU SOLANO MARCOS"
    assert linea.puntos == 85.5 and linea.anterior is None


def test_ignora_mayusculas_acentos_y_espacios(servicio, curso_importado):
    linea = unica(previa(servicio, curso_importado, fila("  abreu   sólano ", "Marcos")))
    assert linea.estado == EstadoLinea.APLICAR


def test_mismas_palabras_en_otro_orden_es_dudosa(servicio, curso_importado):
    linea = unica(previa(servicio, curso_importado, fila("MARCOS", "ABREU SOLANO")))
    assert linea.estado == EstadoLinea.DUDOSA
    assert linea.alumno.nombre_completo == "ABREU SOLANO MARCOS" and linea.puntos == 90


def test_nombre_contenido_en_el_del_curso_es_dudosa(servicio, curso_importado):
    linea = unica(previa(servicio, curso_importado, fila("ABREU", "MARCOS")))
    assert linea.estado == EstadoLinea.DUDOSA


def test_varias_coincidencias_se_omiten(servicio, curso_importado):
    linea = unica(previa(servicio, curso_importado, fila("GARCIA", "ANA")))  # hay dos García … Ana
    assert linea.estado == EstadoLinea.OMITIDA and linea.alumno is None
    assert "varios" in linea.motivo.lower()


def test_sin_coincidencia_se_omite(servicio, curso_importado):
    linea = unica(previa(servicio, curso_importado, fila("NADIE", "INEXISTENTE")))
    assert linea.estado == EstadoLinea.OMITIDA and "ningún" in linea.motivo.lower()


def test_nombre_repetido_en_el_archivo_se_omite(servicio, curso_importado):
    vista = previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 50), fila("ABREU SOLANO", "MARCOS", 60))
    assert [l.estado for l in vista.lineas] == [EstadoLinea.OMITIDA, EstadoLinea.OMITIDA]
    assert all("repetido" in l.motivo.lower() for l in vista.lineas)


def test_dos_filas_para_el_mismo_alumno_prevalece_la_exacta(servicio, curso_importado):
    vista = previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 50), fila("ABREU", "MARCOS", 60))
    exacta, dudosa = vista.lineas
    assert exacta.estado == EstadoLinea.APLICAR and exacta.puntos == 50
    assert dudosa.estado == EstadoLinea.OMITIDA and "mismo alumno" in dudosa.motivo.lower()


def test_dos_filas_dudosas_para_el_mismo_alumno_se_omiten(servicio, curso_importado):
    vista = previa(servicio, curso_importado, fila("ABREU", "MARCOS", 50), fila("MARCOS", "ABREU SOLANO", 60))
    assert [l.estado for l in vista.lineas] == [EstadoLinea.OMITIDA, EstadoLinea.OMITIDA]


def test_incluye_oyentes(servicio, curso_importado):
    servicio.crear_alumno_en_curso(curso_importado.id, "OYENTE UNO", TipoInscripcion.OYENTE)
    assert unica(previa(servicio, curso_importado, fila("OYENTE", "UNO"))).estado == EstadoLinea.APLICAR


# ---------------- cuenta con prioridad ----------------
def test_la_cuenta_tiene_prioridad_sobre_el_nombre(servicio, curso_importado):
    linea = unica(previa(servicio, curso_importado, fila("OTRO", "NOMBRE", 70, cuenta="100000002")))
    assert linea.estado == EstadoLinea.APLICAR and linea.alumno.num_cuenta == "100000002"


def test_cuenta_que_no_esta_en_el_curso_recurre_al_nombre(servicio, curso_importado):
    linea = unica(previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", cuenta="999999999")))
    assert linea.estado == EstadoLinea.APLICAR and linea.alumno.num_cuenta == "100000001"


# ---------------- valores ----------------
@pytest.mark.parametrize("valor, texto", [
    (None, "sin dato"),
    ("Sin entrega", "no es un número"),
    (-5.0, "mayor o igual a 0"),
    (float("nan"), "mayor o igual a 0"),
    (float("inf"), "mayor o igual a 0"),
])
def test_valor_invalido_se_omite_con_motivo(servicio, curso_importado, valor, texto):
    linea = unica(previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", valor)))
    assert linea.estado == EstadoLinea.OMITIDA and texto in linea.motivo.lower()
    assert linea.alumno.nombre_completo == "ABREU SOLANO MARCOS"  # se sabe quién es


def test_cero_y_valores_sobre_100_son_validos(servicio, curso_importado):
    vista = previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 0.0), fila("ACOSTA ORTEGA", "ELENA", 105.0))
    assert [l.estado for l in vista.lineas] == [EstadoLinea.APLICAR, EstadoLinea.APLICAR]


def test_cambian_e_iguales(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000001", 90)
    servicio.registrar_tareas(curso_importado.id, "100000002", 40)
    vista = previa(
        servicio, curso_importado,
        fila("ABREU SOLANO", "MARCOS", 90), fila("ACOSTA ORTEGA", "ELENA", 70), fila("GARCIA LOPEZ", "ANA", 60),
    )
    assert (vista.cambian, vista.iguales) == (2, 1)
    assert [l.anterior for l in vista.lineas] == [90, 40, None]


# ---------------- alcance ----------------
def test_alumnos_que_el_archivo_no_menciona(servicio, curso_importado):
    vista = previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS"))
    assert {a.nombre_completo for a in vista.sin_aparecer} == {
        "ACOSTA ORTEGA ELENA", "GARCIA LOPEZ ANA", "GARCIA PEREZ ANA"}


def test_una_fila_omitida_por_valor_no_cuenta_como_sin_aparecer(servicio, curso_importado):
    vista = previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", None))
    assert "ABREU SOLANO MARCOS" not in {a.nombre_completo for a in vista.sin_aparecer}


def test_la_vista_previa_no_guarda_ni_crea_nada(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000001", 10)
    antes = [(r.alumno.nombre_completo, r.tareas) for r in servicio.resumen_curso(curso_importado.id)]
    previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 99), fila("NUEVO", "ALUMNO", 80))
    despues = [(r.alumno.nombre_completo, r.tareas) for r in servicio.resumen_curso(curso_importado.id)]
    assert antes == despues


# ---------------- grupo y columna ----------------
def test_advierte_si_el_grupo_no_coincide(servicio, curso_importado):
    vista = previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS"), grupo="9999", ciclo="2027-I")
    assert "9999" in vista.advertencia_grupo and "1510" in vista.advertencia_grupo


def test_sin_advertencia_si_coincide_o_el_archivo_no_trae_grupo(servicio, curso_importado):
    assert previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS"), grupo="1510", ciclo="2027-I").advertencia_grupo == ""
    assert previa(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS")).advertencia_grupo == ""


def test_columna_por_omision_es_la_sugerida(servicio, curso_importado):
    vista = servicio.previsualizar_importacion_tareas(curso_importado.id, archivo(fila("ABREU SOLANO", "MARCOS", 77)))
    assert vista.columna.clave == "H" and vista.lineas[0].puntos == 77


def test_columna_inexistente(servicio, curso_importado):
    with pytest.raises(ErrorDominio, match="columna"):
        servicio.previsualizar_importacion_tareas(curso_importado.id, archivo(fila("A", "B")), "Z")


def test_curso_inexistente(servicio):
    with pytest.raises(ErrorDominio):
        servicio.previsualizar_importacion_tareas(999, archivo(fila("A", "B")))


# ---------------- de extremo a extremo: archivo ficticio -> vista previa ----------------
@pytest.mark.parametrize("formato", ["xlsx", "csv"])
def test_archivo_ficticio_a_vista_previa(tmp_path, servicio, curso_importado, formato):
    from importers.calificaciones_plataforma import leer_calificaciones
    from tests.plataforma import crear_csv_plataforma, crear_excel_plataforma

    alumnos = [("ABREU SOLANO", "MARCOS", [80, 90, 100]), ("ACOSTA ORTEGA", "ELENA", [50, 60, 70]),
               ("NADIE", "NUEVO", [10, 10, 10])]
    if formato == "xlsx":
        ruta = crear_excel_plataforma(tmp_path / "p.xlsx", alumnos, grupo="1510", ciclo="2027-I")
    else:
        ruta = crear_csv_plataforma(tmp_path / "p.csv", alumnos)
    vista = servicio.previsualizar_importacion_tareas(curso_importado.id, leer_calificaciones(ruta))
    assert vista.columna.clave in ("H", "G")  # el promedio: la columna de más a la derecha
    assert [l.puntos for l in vista.claras] == [90, 60]
    assert len(vista.omitidas) == 1 and vista.advertencia_grupo == ""
    assert (vista.cambian, vista.iguales) == (2, 0)


# ================= aplicar y deshacer =================
from datetime import date


def importar(servicio, curso, *filas, confirmadas=(), fecha=None, **kwargs):
    return servicio.importar_tareas(curso.id, archivo(*filas, **kwargs), "H", confirmadas, fecha)


def tareas(servicio, curso):
    return {r.alumno.nombre_completo: r.tareas for r in servicio.resumen_curso(curso.id)}


def test_importar_guarda_las_coincidencias_claras(servicio, curso_importado):
    r = importar(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 85.5), fila("ACOSTA ORTEGA", "ELENA", 70),
                 fecha=date(2027, 3, 9))
    assert (r.actualizadas, r.iguales, r.omitidas) == (2, 0, 0)
    assert tareas(servicio, curso_importado)["ABREU SOLANO MARCOS"] == 85.5
    alumno = servicio.resumen_curso(curso_importado.id)[0].alumno
    assert servicio.tareas_de(curso_importado.id, alumno.id).fecha == date(2027, 3, 9)


def test_fecha_por_omision_es_hoy(servicio, curso_importado):
    importar(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 85.5))
    alumno = servicio.resumen_curso(curso_importado.id)[0].alumno
    assert servicio.tareas_de(curso_importado.id, alumno.id).fecha == date.today()


def test_reemplaza_sin_pedir_confirmacion_por_alumno(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000001", 40)
    importar(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 90))
    assert tareas(servicio, curso_importado)["ABREU SOLANO MARCOS"] == 90


def test_una_dudosa_sin_confirmar_no_se_aplica(servicio, curso_importado):
    r = importar(servicio, curso_importado, fila("ABREU", "MARCOS", 90))
    assert r.actualizadas == 0 and r.omitidas == 1
    assert tareas(servicio, curso_importado)["ABREU SOLANO MARCOS"] == 0


def test_una_dudosa_confirmada_se_aplica(servicio, curso_importado):
    abreu = next(r.alumno for r in servicio.resumen_curso(curso_importado.id) if r.alumno.num_cuenta == "100000001")
    r = importar(servicio, curso_importado, fila("ABREU", "MARCOS", 90), confirmadas={abreu.id})
    assert r.actualizadas == 1 and tareas(servicio, curso_importado)["ABREU SOLANO MARCOS"] == 90


def test_confirmar_una_que_no_era_dudosa_no_cambia_nada_extra(servicio, curso_importado):
    otro = next(r.alumno for r in servicio.resumen_curso(curso_importado.id) if r.alumno.num_cuenta == "100000002")
    r = importar(servicio, curso_importado, fila("ABREU", "MARCOS", 90), confirmadas={otro.id})
    assert r.actualizadas == 0 and tareas(servicio, curso_importado)["ACOSTA ORTEGA ELENA"] == 0


def test_lo_omitido_y_lo_que_el_archivo_no_menciona_queda_intacto(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000002", 55)
    importar(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 90), fila("NADIE", "NUEVO", 10),
             fila("ACOSTA ORTEGA", "ELENA", None))
    assert tareas(servicio, curso_importado)["ACOSTA ORTEGA ELENA"] == 55  # celda vacía: no cambia
    assert len(servicio.resumen_curso(curso_importado.id)) == 4  # no se crearon alumnos


def test_un_valor_igual_no_se_reescribe(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000001", 90, date(2027, 1, 1))
    r = importar(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 90), fecha=date(2027, 3, 9))
    assert (r.actualizadas, r.iguales) == (0, 1)
    alumno = servicio.resumen_curso(curso_importado.id)[0].alumno
    assert servicio.tareas_de(curso_importado.id, alumno.id).fecha == date(2027, 1, 1)


def test_no_altera_decimas_ni_examenes(servicio, curso_importado):
    servicio.registrar(curso_importado.id, "100000001", 7)
    examen = servicio.crear_examen(curso_importado.id, "Parcial 1")
    servicio.registrar_calificacion(curso_importado.id, examen.id, "100000001", 60)
    antes = [(r.total, r.prom_examenes) for r in servicio.resumen_curso(curso_importado.id)]
    importar(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 90))
    assert antes == [(r.total, r.prom_examenes) for r in servicio.resumen_curso(curso_importado.id)]


def test_deshacer_restaura_anteriores_y_elimina_nuevas(servicio, curso_importado):
    servicio.registrar_tareas(curso_importado.id, "100000001", 40, date(2027, 1, 1))
    antes = tareas(servicio, curso_importado)
    r = importar(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 90), fila("ACOSTA ORTEGA", "ELENA", 70))
    assert tareas(servicio, curso_importado) != antes
    servicio.deshacer_importacion_tareas(curso_importado.id, r.anteriores)
    assert tareas(servicio, curso_importado) == antes
    abreu = next(x.alumno for x in servicio.resumen_curso(curso_importado.id) if x.alumno.num_cuenta == "100000001")
    acosta = next(x.alumno for x in servicio.resumen_curso(curso_importado.id) if x.alumno.num_cuenta == "100000002")
    assert servicio.tareas_de(curso_importado.id, abreu.id).fecha == date(2027, 1, 1)  # recupera hasta la fecha
    assert servicio.tareas_de(curso_importado.id, acosta.id) is None  # no existía: se elimina


def test_si_algo_falla_a_la_mitad_no_se_guarda_nada(servicio, curso_importado, monkeypatch):
    original = servicio._repo.guardar_tareas
    llamadas = []

    def falla_en_la_segunda(c):
        llamadas.append(c)
        if len(llamadas) == 2:
            raise RuntimeError("fallo simulado")
        original(c)

    monkeypatch.setattr(servicio._repo, "guardar_tareas", falla_en_la_segunda)
    with pytest.raises(RuntimeError):
        importar(servicio, curso_importado, fila("ABREU SOLANO", "MARCOS", 90), fila("ACOSTA ORTEGA", "ELENA", 70))
    monkeypatch.undo()
    assert set(tareas(servicio, curso_importado).values()) == {0.0}


def test_archivo_ficticio_completo_con_deshacer(tmp_path, servicio, curso_importado):
    from importers.calificaciones_plataforma import leer_calificaciones
    from tests.plataforma import crear_excel_plataforma

    ruta = crear_excel_plataforma(tmp_path / "p.xlsx", [("ABREU SOLANO", "MARCOS", [80, 90, 100])], grupo="1510")
    r = servicio.importar_tareas(curso_importado.id, leer_calificaciones(ruta))
    assert tareas(servicio, curso_importado)["ABREU SOLANO MARCOS"] == 90
    servicio.deshacer_importacion_tareas(curso_importado.id, r.anteriores)
    assert tareas(servicio, curso_importado)["ABREU SOLANO MARCOS"] == 0
