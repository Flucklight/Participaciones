"""Configuración: exportar e importar la base (reemplazar todo) con los diálogos reales (datos ficticios)."""

from tkinter import filedialog, messagebox

import pytest

from core.models import FilaLista, ListaInscripcion
from tests.conftest import buscar_dialogo, hay_pantalla

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def _lista(materia, cuenta):
    return ListaInscripcion("2027-I", "ING", materia, "3001", [FilaLista(1, cuenta, "ALUMNO FICTICIO")])


def _confirmar(app, resultado):
    """Programa lo que hará el diálogo cuando aparezca (se abre con wait_window)."""
    def accion():
        d = buscar_dialogo(app)
        if d is None:
            app.after(30, accion)
            return
        d.cerrar(resultado) if resultado else d.cancelar()
    app.after(60, accion)


@pytest.fixture
def config(ui, tmp_path):
    ui.srv.importar_lista(_lista("REDES", "100000001"))
    ui.app.mostrar("configuracion")
    ui.app.update()
    ui.tmp = tmp_path
    ui.vista = ui.app._vista
    return ui


def test_exportar_guarda_un_archivo_con_la_base(config, monkeypatch):
    destino = config.tmp / "viaje.db"
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **k: str(destino))
    config.vista.exportar_base()
    assert destino.is_file()
    assert "viaje.db" in config.vista._mensaje.cget("text")


def test_exportar_cancelado_no_crea_nada(config, monkeypatch):
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **k: "")
    config.vista.exportar_base()
    assert config.vista._mensaje.cget("text") == ""


def test_importar_reemplazar_y_deshacer(config, monkeypatch):
    origen = config.tmp / "viaje.db"
    config.srv.exportar_base(origen)
    config.srv.importar_lista(_lista("EXTRA", "100000002"))
    assert len(config.srv.listar_cursos()) == 2
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(origen))
    _confirmar(config.app, "reemplazar")
    config.vista.importar_base()
    assert [c.materia for c in config.srv.listar_cursos()] == ["REDES"]
    assert config.srv.hay_importacion_por_deshacer
    config.vista.deshacer_importacion()
    assert len(config.srv.listar_cursos()) == 2


def test_importar_cancelado_no_cambia_nada(config, monkeypatch):
    origen = config.tmp / "viaje.db"
    config.srv.exportar_base(origen)
    config.srv.importar_lista(_lista("EXTRA", "100000002"))
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(origen))
    _confirmar(config.app, None)
    config.vista.importar_base()
    assert len(config.srv.listar_cursos()) == 2
    assert not config.srv.hay_importacion_por_deshacer


def test_un_archivo_invalido_muestra_el_error(config, monkeypatch):
    malo = config.tmp / "malo.db"
    malo.write_text("no soy una base " * 40)
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(malo))
    errores = []
    monkeypatch.setattr(messagebox, "showerror", lambda t, m, **k: errores.append(m))
    config.vista.importar_base()
    assert errores and "no es una base" in errores[0]
