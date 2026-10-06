"""Acceso a datos. Es el ÚNICO módulo que contiene SQL."""

from __future__ import annotations

import sqlite3
from datetime import date

from .models import (
    Alumno,
    Curso,
    Participacion,
    ResumenAlumno,
    TipoInscripcion,
)
from .normalizacion import limpiar_nombre, normalizar
from .puntaje import total_con_piso


def _alumno(fila: sqlite3.Row) -> Alumno:
    return Alumno(
        id=fila["id"],
        nombre_completo=fila["nombre_completo"],
        num_cuenta=fila["num_cuenta"],
    )


def _curso(fila: sqlite3.Row) -> Curso:
    return Curso(
        id=fila["id"],
        ciclo=fila["ciclo"],
        carrera=fila["carrera"],
        materia=fila["materia"],
        grupo=fila["grupo"],
        archivado=bool(fila["archivado"]),
    )


def _participacion(fila: sqlite3.Row) -> Participacion:
    return Participacion(
        id=fila["id"],
        curso_id=fila["curso_id"],
        alumno_id=fila["alumno_id"],
        decimas=fila["decimas"],
        fecha=date.fromisoformat(fila["fecha"]),
        nota=fila["nota"],
    )


def _patron_like(token: str) -> str:
    escapado = token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"


class Repositorio:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._db = conexion

    # ---- transacciones -------------------------------------------------
    def transaccion(self) -> sqlite3.Connection:
        """Uso: `with repo.transaccion(): ...` (commit, o rollback si hay error)."""
        return self._db

    # ---- cursos --------------------------------------------------------
    def insertar_curso(self, curso: Curso) -> Curso:
        cur = self._db.execute(
            "INSERT INTO curso (ciclo, carrera, materia, grupo, archivado)"
            " VALUES (?, ?, ?, ?, ?)",
            (curso.ciclo, curso.carrera, curso.materia, curso.grupo, int(curso.archivado)),
        )
        curso.id = cur.lastrowid
        return curso

    def obtener_curso(self, curso_id: int) -> Curso | None:
        fila = self._db.execute("SELECT * FROM curso WHERE id = ?", (curso_id,)).fetchone()
        return _curso(fila) if fila else None

    def buscar_curso_por_clave(self, ciclo: str, materia: str, grupo: str) -> Curso | None:
        fila = self._db.execute(
            "SELECT * FROM curso WHERE ciclo = ? AND materia = ? AND grupo = ?",
            (ciclo, materia, grupo),
        ).fetchone()
        return _curso(fila) if fila else None

    def listar_cursos(self, incluir_archivados: bool = False) -> list[Curso]:
        sql = "SELECT * FROM curso"
        if not incluir_archivados:
            sql += " WHERE archivado = 0"
        sql += " ORDER BY ciclo DESC, materia, grupo"
        return [_curso(f) for f in self._db.execute(sql)]

    def actualizar_curso(self, curso: Curso) -> None:
        self._db.execute(
            "UPDATE curso SET ciclo=?, carrera=?, materia=?, grupo=?, archivado=?"
            " WHERE id=?",
            (curso.ciclo, curso.carrera, curso.materia, curso.grupo,
             int(curso.archivado), curso.id),
        )

    def eliminar_curso(self, curso_id: int) -> None:
        self._db.execute("DELETE FROM curso WHERE id = ?", (curso_id,))

    def contar_participaciones_curso(self, curso_id: int) -> int:
        return self._db.execute(
            "SELECT COUNT(*) FROM participacion WHERE curso_id = ?", (curso_id,)
        ).fetchone()[0]

    def contar_alumnos_curso(self, curso_id: int) -> int:
        return self._db.execute(
            "SELECT COUNT(*) FROM inscripcion WHERE curso_id = ?", (curso_id,)
        ).fetchone()[0]

    # ---- alumnos -------------------------------------------------------
    def insertar_alumno(self, alumno: Alumno) -> Alumno:
        alumno.nombre_completo = limpiar_nombre(alumno.nombre_completo)
        cur = self._db.execute(
            "INSERT INTO alumno (num_cuenta, nombre_completo, nombre_norm)"
            " VALUES (?, ?, ?)",
            (alumno.num_cuenta, alumno.nombre_completo, normalizar(alumno.nombre_completo)),
        )
        alumno.id = cur.lastrowid
        return alumno

    def actualizar_alumno(self, alumno: Alumno) -> None:
        alumno.nombre_completo = limpiar_nombre(alumno.nombre_completo)
        self._db.execute(
            "UPDATE alumno SET num_cuenta=?, nombre_completo=?, nombre_norm=? WHERE id=?",
            (alumno.num_cuenta, alumno.nombre_completo,
             normalizar(alumno.nombre_completo), alumno.id),
        )

    def obtener_alumno(self, alumno_id: int) -> Alumno | None:
        fila = self._db.execute("SELECT * FROM alumno WHERE id = ?", (alumno_id,)).fetchone()
        return _alumno(fila) if fila else None

    def buscar_alumno_por_cuenta(self, num_cuenta: str) -> Alumno | None:
        fila = self._db.execute(
            "SELECT * FROM alumno WHERE num_cuenta = ?", (num_cuenta,)
        ).fetchone()
        return _alumno(fila) if fila else None

    def buscar_alumnos_sin_cuenta_por_nombre(self, nombre: str) -> list[Alumno]:
        filas = self._db.execute(
            "SELECT * FROM alumno WHERE num_cuenta IS NULL AND nombre_norm = ?"
            " ORDER BY id",
            (normalizar(nombre),),
        )
        return [_alumno(f) for f in filas]

    def buscar_alumnos(self, tokens: list[str], curso_id: int | None = None) -> list[Alumno]:
        """Alumnos cuyo nombre contiene TODOS los tokens (ya normalizados).

        Con `curso_id`, solo los inscritos en ese curso; sin él, de todo el sistema.
        """
        sql = "SELECT a.* FROM alumno a"
        params: list = []
        if curso_id is not None:
            sql += " JOIN inscripcion i ON i.alumno_id = a.id AND i.curso_id = ?"
            params.append(curso_id)
        condiciones = []
        for token in tokens:
            condiciones.append("a.nombre_norm LIKE ? ESCAPE '\\'")
            params.append(_patron_like(token))
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " ORDER BY a.nombre_norm"
        return [_alumno(f) for f in self._db.execute(sql, params)]

    def buscar_alumno_en_curso_por_cuenta(
        self, curso_id: int, num_cuenta: str
    ) -> Alumno | None:
        fila = self._db.execute(
            "SELECT a.* FROM alumno a JOIN inscripcion i ON i.alumno_id = a.id"
            " WHERE i.curso_id = ? AND a.num_cuenta = ?",
            (curso_id, num_cuenta),
        ).fetchone()
        return _alumno(fila) if fila else None

    # ---- inscripciones -------------------------------------------------
    def obtener_tipo_inscripcion(
        self, curso_id: int, alumno_id: int
    ) -> TipoInscripcion | None:
        fila = self._db.execute(
            "SELECT tipo FROM inscripcion WHERE curso_id = ? AND alumno_id = ?",
            (curso_id, alumno_id),
        ).fetchone()
        return TipoInscripcion(fila["tipo"]) if fila else None

    def guardar_inscripcion(
        self, curso_id: int, alumno_id: int, tipo: TipoInscripcion
    ) -> None:
        self._db.execute(
            "INSERT INTO inscripcion (curso_id, alumno_id, tipo) VALUES (?, ?, ?)"
            " ON CONFLICT (curso_id, alumno_id) DO UPDATE SET tipo = excluded.tipo",
            (curso_id, alumno_id, tipo.value),
        )

    def decimas_por_alumno(self, curso_id: int) -> dict[int, list[float]]:
        """Décimas de cada alumno del curso en orden cronológico (para aplicar el piso)."""
        por_alumno: dict[int, list[float]] = {}
        filas = self._db.execute(
            "SELECT alumno_id, decimas FROM participacion WHERE curso_id = ?"
            " ORDER BY fecha, id",
            (curso_id,),
        )
        for f in filas:
            por_alumno.setdefault(f["alumno_id"], []).append(f["decimas"])
        return por_alumno

    def resumen_curso(self, curso_id: int) -> list[ResumenAlumno]:
        decimas = self.decimas_por_alumno(curso_id)
        filas = self._db.execute(
            "SELECT a.id, a.num_cuenta, a.nombre_completo, i.tipo,"
            "       COUNT(p.id) AS n, MAX(p.fecha) AS ultima"
            " FROM inscripcion i"
            " JOIN alumno a ON a.id = i.alumno_id"
            " LEFT JOIN participacion p"
            "   ON p.curso_id = i.curso_id AND p.alumno_id = i.alumno_id"
            " WHERE i.curso_id = ?"
            " GROUP BY a.id ORDER BY a.nombre_norm",
            (curso_id,),
        )
        return [
            ResumenAlumno(
                alumno=_alumno(f),
                tipo=TipoInscripcion(f["tipo"]),
                total=total_con_piso(decimas.get(f["id"], [])),
                n_participaciones=f["n"],
                ultima_fecha=date.fromisoformat(f["ultima"]) if f["ultima"] else None,
            )
            for f in filas
        ]

    def cursos_de_alumno(self, alumno_id: int) -> list[Curso]:
        filas = self._db.execute(
            "SELECT c.* FROM curso c JOIN inscripcion i ON i.curso_id = c.id"
            " WHERE i.alumno_id = ? ORDER BY c.ciclo DESC, c.materia, c.grupo",
            (alumno_id,),
        )
        return [_curso(f) for f in filas]

    # ---- participaciones -----------------------------------------------
    def insertar_participacion(self, p: Participacion) -> Participacion:
        cur = self._db.execute(
            "INSERT INTO participacion (curso_id, alumno_id, decimas, fecha, nota)"
            " VALUES (?, ?, ?, ?, ?)",
            (p.curso_id, p.alumno_id, p.decimas, p.fecha.isoformat(), p.nota),
        )
        p.id = cur.lastrowid
        return p

    def obtener_participacion(self, participacion_id: int) -> Participacion | None:
        fila = self._db.execute(
            "SELECT * FROM participacion WHERE id = ?", (participacion_id,)
        ).fetchone()
        return _participacion(fila) if fila else None

    def actualizar_participacion(self, p: Participacion) -> None:
        self._db.execute(
            "UPDATE participacion SET decimas=?, fecha=?, nota=? WHERE id=?",
            (p.decimas, p.fecha.isoformat(), p.nota, p.id),
        )

    def eliminar_participacion(self, participacion_id: int) -> None:
        self._db.execute("DELETE FROM participacion WHERE id = ?", (participacion_id,))

    def listar_participaciones(self, curso_id: int, alumno_id: int) -> list[Participacion]:
        filas = self._db.execute(
            "SELECT * FROM participacion WHERE curso_id = ? AND alumno_id = ?"
            " ORDER BY fecha DESC, id DESC",
            (curso_id, alumno_id),
        )
        return [_participacion(f) for f in filas]

    def total_alumno(self, curso_id: int, alumno_id: int) -> float:
        """Total del alumno en el curso, con el piso de 0 aplicado cronológicamente."""
        filas = self._db.execute(
            "SELECT decimas FROM participacion WHERE curso_id = ? AND alumno_id = ?"
            " ORDER BY fecha, id",
            (curso_id, alumno_id),
        )
        return total_con_piso(f["decimas"] for f in filas)
