import sys
from pathlib import Path

import pytest

from core import rutas


def test_en_desarrollo_los_datos_van_en_data_del_proyecto():
    assert not rutas.esta_empaquetado()
    assert rutas.carpeta_datos() == rutas.carpeta_proyecto() / "data"
    assert (rutas.carpeta_proyecto() / "main.py").exists()


def test_empaquetada_los_datos_van_en_localappdata_fuera_de_la_app(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert rutas.esta_empaquetado()
    assert rutas.carpeta_datos() == tmp_path / "Participaciones" / "data"


def test_empaquetada_sin_localappdata_usa_la_carpeta_del_usuario(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert rutas.carpeta_datos() == Path.home() / "AppData" / "Local" / "Participaciones" / "data"


def test_recursos_empaquetados_se_buscan_en_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert rutas.recurso("assets/icon/app.ico") == tmp_path / "assets" / "icon" / "app.ico"


def test_el_icono_de_la_app_existe_y_es_un_ico_valido():
    pytest.importorskip("PIL")  # Pillow solo se instala para compilar (requirements-build.txt)
    from PIL import Image

    ruta = rutas.recurso("assets/icon/app.ico")
    assert ruta.exists()
    with Image.open(ruta) as ico:
        assert ico.format == "ICO"
        assert (256, 256) in ico.info["sizes"] and (16, 16) in ico.info["sizes"]
