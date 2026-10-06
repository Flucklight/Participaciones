import pytest

from core.errores import ErrorDominio


def test_crear_y_listar_curso(servicio, curso):
    assert curso.id is not None
    assert curso.materia == "DISEÑO Y ANÁLISIS DE ALGORITMOS"
    assert [c.id for c in servicio.listar_cursos()] == [curso.id]


def test_curso_duplicado_rechazado(servicio, curso):
    with pytest.raises(ErrorDominio):
        servicio.crear_curso("2027-i", "diseño y análisis de algoritmos", "1510")


def test_campos_obligatorios(servicio):
    with pytest.raises(ErrorDominio):
        servicio.crear_curso("", "Materia", "1")


def test_editar_curso(servicio, curso):
    editado = servicio.editar_curso(curso.id, "2027-II", "Otra materia", "2000")
    assert editado.ciclo == "2027-II"
    assert servicio.listar_cursos()[0].grupo == "2000"


def test_editar_no_puede_chocar_con_otro_curso(servicio, curso):
    otro = servicio.crear_curso("2027-II", "Otra", "1")
    with pytest.raises(ErrorDominio):
        servicio.editar_curso(otro.id, curso.ciclo, curso.materia, curso.grupo)


def test_archivar_oculta_y_se_puede_restaurar(servicio, curso):
    servicio.archivar_curso(curso.id)
    assert servicio.listar_cursos() == []
    assert len(servicio.listar_cursos(incluir_archivados=True)) == 1
    servicio.archivar_curso(curso.id, False)
    assert len(servicio.listar_cursos()) == 1


def test_eliminar_borra_curso_y_participaciones_pero_conserva_alumnos(servicio, curso):
    alumno = servicio.crear_alumno_en_curso(curso.id, "Oyente Uno")
    servicio.registrar_para_alumno(curso.id, alumno.id, 10)
    assert servicio.resumen_eliminacion(curso.id) == (1, 1)
    servicio.eliminar_curso(curso.id)
    assert servicio.listar_cursos(incluir_archivados=True) == []
    assert servicio.obtener_alumno(alumno.id).nombre_completo == "OYENTE UNO"


def test_eliminar_curso_inexistente(servicio):
    with pytest.raises(ErrorDominio):
        servicio.eliminar_curso(999)
