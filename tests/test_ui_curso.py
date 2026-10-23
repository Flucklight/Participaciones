"""Pantalla Curso: registro rápido, casos especiales y tabla (con los diálogos reales)."""

from types import SimpleNamespace

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


# ---------------- modo Examen del registro rápido ----------------
def _crear_examen_ui(curso_ui, nombre):
    """Usa el diálogo real de «＋ Nuevo»."""
    def llenar():
        d = _dialogo(curso_ui.app)
        d._nombre.insert(0, nombre)
        d._aceptar()

    curso_ui.app.after(300, llenar)
    curso_ui.vista.nuevo_examen()


def _modo_examen(curso_ui):
    curso_ui.vista._selector_modo.set("Examen")
    curso_ui.vista._cambiar_modo("Examen")
    curso_ui.app.update()


def test_por_defecto_el_registro_es_de_participacion(curso_ui):
    v = curso_ui.vista
    assert v._modo == "participacion"
    assert not v._fila_examen.winfo_ismapped()
    assert v._boton_guardar.cget("text") == "Guardar"


def test_cambiar_a_examen_muestra_la_lista_y_cambia_los_campos(curso_ui):
    v = curso_ui.vista
    _modo_examen(curso_ui)
    assert v._modo == "examen" and v._fila_examen.winfo_ismapped()
    assert v._boton_guardar.cget("text") == "Registrar examen"
    assert v._entrada_decimas.cget("placeholder_text") == "Calificación"
    assert not v._atajos[0].winfo_ismapped()
    v._selector_modo.set("Participación")
    v._cambiar_modo("Participación")
    curso_ui.app.update()
    assert v._modo == "participacion" and not v._fila_examen.winfo_ismapped()
    assert v._boton_guardar.cget("text") == "Guardar" and v._atajos[0].winfo_ismapped()


def test_sin_examenes_avisa_que_hay_que_crear_uno(curso_ui):
    v = curso_ui.vista
    _modo_examen(curso_ui)
    _escribir(v, "100000001", "42")
    v.guardar()
    assert _texto_franja(v).startswith("⚠") and "examen" in _texto_franja(v).lower()
    assert curso_ui.srv.listar_examenes(curso_ui.curso.id) == []


def test_nuevo_examen_queda_seleccionado(curso_ui):
    v = curso_ui.vista
    _modo_examen(curso_ui)
    _crear_examen_ui(curso_ui, "Parcial 1")
    assert [e.nombre for e in curso_ui.srv.listar_examenes(curso_ui.curso.id)] == ["Parcial 1"]
    assert v._examen_actual.nombre == "Parcial 1"
    _crear_examen_ui(curso_ui, "Final")
    assert v._examen_actual.nombre == "Final"


def test_nuevo_examen_duplicado_muestra_el_error_en_el_dialogo(curso_ui):
    v = curso_ui.vista
    _modo_examen(curso_ui)
    _crear_examen_ui(curso_ui, "Parcial 1")

    def repetir():
        d = _dialogo(curso_ui.app)
        d._nombre.insert(0, "parcial 1")
        d._aceptar()
        assert "Ya existe" in d._error.cget("text")
        d.cancelar()

    curso_ui.app.after(300, repetir)
    v.nuevo_examen()
    assert len(curso_ui.srv.listar_examenes(curso_ui.curso.id)) == 1


def test_registrar_calificacion_por_cuenta_conserva_modo_y_examen(curso_ui):
    v = curso_ui.vista
    _modo_examen(curso_ui)
    _crear_examen_ui(curso_ui, "Parcial 1")
    _escribir(v, "100000001", "42")
    v.guardar()
    assert "ABREU SOLANO MARCOS" in _texto_franja(v) and "Parcial 1" in _texto_franja(v)
    assert "42" in _texto_franja(v)
    alumno = _fila(v, "100000001").alumno
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, alumno.id).puntos == 42
    assert v._modo == "examen" and v._examen_actual.nombre == "Parcial 1"
    assert v._entrada_alumno.get() == "" and v._entrada_decimas.get() == ""
    assert _fila(v, "100000001").total == 0  # las décimas no cambian


def test_calificacion_invalida_muestra_error_y_no_guarda(curso_ui):
    v = curso_ui.vista
    _modo_examen(curso_ui)
    _crear_examen_ui(curso_ui, "Parcial 1")
    for texto in ("", "abc", "-3"):
        _escribir(v, "100000001", texto)
        v.guardar()
        assert _texto_franja(v).startswith("⚠"), texto
    assert curso_ui.srv._repo.contar_calificaciones_examen(v._examen_actual.id) == 0


def test_examen_ambiguo_pide_elegir_y_califica_al_elegido(curso_ui):
    v = curso_ui.vista
    _modo_examen(curso_ui)
    _crear_examen_ui(curso_ui, "Parcial 1")

    def elegir():
        d = _dialogo(curso_ui.app)
        d.cerrar(next(a for a in v._servicio.buscar_alumnos_en_curso(v.curso.id, "garcia ana")
                      if a.num_cuenta == "100000004"))

    curso_ui.app.after(300, elegir)
    _escribir(v, "garcia ana", "9")
    v.guardar()
    alumno = _fila(v, "100000004").alumno
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, alumno.id).puntos == 9


def test_examen_de_alumno_inexistente_ofrece_crear_oyente_y_califica(curso_ui):
    v = curso_ui.vista
    _modo_examen(curso_ui)
    _crear_examen_ui(curso_ui, "Parcial 1")
    curso_ui.app.after(300, lambda: _dialogo(curso_ui.app)._aceptar())
    _escribir(v, "luis nuevo", "7.5")
    v.guardar()
    oyente = next(f for f in v._filas if f.alumno.nombre_completo == "LUIS NUEVO")
    assert oyente.tipo == TipoInscripcion.OYENTE
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, oyente.alumno.id).puntos == 7.5


def test_reemplazo_advierte_y_no_guarda_hasta_confirmar(curso_ui):
    v = curso_ui.vista
    _modo_examen(curso_ui)
    _crear_examen_ui(curso_ui, "Parcial 1")
    _escribir(v, "100000001", "35")
    v.guardar()
    _escribir(v, "100000001", "42")
    v.guardar()
    assert "Ya tiene 35" in _texto_franja(v) and "42" in _texto_franja(v)
    alumno = _fila(v, "100000001").alumno
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, alumno.id).puntos == 35
    v.confirmar_reemplazo()
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, alumno.id).puntos == 42
    assert v._entrada_alumno.get() == ""


def test_cancelar_reemplazo_conserva_la_calificacion(curso_ui):
    v = curso_ui.vista
    _modo_examen(curso_ui)
    _crear_examen_ui(curso_ui, "Parcial 1")
    _escribir(v, "100000001", "35")
    v.guardar()
    _escribir(v, "100000001", "42")
    v.guardar()
    v.cancelar_reemplazo()
    alumno = _fila(v, "100000001").alumno
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, alumno.id).puntos == 35
    assert "cancel" in _texto_franja(v).lower()


# ---------------- modo Examen: deshacer, clic en fila, F2 y promedio ----------------
def _examen_listo(curso_ui, nombre="Parcial 1"):
    _modo_examen(curso_ui)
    _crear_examen_ui(curso_ui, nombre)
    return curso_ui.vista


def _calificar(v, cuenta, puntos):
    _escribir(v, cuenta, puntos)
    v.guardar()


def _clic_en_fila(curso_ui, cuenta):
    from types import SimpleNamespace

    v = curso_ui.vista
    curso_ui.app.update()
    x, y, _w, h = v._tabla.bbox(str(_fila(v, cuenta).alumno.id))
    v._al_clic_tabla(SimpleNamespace(x=x + 20, y=y + h // 2))


def test_deshacer_la_primera_calificacion_la_elimina(curso_ui):
    v = _examen_listo(curso_ui)
    _calificar(v, "100000001", "42")
    assert v._boton_deshacer.winfo_manager()  # el botón Deshacer está visible
    v.deshacer()
    alumno = _fila(v, "100000001").alumno
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, alumno.id) is None
    assert "Se deshizo" in _texto_franja(v)
    v.deshacer()  # sin nada más que deshacer: no falla
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, alumno.id) is None


def test_deshacer_un_reemplazo_restaura_la_calificacion_anterior(curso_ui):
    v = _examen_listo(curso_ui)
    _calificar(v, "100000001", "35")
    _calificar(v, "100000001", "42")
    v.confirmar_reemplazo()
    v.deshacer()
    alumno = _fila(v, "100000001").alumno
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, alumno.id).puntos == 35


def test_deshacer_solo_afecta_al_ultimo_registro(curso_ui):
    v = _examen_listo(curso_ui)
    _calificar(v, "100000001", "42")
    _modo_participacion(curso_ui)
    _calificar(v, "100000001", "10")  # participación: ahora lo último es esto
    v.deshacer()
    assert _fila(v, "100000001").total == 0
    alumno = _fila(v, "100000001").alumno
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, alumno.id).puntos == 42


def _modo_participacion(curso_ui):
    curso_ui.vista._selector_modo.set("Participación")
    curso_ui.vista._cambiar_modo("Participación")
    curso_ui.app.update()


def test_clic_en_fila_en_modo_examen_carga_la_calificacion_actual(curso_ui):
    v = _examen_listo(curso_ui)
    _calificar(v, "100000002", "35")
    _clic_en_fila(curso_ui, "100000002")
    assert v._entrada_alumno.get() == "ACOSTA ORTEGA ELENA"
    assert v._entrada_decimas.get() == "35"
    v._entrada_decimas.delete(0, "end")
    v._entrada_decimas.insert(0, "40")
    v.guardar()  # modificar: advierte reemplazo
    assert "Ya tiene 35" in _texto_franja(v)
    v.confirmar_reemplazo()
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, _fila(v, "100000002").alumno.id).puntos == 40


def test_clic_en_fila_sin_calificacion_deja_vacio_el_campo(curso_ui):
    v = _examen_listo(curso_ui)
    _clic_en_fila(curso_ui, "100000001")
    assert v._elegido.num_cuenta == "100000001" and v._entrada_decimas.get() == ""


def test_clic_en_fila_en_modo_participacion_no_carga_calificaciones(curso_ui):
    v = _examen_listo(curso_ui)
    _calificar(v, "100000002", "35")
    _modo_participacion(curso_ui)
    _clic_en_fila(curso_ui, "100000002")
    assert v._entrada_decimas.get() == ""


def test_f2_alterna_el_modo(curso_ui):
    v = curso_ui.vista
    for campo in (v._entrada_alumno, v._entrada_decimas):
        assert campo._entry.bind("<F2>")  # el Entry de tk guarda el enlace
    assert v._alternar_modo() == "break" and v._modo == "examen"
    assert v._selector_modo.get() == "Examen"
    v._alternar_modo()
    assert v._modo == "participacion" and v._selector_modo.get() == "Participación"


def _columnas_examen(v):
    """[(id de columna, encabezado)] de las columnas de examen de la tabla."""
    return [(c, v._tabla.heading(c, "text").split("  ")[0]) for c in v._tabla["columns"]
            if c.startswith("examen_")]


def _celda(v, cuenta, columna):
    return v._tabla.item(str(_fila(v, cuenta).alumno.id), "values")[list(v._tabla["columns"]).index(columna)]


def test_sin_examenes_la_tabla_no_tiene_columnas_de_examen(curso_ui):
    assert _columnas_examen(curso_ui.vista) == []


def test_cada_examen_agrega_una_columna_con_su_nombre(curso_ui):
    v = _examen_listo(curso_ui, "Parcial 1")
    assert [t for _c, t in _columnas_examen(v)] == ["Examen - Parcial 1"]
    _crear_examen_ui(curso_ui, "Final")
    assert [t for _c, t in _columnas_examen(v)] == ["Examen - Parcial 1", "Examen - Final"]
    assert "prom_examenes" not in v._tabla["columns"]  # ya no hay columna de promedio


def test_la_columna_muestra_la_calificacion_y_0_si_no_se_ha_capturado(curso_ui):
    v = _examen_listo(curso_ui, "Parcial 1")
    columna = _columnas_examen(v)[0][0]
    _calificar(v, "100000001", "42")
    assert _celda(v, "100000001", columna) == "42"
    assert _celda(v, "100000002", columna) == "0"
    _calificar(v, "100000002", "7.5")
    assert _celda(v, "100000002", columna) == "7.5"


def test_la_tabla_muestra_las_columnas_al_abrir_un_curso_con_examenes(curso_ui):
    curso_ui.srv.crear_examen(curso_ui.curso.id, "Parcial 1")
    curso_ui.app.abrir_curso(curso_ui.curso.id)
    curso_ui.app.update()
    assert [t for _c, t in _columnas_examen(curso_ui.app._vista)] == ["Examen - Parcial 1"]


def test_ordenar_por_una_columna_de_examen(curso_ui):
    v = _examen_listo(curso_ui)
    _calificar(v, "100000003", "90")
    _calificar(v, "100000001", "50")
    columna = _columnas_examen(v)[0][0]
    v._ordenar_por(columna)  # primer clic: de mayor a menor
    assert v._tabla.get_children()[0] == str(_fila(v, "100000003").alumno.id)
    assert "▼" in v._tabla.heading(columna, "text")
    v._ordenar_por(columna)
    assert v._tabla.get_children()[-1] == str(_fila(v, "100000003").alumno.id)


# ---------------- gestionar exámenes: renombrar y eliminar ----------------
@pytest.fixture
def preguntas(monkeypatch):
    """Captura las confirmaciones (messagebox.askyesno); `respuesta['si']` decide qué se contesta."""
    from tkinter import messagebox

    registro = SimpleNamespace(mensajes=[], si=True)
    monkeypatch.setattr(
        messagebox, "askyesno", lambda titulo, mensaje, **k: registro.mensajes.append(mensaje) or registro.si
    )
    return registro


def _nombres_examenes(curso_ui):
    return [e.nombre for e in curso_ui.srv.listar_examenes(curso_ui.curso.id)]


def test_renombrar_el_examen_actualiza_lista_y_columna(curso_ui):
    v = _examen_listo(curso_ui, "Parcial 1")
    _calificar(v, "100000001", "42")

    def renombrar():
        d = _dialogo(curso_ui.app)
        assert d._nombre.get() == "Parcial 1"  # parte del nombre actual
        d._nombre.delete(0, "end")
        d._nombre.insert(0, "Primer parcial")
        d._aceptar()

    curso_ui.app.after(300, renombrar)
    v.renombrar_examen()
    assert _nombres_examenes(curso_ui) == ["Primer parcial"]
    assert v._examen_actual.nombre == "Primer parcial" and v._menu_examen.get() == "Primer parcial"
    assert [t for _c, t in _columnas_examen(v)] == ["Examen - Primer parcial"]
    alumno = _fila(v, "100000001").alumno
    assert curso_ui.srv.calificacion_de(v._examen_actual.id, alumno.id).puntos == 42  # conserva notas


def test_renombrar_a_un_nombre_repetido_muestra_el_error_en_el_dialogo(curso_ui):
    v = _examen_listo(curso_ui, "Parcial 1")
    _crear_examen_ui(curso_ui, "Final")

    def repetir():
        d = _dialogo(curso_ui.app)
        d._nombre.delete(0, "end")
        d._nombre.insert(0, "parcial 1")
        d._aceptar()
        assert "Ya existe" in d._error.cget("text")
        d.cancelar()

    curso_ui.app.after(300, repetir)
    v.renombrar_examen()
    assert _nombres_examenes(curso_ui) == ["Parcial 1", "Final"]


def test_eliminar_el_examen_pide_confirmacion_e_informa_cuantas_calificaciones_se_pierden(curso_ui, preguntas):
    v = _examen_listo(curso_ui, "Parcial 1")
    _calificar(v, "100000001", "42")
    _calificar(v, "100000002", "35")
    preguntas.si = False
    v.eliminar_examen()
    assert "2 calificaciones" in preguntas.mensajes[-1] and "Parcial 1" in preguntas.mensajes[-1]
    assert _nombres_examenes(curso_ui) == ["Parcial 1"]  # cancelado: no pasa nada

    preguntas.si = True
    v.eliminar_examen()
    assert _nombres_examenes(curso_ui) == []
    assert v._examen_actual is None and _columnas_examen(v) == []
    assert curso_ui.srv._repo.contar_calificaciones_examen(1) == 0
    assert _texto_franja(v).startswith("✓") or "eliminado" in _texto_franja(v).lower()


def test_eliminar_un_examen_conserva_los_demas_y_elige_otro(curso_ui, preguntas):
    v = _examen_listo(curso_ui, "Parcial 1")
    _crear_examen_ui(curso_ui, "Final")  # queda seleccionado el Final
    v.eliminar_examen()
    assert _nombres_examenes(curso_ui) == ["Parcial 1"]
    assert v._examen_actual.nombre == "Parcial 1"
    assert [t for _c, t in _columnas_examen(v)] == ["Examen - Parcial 1"]


def test_eliminar_un_examen_sin_calificaciones_lo_dice(curso_ui, preguntas):
    v = _examen_listo(curso_ui, "Parcial 1")
    v.eliminar_examen()
    assert "no tiene calificaciones" in preguntas.mensajes[-1].lower()


def test_eliminar_examen_invalida_el_deshacer_de_ese_examen(curso_ui, preguntas):
    v = _examen_listo(curso_ui, "Parcial 1")
    _calificar(v, "100000001", "42")
    v.eliminar_examen()
    v.deshacer()  # no debe fallar ni resucitar nada
    assert _nombres_examenes(curso_ui) == []


def test_sin_examenes_renombrar_y_eliminar_avisan(curso_ui, preguntas):
    v = curso_ui.vista
    _modo_examen(curso_ui)
    v.renombrar_examen()
    assert _texto_franja(v).startswith("⚠")
    v.eliminar_examen()
    assert _texto_franja(v).startswith("⚠") and preguntas.mensajes == []
