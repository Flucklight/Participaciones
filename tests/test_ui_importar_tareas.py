"""Pantalla Curso: importar tareas desde un archivo (diálogo real, datos ficticios)."""

import tkinter as tk

import customtkinter as ctk
import pytest

from tests.conftest import buscar_dialogo as _dialogo, hay_pantalla
from tests.plataforma import crear_csv_plataforma, crear_excel_plataforma
from tests.test_ui_curso import _texto_franja, curso_ui  # noqa: F401  (fixture)

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")

ALUMNOS = [("ABREU SOLANO", "MARCOS", [80, 90, 100]), ("ACOSTA ORTEGA", "ELENA", [50, 60, 70])]


def _importar_con(ui, ruta, ajustar=None, aceptar=True):
    """Abre el diálogo de importar con `ruta` en el selector, lo ajusta y lo acepta o cancela.

    Un error dentro del diálogo se guarda y se relanza después: dejar un diálogo modal abierto
    colgaría la prueba.
    """
    ui.filedialog.askopenfilename = lambda **k: str(ruta) if ruta else ""
    estado = {}

    def accion():
        d = _dialogo(ui.app)
        if d is None:
            return
        try:
            if ajustar:
                ajustar(d)
            if aceptar:
                d._aceptar()
        except BaseException as error:  # noqa: BLE001
            estado["error"] = error
        finally:
            try:
                if d.winfo_exists():
                    d.cancelar()
            except tk.TclError:
                pass

    if ruta:
        ui.app.after(300, accion)
    ui.vista.importar_tareas()
    if "error" in estado:
        raise estado["error"]


def _tareas(ui):
    return {r.alumno.num_cuenta: r.tareas for r in ui.srv.resumen_curso(ui.curso.id)}


def _filas_dialogo(d):
    return [d._tabla.item(i, "values") for i in d._tabla.get_children()]


def _botones(raiz):
    for hijo in raiz.winfo_children():
        if isinstance(hijo, ctk.CTkButton):
            yield hijo
        yield from _botones(hijo)


# ---------------- botón y apertura ----------------
def test_el_encabezado_tiene_el_boton_importar_tareas(curso_ui):
    assert any("Importar tareas" in b.cget("text") for b in _botones(curso_ui.vista))


def test_cancelar_el_selector_de_archivo_no_hace_nada(curso_ui):
    _importar_con(curso_ui, None)
    assert set(_tareas(curso_ui).values()) == {0.0}
    assert "Tareas importadas" not in _texto_franja(curso_ui.vista)


# ---------------- aplicar ----------------
def test_importar_xlsx_muestra_resumen_y_guarda_al_aplicar(curso_ui, tmp_path):
    ruta = crear_excel_plataforma(tmp_path / "p.xlsx", ALUMNOS)
    vistos = {}

    def mirar(d):
        vistos["resumen"] = d._resumen.cget("text")
        vistos["boton"] = d._boton.cget("text")
        vistos["columna"] = d._columna.get()
        vistos["filas"] = _filas_dialogo(d)
        assert _tareas(curso_ui) == {c: 0.0 for c in _tareas(curso_ui)}  # nada guardado aún

    _importar_con(curso_ui, ruta, mirar)
    assert "2 coinciden (2 cambian · 0 quedan igual)" in vistos["resumen"]
    assert "2 alumnos del curso no aparecen" in vistos["resumen"]
    assert vistos["boton"] == "Aplicar 2 cambios" and vistos["columna"] == "Columna H (sin encabezado)"
    assert ("Cambia", "ABREU SOLANO MARCOS", "—", "90", "ABREU SOLANO MARCOS") in vistos["filas"]
    assert _tareas(curso_ui)["100000001"] == 90 and _tareas(curso_ui)["100000002"] == 60
    assert "Tareas importadas: 2 actualizadas, 0 omitidas." in _texto_franja(curso_ui.vista)
    assert curso_ui.vista._tabla.item(curso_ui.vista._tabla.get_children()[0], "values")  # tabla recargada


def test_importar_csv(curso_ui, tmp_path):
    ruta = crear_csv_plataforma(tmp_path / "p.csv", ALUMNOS)
    _importar_con(curso_ui, ruta)
    assert _tareas(curso_ui)["100000001"] == 90


def test_cancelar_el_dialogo_no_guarda_nada(curso_ui, tmp_path):
    ruta = crear_excel_plataforma(tmp_path / "p.xlsx", ALUMNOS)
    _importar_con(curso_ui, ruta, aceptar=False)
    assert set(_tareas(curso_ui).values()) == {0.0}
    assert "Tareas importadas" not in _texto_franja(curso_ui.vista)


def test_cambiar_la_columna_actualiza_la_vista_previa(curso_ui, tmp_path):
    ruta = crear_excel_plataforma(tmp_path / "p.xlsx", ALUMNOS)
    vistos = {}

    def elegir(d):
        assert "Tarea 1: Introducción (columna E)" in d._por_descripcion
        d._columna.set("Tarea 1: Introducción (columna E)")
        d._al_elegir_columna("")
        vistos["filas"] = _filas_dialogo(d)
        vistos["muestra"] = d._muestra.cget("text")

    _importar_con(curso_ui, ruta, elegir)
    assert ("Cambia", "ABREU SOLANO MARCOS", "—", "80", "ABREU SOLANO MARCOS") in vistos["filas"]
    assert vistos["muestra"].startswith("valores: 80, 50")
    assert _tareas(curso_ui)["100000001"] == 80  # se importó la columna elegida


def test_los_valores_iguales_aparecen_como_igual_y_no_cuentan(curso_ui, tmp_path):
    curso_ui.srv.registrar_tareas(curso_ui.curso.id, "100000001", 90)
    ruta = crear_excel_plataforma(tmp_path / "p.xlsx", ALUMNOS)
    vistos = {}
    _importar_con(curso_ui, ruta, lambda d: vistos.update(boton=d._boton.cget("text"), filas=_filas_dialogo(d)))
    assert vistos["boton"] == "Aplicar 1 cambio"
    assert any(f[0] == "Igual" and f[2] == "90" and f[3] == "90" for f in vistos["filas"])


# ---------------- dudosas ----------------
def test_una_dudosa_solo_se_aplica_si_se_marca(curso_ui, tmp_path):
    ruta = crear_excel_plataforma(tmp_path / "p.xlsx", [("ABREU", "MARCOS", [80, 90, 100])])
    vistos = {}

    def sin_marcar(d):
        vistos["boton"] = d._boton.cget("text"), str(d._boton.cget("state"))
        vistos["marcas"] = len(d._marcas)
        vistos["fila"] = _filas_dialogo(d)[0][0]

    _importar_con(curso_ui, ruta, sin_marcar, aceptar=False)
    assert vistos["boton"] == ("Aplicar 0 cambios", "disabled") and vistos["marcas"] == 1
    assert vistos["fila"] == "Dudosa"
    assert _tareas(curso_ui)["100000001"] == 0

    def marcar(d):
        d._marcas[0][0].select()
        d._al_marcar()
        vistos["boton2"] = d._boton.cget("text"), str(d._boton.cget("state"))

    _importar_con(curso_ui, ruta, marcar)
    assert vistos["boton2"] == ("Aplicar 1 cambio", "normal")
    assert _tareas(curso_ui)["100000001"] == 90


def test_las_dudosas_marcadas_se_conservan_al_cambiar_de_columna(curso_ui, tmp_path):
    ruta = crear_excel_plataforma(tmp_path / "p.xlsx", [("ABREU", "MARCOS", [80, 90, 100])])

    def ajustar(d):
        d._marcas[0][0].select()
        d._al_marcar()
        d._columna.set("Tarea 1: Introducción (columna E)")
        d._al_elegir_columna("")
        assert d._marcas[0][0].get() == 1 and d._boton.cget("text") == "Aplicar 1 cambio"

    _importar_con(curso_ui, ruta, ajustar)
    assert _tareas(curso_ui)["100000001"] == 80


# ---------------- avisos y errores ----------------
def test_archivo_invalido_muestra_el_error_y_no_abre_el_dialogo(curso_ui, tmp_path):
    ruta = tmp_path / "datos.txt"
    ruta.write_text("hola")
    _importar_con(curso_ui, ruta)
    assert curso_ui.avisos and curso_ui.avisos[0][0] == "error" and "xlsx" in curso_ui.avisos[0][1]
    assert "⚠" in _texto_franja(curso_ui.vista)


def test_grupo_distinto_exige_confirmar_de_todos_modos(curso_ui, tmp_path):
    ruta = crear_excel_plataforma(tmp_path / "p.xlsx", ALUMNOS, grupo="9999")
    vistos = {}

    def revisar(d):
        vistos["aviso"] = d._aviso.cget("text")
        vistos["antes"] = str(d._boton.cget("state"))
        d._forzar.select()
        d._actualizar_boton()
        vistos["despues"] = str(d._boton.cget("state"))

    _importar_con(curso_ui, ruta, revisar)
    assert "9999" in vistos["aviso"] and "3001" in vistos["aviso"]
    assert (vistos["antes"], vistos["despues"]) == ("disabled", "normal")
    assert _tareas(curso_ui)["100000001"] == 90


def test_sin_cambios_que_aplicar_el_boton_esta_deshabilitado(curso_ui, tmp_path):
    ruta = crear_excel_plataforma(tmp_path / "p.xlsx", [("NADIE", "NUEVO", [80, 90, 100])])
    vistos = {}
    _importar_con(curso_ui, ruta, lambda d: vistos.update(estado=str(d._boton.cget("state")), filas=_filas_dialogo(d)),
                  aceptar=False)
    assert vistos["estado"] == "disabled" and vistos["filas"][0][0] == "Omitida"
    assert len(curso_ui.srv.resumen_curso(curso_ui.curso.id)) == 4  # no se creó ningún alumno
