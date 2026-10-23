"""Reemplazar toda la base por la de un archivo, con respaldo previo y deshacer (R19; datos ficticios)."""

import pytest

from core.database import conectar
from core.errores import ErrorDominio
from core.models import FilaLista, ListaInscripcion
from core.repository import Repositorio
from core.services import ServicioParticipaciones


def _lista(materia, grupo, cuentas):
    return ListaInscripcion(
        "2027-I", "ING", materia, grupo,
        [FilaLista(i, c, f"ALUMNO FICTICIO {c}") for i, c in enumerate(cuentas, 1)],
    )


def _servicio(ruta):
    conexion = conectar(ruta)
    return ServicioParticipaciones(Repositorio(conexion)), conexion


@pytest.fixture
def dos_bases(tmp_path):
    """Laptop: 2 cursos con participaciones, exámenes y equipo. Aquí: 1 curso distinto."""
    laptop, c1 = _servicio(tmp_path / "laptop.db")
    redes = laptop.importar_lista(_lista("REDES", "3001", ["100000001", "100000002"])).curso
    laptop.importar_lista(_lista("AUTOMATAS", "1509", ["100000003"]))
    a = laptop.buscar_alumnos_en_curso(redes.id, "100000001")[0]
    laptop.registrar_para_alumno(redes.id, a.id, 8)
    laptop.registrar_para_alumno(redes.id, a.id, -3)
    examen = laptop.crear_examen(redes.id, "Parcial 1")
    laptop.registrar_calificacion_para_alumno(redes.id, examen.id, a.id, 7.5)
    laptop.exportar_base(tmp_path / "viaje.db")
    local, c2 = _servicio(tmp_path / "aqui.db")
    otro = local.importar_lista(_lista("BASES", "2002", ["100000009"])).curso
    local.registrar_para_alumno(otro.id, local.buscar_alumnos_en_curso(otro.id, "100000009")[0].id, 4)
    yield laptop, local, tmp_path
    c1.close()
    c2.close()


def _foto(servicio):
    """Todo lo observable por curso: total y finales por alumno."""
    foto = {}
    for curso in servicio.listar_cursos(incluir_archivados=True):
        foto[(curso.ciclo, curso.materia, curso.grupo)] = sorted(
            (f.alumno.num_cuenta, f.total, servicio.desglose_final(curso.id, f.alumno.id).final)
            for f in servicio.resumen_curso(curso.id)
        )
    return foto


def test_reemplazar_deja_la_base_igual_al_archivo(dos_bases):
    laptop, local, tmp = dos_bases
    resultado = local.reemplazar_base(tmp / "viaje.db", tmp / "respaldos")
    assert resultado == laptop.resumen_base_local()
    assert _foto(local) == _foto(laptop)
    assert "BASES" not in {k[1] for k in _foto(local)}


def test_reemplazar_respalda_lo_local_antes(dos_bases):
    _, local, tmp = dos_bases
    antes = local.resumen_base_local()
    local.reemplazar_base(tmp / "viaje.db", tmp / "respaldos")
    respaldos = list((tmp / "respaldos").glob("participaciones_*.db"))
    assert len(respaldos) == 1
    assert local.resumen_base_archivo(respaldos[0]) == antes


def test_el_total_sigue_respetando_el_minimo_de_cero_tras_reemplazar(dos_bases):
    _, local, tmp = dos_bases
    local.reemplazar_base(tmp / "viaje.db", tmp / "respaldos")
    curso = next(c for c in local.listar_cursos() if c.materia == "REDES")
    a = local.buscar_alumnos_en_curso(curso.id, "100000001")[0]
    assert local.total_alumno(curso.id, a.id) == 5  # +8 y -3


def test_deshacer_importacion_devuelve_la_base_de_antes(dos_bases):
    _, local, tmp = dos_bases
    antes = _foto(local)
    local.reemplazar_base(tmp / "viaje.db", tmp / "respaldos")
    assert local.hay_importacion_por_deshacer
    local.deshacer_importacion()
    assert _foto(local) == antes
    assert not local.hay_importacion_por_deshacer


def test_deshacer_sin_importacion_da_mensaje(dos_bases):
    _, local, _ = dos_bases
    with pytest.raises(ErrorDominio, match="ninguna importación"):
        local.deshacer_importacion()


def test_un_archivo_invalido_no_toca_nada(dos_bases):
    _, local, tmp = dos_bases
    malo = tmp / "malo.db"
    malo.write_text("no soy una base " * 40)
    antes = _foto(local)
    with pytest.raises(ErrorDominio):
        local.reemplazar_base(malo, tmp / "respaldos")
    assert _foto(local) == antes
    assert not (tmp / "respaldos").exists()
    assert not local.hay_importacion_por_deshacer


def test_la_conexion_sigue_viva_y_acepta_escrituras_tras_reemplazar(dos_bases):
    _, local, tmp = dos_bases
    local.reemplazar_base(tmp / "viaje.db", tmp / "respaldos")
    curso = next(c for c in local.listar_cursos() if c.materia == "AUTOMATAS")
    a = local.buscar_alumnos_en_curso(curso.id, "100000003")[0]
    local.registrar_para_alumno(curso.id, a.id, 2)
    assert local.total_alumno(curso.id, a.id) == 2


def test_el_archivo_importado_no_cambia(dos_bases):
    _, local, tmp = dos_bases
    ruta = tmp / "viaje.db"
    antes = ruta.read_bytes()
    local.reemplazar_base(ruta, tmp / "respaldos")
    assert ruta.read_bytes() == antes
