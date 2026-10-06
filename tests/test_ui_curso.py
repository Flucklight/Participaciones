"""Pantalla Curso: registro rápido, casos especiales y tabla (con los diálogos reales)."""

import pytest

from core.models import FilaLista, ListaInscripcion, TipoInscripcion
from tests.conftest import buscar_dialogo as _dialogo, hay_pantalla

pytestmark = pytest.mark.skipif(not hay_pantalla(), reason="sin entorno gráfico")


@pytest.fixture
def curso_ui(ui):
    """Curso importado con 4 alumnos (dos 'García Ana') y la pantalla Curso abierta."""
    lista = ListaInscripcion(
        "2027-I", "ING", "REDES", "3001",
        [
            FilaLista(1, "100000001", "ABREU SOLANO MARCOS"),
            FilaLista(2, "100000002", "ACOSTA ORTEGA ELENA"),
            FilaLista(3, "100000003", "GARCIA LOPEZ ANA"),
            FilaLista(4, "100000004", "GARCIA PEREZ ANA"),
        ],
    )
    curso = ui.srv.importar_lista(lista).curso
    ui.app.abrir_curso(curso.id)
    ui.app.update()
    ui.curso = curso
    ui.vista = ui.app._vista
    return ui


def _escribir(v, alumno, decimas):
    v._entrada_alumno.delete(0, "end")
    v._entrada_alumno.insert(0, alumno)
    v._entrada_decimas.delete(0, "end")
    v._entrada_decimas.insert(0, decimas)


def _texto_franja(v):
    return v._mensaje.cget("text")


def _fila(v, cuenta):
    return next(f for f in v._filas if f.alumno.num_cuenta == cuenta)


def test_la_tabla_lista_a_los_alumnos_sin_participaciones(curso_ui):
    v = curso_ui.vista
    assert len(v._tabla.get_children()) == 4
    assert "4 alumnos" in v._resumen.cget("text") and "4 sin participaciones" in v._resumen.cget("text")


def test_registro_por_cuenta_muestra_nombre_suma_y_total(curso_ui):
    v = curso_ui.vista
    _escribir(v, "100000001", "10")
    v.guardar()
    assert "ABREU SOLANO MARCOS" in _texto_franja(v)
    assert "+10" in _texto_franja(v) and "total 10" in _texto_franja(v)
    _escribir(v, "100000001", "5")
    v.guardar()
    assert "+5" in _texto_franja(v) and "total 15" in _texto_franja(v)
    assert v._tabla.item(str(_fila(v, "100000001").alumno.id), "values")[3] == "15"
    assert v._entrada_alumno.get() == "" and v._entrada_decimas.get() == ""


def test_decimas_negativas_y_con_coma(curso_ui):
    v = curso_ui.vista
    _escribir(v, "100000001", "10")
    v.guardar()
    _escribir(v, "100000001", "-2,5")
    v.guardar()
    assert "total 7.5" in _texto_franja(v)


def test_entradas_invalidas_muestran_error_y_no_guardan(curso_ui):
    v = curso_ui.vista
    for alumno, decimas in (("", "10"), ("100000001", ""), ("100000001", "abc"), ("100000001", "0")):
        _escribir(v, alumno, decimas)
        v.guardar()
        assert _texto_franja(v).startswith("⚠"), (alumno, decimas)
    assert all(f.n_participaciones == 0 for f in curso_ui.srv.resumen_curso(curso_ui.curso.id))


def test_deshacer_quita_el_ultimo_registro(curso_ui):
    v = curso_ui.vista
    _escribir(v, "100000001", "10")
    v.guardar()
    _escribir(v, "100000001", "5")
    v.guardar()
    v.deshacer()
    assert "Se deshizo" in _texto_franja(v)
    assert _fila(v, "100000001").total == 10
    v.deshacer()  # sin nada que deshacer: no falla ni cambia nada
    assert _fila(v, "100000001").total == 10


def test_autocompletado_sugiere_y_elige_con_teclado(curso_ui):
    v = curso_ui.vista
    v._entrada_alumno.insert(0, "acosta")
    v._sugerencias = curso_ui.srv.buscar_alumnos_en_curso(curso_ui.curso.id, "acosta")
    v._pintar_sugerencias()
    assert [a.num_cuenta for a in v._sugerencias] == ["100000002"]
    v._enter_alumno()  # una sola coincidencia: se elige con Enter
    assert v._elegido.num_cuenta == "100000002"
    assert v._entrada_alumno.get() == "ACOSTA ORTEGA ELENA"
    v._entrada_decimas.insert(0, "10")
    v.guardar()
    assert _fila(v, "100000002").total == 10


def test_ambiguo_pide_elegir_y_registra_al_elegido(curso_ui):
    v = curso_ui.vista

    def elegir():
        d = _dialogo(curso_ui.app)
        assert len(d.cuerpo.winfo_children()) > 0
        d.cerrar(next(a for a in v._servicio.buscar_alumnos_en_curso(v.curso.id, "garcia ana")
                      if a.num_cuenta == "100000004"))

    curso_ui.app.after(300, elegir)
    _escribir(v, "garcia ana", "10")
    v.guardar()
    assert _fila(v, "100000004").total == 10 and _fila(v, "100000003").total == 0


def test_ambiguo_cancelado_no_guarda(curso_ui):
    v = curso_ui.vista
    curso_ui.app.after(300, lambda: _dialogo(curso_ui.app).cancelar())
    _escribir(v, "garcia ana", "10")
    v.guardar()
    assert "cancelado" in _texto_franja(v)
    assert all(f.total == 0 for f in v._filas)


def test_no_existe_crear_oyente_y_registrar(curso_ui):
    v = curso_ui.vista

    def crear():
        d = _dialogo(curso_ui.app)
        assert d._nombre.get() == "LUIS NUEVO"  # precargado desde lo escrito
        d._aceptar()  # por defecto: oyente

    curso_ui.app.after(300, crear)
    _escribir(v, "luis nuevo", "10")
    v.guardar()
    oyente = next(f for f in v._filas if f.alumno.nombre_completo == "LUIS NUEVO")
    assert oyente.tipo == TipoInscripcion.OYENTE and oyente.total == 10
    assert oyente.alumno.num_cuenta is None
    assert "alumno agregado" in _texto_franja(v)
    assert "1 oyente" in v._resumen.cget("text")


def test_no_existe_por_cuenta_precarga_la_cuenta_y_exige_nombre(curso_ui):
    v = curso_ui.vista

    def intentar():
        d = _dialogo(curso_ui.app)
        assert d._cuenta.get() == "400000001"
        d._aceptar()  # sin nombre: el error aparece dentro del diálogo
        assert "nombre" in d._error.cget("text").lower()
        d._nombre.insert(0, "Persona Nueva")
        d._tipo.set("Regular")
        d._aceptar()

    curso_ui.app.after(300, intentar)
    _escribir(v, "400000001", "5")
    v.guardar()
    nuevo = next(f for f in v._filas if f.alumno.num_cuenta == "400000001")
    assert nuevo.tipo == TipoInscripcion.REGULAR and nuevo.total == 5


def test_no_existe_cancelar_no_crea_nada(curso_ui):
    v = curso_ui.vista
    curso_ui.app.after(300, lambda: _dialogo(curso_ui.app).cancelar())
    _escribir(v, "nadie", "10")
    v.guardar()
    assert len(v._filas) == 4 and "cancelado" in _texto_franja(v)


def test_alumno_de_otro_curso_se_ofrece_para_inscribir(curso_ui):
    srv = curso_ui.srv
    otro = srv.crear_curso("2027-II", "Otra materia", "9")
    curso_ui.app.abrir_curso(otro.id)
    curso_ui.app.update()
    v = curso_ui.app._vista

    def inscribir():
        d = _dialogo(curso_ui.app)
        assert d._opcion.get() != 0  # preseleccionado el alumno existente
        d._aceptar()

    curso_ui.app.after(300, inscribir)
    _escribir(v, "100000001", "10")
    v.guardar()
    assert srv.contar_alumnos(otro.id) == 1
    assert srv.total_alumno(otro.id, v._filas[0].alumno.id) == 10
    assert srv.contar_alumnos(curso_ui.curso.id) == 4  # no se duplicó el alumno


def test_agregar_alumno_manual_como_oyente(curso_ui):
    v = curso_ui.vista

    def alta():
        d = _dialogo(curso_ui.app)
        d._nombre.insert(0, "oyente manual")
        d._aceptar()

    curso_ui.app.after(300, alta)
    v.agregar_alumno()
    assert any(f.alumno.nombre_completo == "OYENTE MANUAL" and f.tipo == TipoInscripcion.OYENTE
               for f in v._filas)


def test_ocultar_oyentes_filtrar_y_ordenar(curso_ui):
    v, srv = curso_ui.vista, curso_ui.srv
    oyente = srv.crear_alumno_en_curso(curso_ui.curso.id, "Zeta Oyente")
    srv.registrar_para_alumno(curso_ui.curso.id, oyente.id, 99)
    srv.registrar(curso_ui.curso.id, "100000002", 20)
    v.recargar()
    assert len(v._tabla.get_children()) == 5

    v._ver_oyentes.deselect()
    v._dibujar_tabla()
    assert len(v._tabla.get_children()) == 4

    v._buscar.insert(0, "garcia")
    v._dibujar_tabla()
    assert len(v._tabla.get_children()) == 2
    v._buscar.delete(0, "end")
    v._ver_oyentes.select()

    v._ordenar_por("total")  # primer clic en Décimas: descendente
    primero = v._tabla.get_children()[0]
    assert primero == str(oyente.id)
    v._ordenar_por("total")
    assert v._tabla.get_children()[-1] == str(oyente.id)


def test_un_clic_en_una_fila_carga_al_alumno_en_el_campo_y_enfoca_las_decimas(curso_ui):
    from types import SimpleNamespace

    v = curso_ui.vista
    curso_ui.app.update()
    fila = _fila(v, "100000002")
    x, y, _w, h = v._tabla.bbox(str(fila.alumno.id))
    v._al_clic_tabla(SimpleNamespace(x=x + 20, y=y + h // 2))
    assert v._entrada_alumno.get() == "ACOSTA ORTEGA ELENA"
    assert v._elegido.id == fila.alumno.id

    # solo falta escribir las décimas y Enter
    v._entrada_decimas.insert(0, "10")
    v.guardar()
    assert _fila(v, "100000002").total == 10
    assert v._entrada_alumno.get() == ""  # listo para el siguiente


def test_clic_en_el_encabezado_o_en_vacio_no_carga_a_nadie(curso_ui):
    from types import SimpleNamespace

    v = curso_ui.vista
    curso_ui.app.update()
    v._al_clic_tabla(SimpleNamespace(x=30, y=5))  # encabezado
    v._al_clic_tabla(SimpleNamespace(x=30, y=100000))  # debajo de la última fila
    assert v._entrada_alumno.get() == "" and v._elegido is None


def test_registrar_no_rellena_el_campo_por_la_seleccion_automatica(curso_ui):
    v = curso_ui.vista
    _escribir(v, "100000001", "10")
    v.guardar()  # la fila queda resaltada/seleccionada, pero eso no es un clic del usuario
    assert v._entrada_alumno.get() == "" and v._elegido is None


def test_restar_mas_de_lo_que_hay_avisa_que_el_minimo_es_cero(curso_ui):
    v = curso_ui.vista
    _escribir(v, "100000001", "5")
    v.guardar()
    _escribir(v, "100000001", "-10")
    v.guardar()
    texto = _texto_franja(v)
    assert "-10 solicitadas" in texto and "se aplicaron -5" in texto and "total 0" in texto
    assert _fila(v, "100000001").total == 0


# ---------------------------------------------------------------- exportar
def _exportar_con(curso_ui, ruta, ajustar=None):
    """Abre el diálogo de exportar, lo acepta (tras `ajustar`) y simula el cuadro de guardar."""
    from tkinter import filedialog

    filedialog.asksaveasfilename = lambda **k: str(ruta) if ruta else ""

    def aceptar():
        d = _dialogo(curso_ui.app)
        if ajustar:
            ajustar(d)
        d._aceptar()

    curso_ui.app.after(300, aceptar)
    curso_ui.vista.exportar()


def test_exportar_excel_desde_la_pantalla_curso(curso_ui, tmp_path):
    import openpyxl

    v = curso_ui.vista
    _escribir(v, "100000001", "10")
    v.guardar()
    ruta = tmp_path / "salida.xlsx"
    _exportar_con(curso_ui, ruta)
    assert openpyxl.load_workbook(ruta).sheetnames == ["Resumen", "Participaciones"]
    assert "Exportado: 4 alumnos y 1 participaciones" in _texto_franja(v)
    assert "salida.xlsx" in _texto_franja(v)


def test_exportar_con_oyentes_y_en_csv(curso_ui, tmp_path):
    srv = curso_ui.srv
    oyente = srv.crear_alumno_en_curso(curso_ui.curso.id, "Pablo Oyente")
    srv.registrar_para_alumno(curso_ui.curso.id, oyente.id, 15)
    curso_ui.vista.recargar()

    ruta = tmp_path / "salida.csv"

    def marcar(d):
        d._formato.set("CSV (.csv)")
        d._al_cambiar_formato("CSV (.csv)")
        assert str(d._detalle.cget("state")) == "disabled"  # el detalle solo existe en Excel
        d._oyentes.select()

    _exportar_con(curso_ui, ruta, marcar)
    texto = ruta.read_text(encoding="utf-8-sig")
    assert "PABLO OYENTE" in texto and "Tipo" in texto.splitlines()[0]


def test_exportar_sin_oyentes_deshabilita_la_casilla(curso_ui, tmp_path):
    estados = {}

    def mirar(d):
        estados["oyentes"] = str(d._oyentes.cget("state"))

    _exportar_con(curso_ui, tmp_path / "x.xlsx", mirar)
    assert estados["oyentes"] == "disabled"  # no hay oyentes que incluir


def test_exportar_cancelando_el_cuadro_de_guardar_no_crea_nada(curso_ui, tmp_path):
    _exportar_con(curso_ui, None)
    assert list(tmp_path.glob("*.xlsx")) == []
    assert "Exportado" not in _texto_franja(curso_ui.vista)


def test_exportar_cancelando_el_dialogo_de_opciones(curso_ui, tmp_path):
    from tkinter import filedialog

    llamado = []
    filedialog.asksaveasfilename = lambda **k: llamado.append(1) or str(tmp_path / "x.xlsx")
    curso_ui.app.after(300, lambda: _dialogo(curso_ui.app).cancelar())
    curso_ui.vista.exportar()
    assert llamado == []  # ni siquiera se pidió dónde guardar


def test_exportar_con_error_avisa_y_deja_la_app_en_pie(curso_ui, tmp_path):
    ruta = tmp_path / "no_existe" / "x.xlsx"  # carpeta inexistente
    _exportar_con(curso_ui, ruta)
    assert curso_ui.avisos[-1][0] == "error" and "No se pudo guardar" in curso_ui.avisos[-1][1]
    assert _texto_franja(curso_ui.vista).startswith("⚠")
