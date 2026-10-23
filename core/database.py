"""Conexión y esquema de SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .errores import ErrorDominio
from .rutas import carpeta_datos

RUTA_POR_DEFECTO = carpeta_datos() / "participaciones.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS alumno (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    num_cuenta      TEXT UNIQUE,
    nombre_completo TEXT NOT NULL,
    nombre_norm     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alumno_nombre_norm ON alumno(nombre_norm);

CREATE TABLE IF NOT EXISTS curso (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ciclo     TEXT NOT NULL,
    carrera   TEXT NOT NULL DEFAULT '',
    materia   TEXT NOT NULL,
    grupo     TEXT NOT NULL,
    archivado INTEGER NOT NULL DEFAULT 0,
    UNIQUE (ciclo, materia, grupo)
);

CREATE TABLE IF NOT EXISTS inscripcion (
    curso_id  INTEGER NOT NULL REFERENCES curso(id) ON DELETE CASCADE,
    alumno_id INTEGER NOT NULL REFERENCES alumno(id) ON DELETE CASCADE,
    tipo      TEXT NOT NULL CHECK (tipo IN ('regular', 'oyente')),
    PRIMARY KEY (curso_id, alumno_id)
);

CREATE TABLE IF NOT EXISTS participacion (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    curso_id  INTEGER NOT NULL REFERENCES curso(id) ON DELETE CASCADE,
    alumno_id INTEGER NOT NULL REFERENCES alumno(id) ON DELETE CASCADE,
    decimas   REAL NOT NULL,
    fecha     TEXT NOT NULL,
    nota      TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_participacion_curso_alumno
    ON participacion(curso_id, alumno_id);

CREATE TABLE IF NOT EXISTS examen (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    curso_id    INTEGER NOT NULL REFERENCES curso(id) ON DELETE CASCADE,
    nombre      TEXT NOT NULL,
    nombre_norm TEXT NOT NULL,
    UNIQUE (curso_id, nombre_norm)
);

CREATE TABLE IF NOT EXISTS calificacion_tareas (
    curso_id  INTEGER NOT NULL REFERENCES curso(id) ON DELETE CASCADE,
    alumno_id INTEGER NOT NULL REFERENCES alumno(id) ON DELETE CASCADE,
    puntos    REAL NOT NULL,
    fecha     TEXT NOT NULL,
    PRIMARY KEY (curso_id, alumno_id)
);

CREATE TABLE IF NOT EXISTS calificacion_proyecto (
    curso_id  INTEGER NOT NULL REFERENCES curso(id) ON DELETE CASCADE,
    alumno_id INTEGER NOT NULL REFERENCES alumno(id) ON DELETE CASCADE,
    puntos    REAL NOT NULL,
    fecha     TEXT NOT NULL,
    PRIMARY KEY (curso_id, alumno_id)
);

CREATE TABLE IF NOT EXISTS ponderacion (
    curso_id        INTEGER PRIMARY KEY REFERENCES curso(id) ON DELETE CASCADE,
    participaciones REAL NOT NULL,
    examenes        REAL NOT NULL,
    tareas          REAL NOT NULL,
    proyecto        REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS equipo (
    curso_id INTEGER NOT NULL REFERENCES curso(id) ON DELETE CASCADE,
    numero   INTEGER NOT NULL,
    nombre   TEXT NOT NULL DEFAULT '',
    proyecto TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (curso_id, numero)
);

CREATE TABLE IF NOT EXISTS miembro_equipo (
    curso_id  INTEGER NOT NULL,
    alumno_id INTEGER NOT NULL REFERENCES alumno(id) ON DELETE CASCADE,
    numero    INTEGER NOT NULL,
    PRIMARY KEY (curso_id, alumno_id),
    FOREIGN KEY (curso_id, numero) REFERENCES equipo(curso_id, numero) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS calificacion (
    examen_id INTEGER NOT NULL REFERENCES examen(id) ON DELETE CASCADE,
    alumno_id INTEGER NOT NULL REFERENCES alumno(id) ON DELETE CASCADE,
    puntos    REAL NOT NULL,
    fecha     TEXT NOT NULL,
    PRIMARY KEY (examen_id, alumno_id)
);
"""


def conectar(ruta: str | Path = RUTA_POR_DEFECTO) -> sqlite3.Connection:
    """Abre la base (la crea si no existe) con claves foráneas activas."""
    if str(ruta) != ":memory:":
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.executescript(ESQUEMA)
    _migrar(conexion)
    return conexion


def _migrar(conexion: sqlite3.Connection) -> None:
    """Agrega a una base ya existente lo que `CREATE TABLE IF NOT EXISTS` no puede: columnas nuevas."""
    columnas = {f["name"] for f in conexion.execute("PRAGMA table_info(equipo)")}
    for nombre in ("nombre", "proyecto"):  # los equipos de la versión 1.4.0 no tenían nombre ni proyecto
        if nombre not in columnas:
            conexion.execute(f"ALTER TABLE equipo ADD COLUMN {nombre} TEXT NOT NULL DEFAULT ''")
    conexion.commit()


def respaldar(conexion: sqlite3.Connection, carpeta: str | Path, conservar: int = 10) -> Path:
    """Copia consistente de la base en `carpeta`; conserva solo los `conservar` más recientes."""
    from datetime import datetime

    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"participaciones_{datetime.now():%Y%m%d_%H%M%S}.db"
    copia = sqlite3.connect(destino)
    try:
        conexion.commit()
        conexion.backup(copia)
    finally:
        copia.close()
    antiguos = sorted(carpeta.glob("participaciones_*.db"))[:-conservar]
    for archivo in antiguos:
        archivo.unlink(missing_ok=True)
    return destino


# ---- exportar e importar la base completa (R19) ---------------------------
_TABLAS_BASE = ("alumno", "curso", "inscripcion", "participacion")  # sin ellas no es una base de la app


def _ruta_de(conexion: sqlite3.Connection) -> Path | None:
    for _, nombre, archivo in conexion.execute("PRAGMA database_list"):
        if nombre == "main" and archivo:
            return Path(archivo)
    return None  # en memoria


def _estructura(conexion: sqlite3.Connection) -> dict[str, set[str]]:
    tablas = [f[0] for f in conexion.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    return {t: {c[1] for c in conexion.execute(f'PRAGMA table_info("{t}")')} for t in tablas}


def exportar_base(conexion: sqlite3.Connection, destino: str | Path) -> Path:
    """Copia consistente de toda la base en `destino` (sobrescribe si existe). No modifica el origen."""
    destino = Path(destino)
    if not destino.parent.is_dir():
        raise ErrorDominio(f"La carpeta «{destino.parent}» no existe.")
    origen = _ruta_de(conexion)
    if origen is not None and destino.resolve() == origen.resolve():
        raise ErrorDominio("El destino es la base en uso; elige otro archivo.")
    conexion.commit()
    copia = None
    try:
        copia = sqlite3.connect(destino)
        conexion.backup(copia)
    except (sqlite3.Error, OSError) as error:
        raise ErrorDominio(
            f"No se pudo guardar «{destino.name}»: revisa que no esté abierto y que haya permisos ({error})."
        ) from error
    finally:
        if copia is not None:
            copia.close()
    return destino


def abrir_base_externa(ruta: str | Path) -> sqlite3.Connection:
    """Valida un `.db` ajeno y devuelve una copia EN MEMORIA ya migrada al esquema actual.

    El archivo original nunca se modifica. Rechaza lo que no es una base de la app o es de una
    versión más nueva (tablas o columnas que esta versión no conoce)."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise ErrorDominio(f"No se encontró el archivo «{ruta.name}».")
    origen = copia = None
    try:
        origen = sqlite3.connect(f"{ruta.resolve().as_uri()}?mode=ro", uri=True)
        copia = sqlite3.connect(":memory:")
        origen.backup(copia)  # falla aquí si no es SQLite
        copia.row_factory = sqlite3.Row
        ajena = _estructura(copia)
    except sqlite3.Error as error:
        if copia is not None:
            copia.close()
        raise ErrorDominio(f"«{ruta.name}» no es una base de Participaciones válida.") from error
    finally:
        if origen is not None:
            origen.close()
    if not all(t in ajena for t in _TABLAS_BASE):
        copia.close()
        raise ErrorDominio(f"«{ruta.name}» no es una base de Participaciones (faltan tablas).")
    esperada = _estructura(conectar(":memory:"))
    if any(t not in esperada or not c <= esperada[t] for t, c in ajena.items()):
        copia.close()
        raise ErrorDominio(
            f"«{ruta.name}» parece de una versión más nueva de la aplicación; actualiza esta versión."
        )
    copia.executescript(ESQUEMA)  # tablas que la versión de origen aún no tenía
    _migrar(copia)
    return copia


def reemplazar_contenido(conexion: sqlite3.Connection, origen: sqlite3.Connection) -> None:
    """Deja `conexion` con exactamente el contenido de `origen`, sin cerrarla."""
    conexion.commit()
    try:
        origen.backup(conexion)
    except sqlite3.Error as error:
        raise ErrorDominio(f"No se pudo reemplazar la base: {error}") from error
