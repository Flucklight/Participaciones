from core.normalizacion import es_numero_de_cuenta, limpiar_nombre, normalizar


def test_limpiar_nombre_mayusculas_y_espacios():
    assert limpiar_nombre("  juan   de la  paz ") == "JUAN DE LA PAZ"


def test_limpiar_conserva_acentos():
    assert limpiar_nombre("martínez") == "MARTÍNEZ"


def test_normalizar_ignora_acentos_mayusculas_y_espacios():
    assert normalizar("MARTÍNEZ  Muñoz ") == normalizar("martinez muñoz") == "MARTINEZ MUNOZ"


def test_numero_de_cuenta():
    assert es_numero_de_cuenta(" 100000001 ")
    assert not es_numero_de_cuenta("32A")
    assert not es_numero_de_cuenta("")
