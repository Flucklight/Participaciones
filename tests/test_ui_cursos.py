"""Prueba de humo de la pantalla Cursos: maneja los diálogos reales por código.

Se omite si no hay pantalla disponible (p. ej. en un servidor sin entorno gráfico).
La ventana se coloca fuera de la zona visible para no estorbar.
"""

import pytest

from tests.conftest import buscar_dialogo as _dialogo, hay_pantalla


pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


def test_crear_editar_archivar_y_estado_vacio(ui):
    app, srv, vista = ui.app, ui.srv, ui.vista
    assert "Aún no tienes" in vista._vacio.cget("text")

    def llenar():
        d = _dialogo(app)
        for clave, valor in dict(materia="Redes", grupo="3001", ciclo="2027-I").items():
            d._campos[clave].insert(0, valor)
        d._aceptar()

    app.after(300, llenar)
    vista.crear()
    app.update()
    assert [c.materia for c in srv.listar_cursos()] == ["REDES"]
    assert len(vista._tarjetas) == 1

    def duplicado():
        d = _dialogo(app)
        for clave, valor in dict(materia="redes", grupo="3001", ciclo="2027-i").items():
            d._campos[clave].insert(0, valor)
        d._aceptar()
        assert "Ya existe" in d._error.cget("text")  # el diálogo sigue abierto con el error
        d.cancelar()

    app.after(300, duplicado)
    vista.crear()
    assert len(srv.listar_cursos()) == 1

    curso = srv.listar_cursos()[0]

    def editar():
        d = _dialogo(app)
        d._campos["grupo"].delete(0, "end")
        d._campos["grupo"].insert(0, "3002")
        d._aceptar()

    app.after(300, editar)
    vista.editar(curso)
    assert srv.listar_cursos()[0].grupo == "3002"

    vista.archivar(srv.listar_cursos()[0])
    assert len(vista._tarjetas) == 0
    vista._ver_archivados.select()
    vista.recargar()
    assert len(vista._tarjetas) == 1


def test_importar_con_vinculo_de_oyente_y_eliminar_curso(ui, tmp_path):
    from tests.conftest import crear_excel

    app, srv, vista = ui.app, ui.srv, ui.vista
    cid = srv.crear_curso("2027-I", "DISEÑO Y ANALISIS DE ALGORITMOS", "1510").id
    oyente = srv.crear_alumno_en_curso(cid, "abreu solano marcos")
    srv.registrar_para_alumno(cid, oyente.id, 10)
    ruta = crear_excel(
        tmp_path / "lista.xlsx",
        [("100000001", "ABREU SOLANO MARCOS"), ("100000002", "ACOSTA ORTEGA ELENA")],
    )
    ui.filedialog.askopenfilename = lambda **k: str(ruta)

    def aceptar_vinculo():
        d = _dialogo(app)
        assert len(d._marcas) == 1
        d._marcas[0][0].select()
        d._aceptar()

    app.after(400, aceptar_vinculo)
    vista.importar()
    assert ui.avisos[-1][0] == "info" and "Oyentes vinculados: 1" in ui.avisos[-1][1]
    assert srv.obtener_alumno(oyente.id).num_cuenta == "100000001"
    assert srv.total_alumno(cid, oyente.id) == 10
    assert srv.contar_alumnos(cid) == 2

    malo = tmp_path / "malo.xlsx"
    malo.write_text("no soy un excel")
    ui.filedialog.askopenfilename = lambda **k: str(malo)
    vista.importar()
    assert ui.avisos[-1][0] == "error"

    vista._seleccionar(cid)
    assert str(vista._boton_eliminar.cget("state")) == "normal"

    def confirmar_eliminar():
        d = _dialogo(app)
        assert str(d._ok.cget("state")) == "disabled"  # exige escribir ELIMINAR
        d._entrada.insert(0, "eliminar")
        d._revisar()
        assert str(d._ok.cget("state")) == "normal"
        d._ok.invoke()

    app.after(300, confirmar_eliminar)
    vista.eliminar_seleccionado()
    assert cid not in {c.id for c in srv.listar_cursos(True)}
    assert srv.obtener_alumno(oyente.id) is not None  # el alumno se conserva


def test_navegacion_entre_secciones(ui):
    app, srv = ui.app, ui.srv
    curso = srv.crear_curso("2027-I", "Redes", "1")
    app.mostrar("configuracion")
    app.update()
    app.abrir_curso(curso.id)
    app.update()
    app.mostrar("cursos")
    app.update()
