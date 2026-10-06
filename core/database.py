"""Conexión y esquema de SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

RUTA_POR_DEFECTO = Path(__file__).resolve().parent.parent / "data" / "participaciones.db"

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
"""


def conectar(ruta: str | Path = RUTA_POR_DEFECTO) -> sqlite3.Connection:
    """Abre la base (la crea si no existe) con claves foráneas activas."""
    if str(ruta) != ":memory:":
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.executescript(ESQUEMA)
    return conexion


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
