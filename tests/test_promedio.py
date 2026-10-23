from core.promedio import promedio_examenes


def test_media_simple_de_los_puntos():
    assert promedio_examenes([42, 70]) == 56


def test_examen_sin_capturar_cuenta_como_cero():
    assert promedio_examenes([42, 70, 0]) == (42 + 70 + 0) / 3


def test_puntos_extra_sin_tope():
    assert promedio_examenes([110, 90]) == 100


def test_curso_sin_examenes_no_tiene_promedio():
    assert promedio_examenes([]) is None
