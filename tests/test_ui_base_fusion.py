"""Configuración: fusionar la base con la vista previa y las decisiones (diálogos reales, datos ficticios)."""

from tkinter import filedialog

import pytest

from tests.conftest import buscar_dialogo, hay_pantalla
from tests.fusion import D1, alumno, lista, poblar_completo, servicio
from ui_desktop.dialogos_base import DialogoFusion, DialogoImportarBase

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def _programar(app, clase, accion):
    """Cuando aparezca un diálogo de `clase` (se abre con wait_window), ejecuta `accion(dialogo)`."""
    def buscar():
        d = buscar_dialogo(app)
        if isinstance(d, clase):
            accion(d)
        else:
            app.after(30, buscar)
    app.after(60, buscar)


@pytest.fixture
def config(ui, tmp_path):
    laptop, conexion = servicio(tmp_path / "laptop.db")
    poblar_completo(laptop)
    laptop.exportar_base(tmp_path / "viaje.db")
    conexion.close()
    ui.app.mostrar("configuracion")
    ui.app.update()
    ui.tmp = tmp_path
    ui.vista = ui.app._vista
    return ui


def _fusionar(config, monkeypatch, accion_fusion):
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(config.tmp / "viaje.db"))
    _programar(config.app, DialogoImportarBase, lambda d: d.cerrar("fusionar"))
    _programar(config.app, DialogoFusion, accion_fusion)
    config.vista.importar_base()


def test_fusionar_en_una_base_vacia_agrega_todo_y_se_puede_deshacer(config, monkeypatch):
    vistos = {}

    def aceptar(d):
        vistos["boton"] = d._boton.cget("text")
        vistos["resumen"] = d._resumen.cget("text")
        d._aceptar()

    _fusionar(config, monkeypatch, aceptar)
    assert vistos["boton"].startswith("Aplicar ") and "cambios" in vistos["boton"]
    assert "1 cursos" in vistos["resumen"] and "2 alumnos" in vistos["resumen"]
    assert [c.materia for c in config.srv.listar_cursos()] == ["REDES"]
    assert config.srv.hay_importacion_por_deshacer
    config.vista.deshacer_importacion()
    assert config.srv.listar_cursos() == []


def test_cancelar_la_fusion_no_guarda_nada(config, monkeypatch):
    _fusionar(config, monkeypatch, lambda d: d.cancelar())
    assert config.srv.listar_cursos() == []
    assert not config.srv.hay_importacion_por_deshacer


def test_un_conflicto_se_muestra_y_solo_cambia_si_se_marca(config, monkeypatch):
    curso = config.srv.importar_lista(lista()).curso
    a = alumno(config.srv, curso, "100000001")
    config.srv.establecer_tareas(curso.id, a.id, 5, D1)
    vistos = {}

    def marcar_y_aceptar(d):
        vistos["conflictos"] = [c.entidad for c in d._plan.conflictos]
        antes = d.cambios
        d._usar.add(d._plan.conflictos[0].id)
        d._actualizar_boton()
        vistos["suma"] = d.cambios - antes
        d._aceptar()

    _fusionar(config, monkeypatch, marcar_y_aceptar)
    assert "Tareas" in vistos["conflictos"] and vistos["suma"] == 1
    assert config.srv.tareas_de(curso.id, a.id).puntos == 9


def test_sin_marcar_el_conflicto_se_conserva_lo_local(config, monkeypatch):
    curso = config.srv.importar_lista(lista()).curso
    a = alumno(config.srv, curso, "100000001")
    config.srv.establecer_tareas(curso.id, a.id, 5, D1)
    _fusionar(config, monkeypatch, lambda d: d._aceptar())
    assert config.srv.tareas_de(curso.id, a.id).puntos == 5


def test_un_dudoso_recalcula_la_vista_previa_al_marcarlo(config, monkeypatch):
    curso = config.srv.importar_lista(lista(alumnos=(("100000001", "ABREU SOLANO MARCOS"),))).curso
    config.srv.crear_alumno_en_curso(curso.id, "Acosta Ortega Elena")  # oyente sin cuenta con el nombre del archivo
    vistos = {}

    def marcar(d):
        vistos["antes"] = (len(d._plan.dudosos), d._plan.omitidos)
        d._unir.add(d._plan.dudosos[0].id)
        d._refrescar()
        vistos["despues"] = (len(d._plan.dudosos), d._plan.omitidos, d._plan.dudosos[0].unir)
        d._aceptar()

    _fusionar(config, monkeypatch, marcar)
    assert vistos["antes"] == (1, 1) and vistos["despues"] == (1, 0, True)
    assert config.srv.resumen_base_local().alumnos == 2  # se unió, no se duplicó
