import pytest

from ui_desktop.formato import formatear_decimas, leer_decimas, titulo_legible


def test_titulo_legible_mantiene_palabras_cortas_en_minuscula():
    assert titulo_legible("DISEÑO Y ANALISIS DE ALGORITMOS") == "Diseño y Analisis de Algoritmos"
    assert titulo_legible("de la paz") == "De la Paz"  # la primera palabra siempre con mayúscula


@pytest.mark.parametrize(
    "valor, con_signo, esperado",
    [(10, False, "10"), (10.0, True, "+10"), (-4, True, "-4"), (2.5, False, "2.5"),
     (100, False, "100"), (0, True, "0"), (0.004, False, "0"), (-0.001, False, "0")],
)
def test_formatear_decimas(valor, con_signo, esperado):
    assert formatear_decimas(valor, con_signo) == esperado


@pytest.mark.parametrize(
    "texto, esperado",
    [("10", 10), (" +5 ", 5), ("-2,5", -2.5), ("3.25", 3.25)],
)
def test_leer_decimas(texto, esperado):
    assert leer_decimas(texto) == esperado


@pytest.mark.parametrize("texto", ["", "  ", "abc", "1,2,3"])
def test_leer_decimas_invalidas(texto):
    with pytest.raises(ValueError):
        leer_decimas(texto)
