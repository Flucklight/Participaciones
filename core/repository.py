"""Acceso a datos. Es el ÚNICO módulo que contiene SQL."""

from __future__ import annotations

import sqlite3
from datetime import date

from .models import (
    Alumno,
    Calificacion,
    CalificacionProyecto,
    CalificacionTareas,
    Curso,
    Examen,
    InstantaneaAlumno,
    Participacion,
    ResumenAlumno,
    ResumenBase,
    TipoInscripcion,
)
from .calificacion_final import Ponderaciones
from .normalizacion import limpiar_nombre, normalizar
from .promedio import promedio_examenes
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


def _examen(fila: sqlite3.Row) -> Examen:
    return Examen(id=fila["id"], curso_id=fila["curso_id"], nombre=fila["nombre"])


def _calificacion(fila: sqlite3.Row) -> Calificacion:
    return Calificacion(
        examen_id=fila["examen_id"],
        alumno_id=fila["alumno_id"],
        puntos=fila["puntos"],
        fecha=date.fromisoformat(fila["fecha"]),
    )


def _proyecto(fila: sqlite3.Row) -> CalificacionProyecto:
    return CalificacionProyecto(
        curso_id=fila["curso_id"],
        alumno_id=fila["alumno_id"],
        puntos=fila["puntos"],
        fecha=date.fromisoformat(fila["fecha"]),
    )


def _tareas(fila: sqlite3.Row) -> CalificacionTareas:
    return CalificacionTareas(
        curso_id=fila["curso_id"],
        alumno_id=fila["alumno_id"],
        puntos=fila["puntos"],
        fecha=date.fromisoformat(fila["fecha"]),
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

    @property
    def conexion(self) -> sqlite3.Connection:
        """Solo para copiar o restaurar la base completa (`core.database`); no para consultas."""
        return self._db

    def contar_contenido(self) -> ResumenBase:
        def contar(tabla: str) -> int:
            return self._db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]

        return ResumenBase(contar("curso"), contar("alumno"), contar("participacion"))

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

    def buscar_alumnos_por_nombre(self, nombre: str) -> list[Alumno]:
        """Alumnos (con o sin cuenta) cuyo nombre normalizado es exactamente `nombre` normalizado."""
        filas = self._db.execute(
            "SELECT * FROM alumno WHERE nombre_norm = ? ORDER BY id", (normalizar(nombre),)
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
        examenes = [e.id for e in self.listar_examenes(curso_id)]
        puntos = self.puntos_por_alumno(curso_id)
        tareas = self.tareas_por_alumno(curso_id)
        equipos = self.equipos_por_alumno(curso_id)
        proyecto = self.proyecto_por_alumno(curso_id)
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
                prom_examenes=promedio_examenes(
                    [puntos.get(f["id"], {}).get(e, 0.0) for e in examenes]
                ),
                calificaciones=dict(puntos.get(f["id"], {})),
                tareas=tareas.get(f["id"], 0.0),
                equipo=equipos.get(f["id"]),
                proyecto=proyecto.get(f["id"], 0.0),
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

    def capturar_alumno_en_curso(self, curso_id: int, alumno_id: int) -> InstantaneaAlumno | None:
        """Todo lo del alumno en el curso (None si no está inscrito), para eliminarlo o deshacer."""
        alumno = self.obtener_alumno(alumno_id)
        tipo = self.obtener_tipo_inscripcion(curso_id, alumno_id)
        if alumno is None or tipo is None:
            return None
        califs = self._db.execute(
            "SELECT c.* FROM calificacion c JOIN examen e ON e.id = c.examen_id"
            " WHERE e.curso_id = ? AND c.alumno_id = ? ORDER BY c.examen_id",
            (curso_id, alumno_id),
        )
        en_otros = self._db.execute(
            "SELECT COUNT(*) FROM inscripcion WHERE alumno_id = ? AND curso_id <> ?",
            (alumno_id, curso_id),
        ).fetchone()[0]
        return InstantaneaAlumno(
            curso_id=curso_id,
            alumno=alumno,
            tipo=tipo,
            participaciones=sorted(
                self.listar_participaciones(curso_id, alumno_id), key=lambda p: (p.fecha, p.id)
            ),
            calificaciones=[_calificacion(f) for f in califs],
            tareas=self.obtener_tareas(curso_id, alumno_id),
            proyecto=self.obtener_proyecto(curso_id, alumno_id),
            equipo=self.equipo_de(curso_id, alumno_id),
            alumno_borrado=en_otros == 0,
        )

    def eliminar_alumno_de_curso(self, curso_id: int, alumno_id: int) -> None:
        """Quita al alumno de ESE curso con todo lo suyo ahí; si no queda inscrito en otro, borra al alumno.
        Los equipos no se tocan (un equipo vacío conserva su número)."""
        self._db.execute(
            "DELETE FROM calificacion WHERE alumno_id = ? AND examen_id IN"
            " (SELECT id FROM examen WHERE curso_id = ?)",
            (alumno_id, curso_id),
        )
        for tabla in ("participacion", "calificacion_tareas", "calificacion_proyecto", "miembro_equipo",
                      "inscripcion"):
            self._db.execute(f"DELETE FROM {tabla} WHERE curso_id = ? AND alumno_id = ?", (curso_id, alumno_id))
        self._db.execute(
            "DELETE FROM alumno WHERE id = ? AND NOT EXISTS (SELECT 1 FROM inscripcion WHERE alumno_id = ?)",
            (alumno_id, alumno_id),
        )

    def restaurar_alumno_en_curso(self, s: InstantaneaAlumno) -> Alumno:
        """Inverso de `eliminar_alumno_de_curso`. Si hubo que borrar al alumno se vuelve a crear (con
        otro id); las participaciones se reinsertan en su orden (fecha, id). No valida: lo hace el servicio."""
        alumno = s.alumno
        if s.alumno_borrado:
            alumno = self.insertar_alumno(Alumno(None, alumno.nombre_completo, alumno.num_cuenta))
        self.guardar_inscripcion(s.curso_id, alumno.id, s.tipo)
        for p in s.participaciones:
            self.insertar_participacion(Participacion(None, s.curso_id, alumno.id, p.decimas, p.fecha, p.nota))
        for c in s.calificaciones:
            self.guardar_calificacion(Calificacion(c.examen_id, alumno.id, c.puntos, c.fecha))
        if s.tareas:
            self.guardar_tareas(CalificacionTareas(s.curso_id, alumno.id, s.tareas.puntos, s.tareas.fecha))
        if s.proyecto:
            self.guardar_proyecto(CalificacionProyecto(s.curso_id, alumno.id, s.proyecto.puntos, s.proyecto.fecha))
        if s.equipo is not None:
            self.agregar_miembro_equipo(s.curso_id, alumno.id, s.equipo)
        return alumno

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

    # ---- exámenes y calificaciones --------------------------------------
    def insertar_examen(self, examen: Examen) -> Examen:
        cur = self._db.execute(
            "INSERT INTO examen (curso_id, nombre, nombre_norm) VALUES (?, ?, ?)",
            (examen.curso_id, examen.nombre, normalizar(examen.nombre)),
        )
        examen.id = cur.lastrowid
        return examen

    def obtener_examen(self, examen_id: int) -> Examen | None:
        fila = self._db.execute("SELECT * FROM examen WHERE id = ?", (examen_id,)).fetchone()
        return _examen(fila) if fila else None

    def buscar_examen_por_nombre(self, curso_id: int, nombre: str) -> Examen | None:
        fila = self._db.execute(
            "SELECT * FROM examen WHERE curso_id = ? AND nombre_norm = ?",
            (curso_id, normalizar(nombre)),
        ).fetchone()
        return _examen(fila) if fila else None

    def listar_examenes(self, curso_id: int) -> list[Examen]:
        filas = self._db.execute(
            "SELECT * FROM examen WHERE curso_id = ? ORDER BY id", (curso_id,)
        )
        return [_examen(f) for f in filas]

    def actualizar_examen(self, examen: Examen) -> None:
        self._db.execute(
            "UPDATE examen SET nombre = ?, nombre_norm = ? WHERE id = ?",
            (examen.nombre, normalizar(examen.nombre), examen.id),
        )

    def eliminar_examen(self, examen_id: int) -> None:
        self._db.execute("DELETE FROM examen WHERE id = ?", (examen_id,))

    def contar_examenes_curso(self, curso_id: int) -> int:
        return self._db.execute(
            "SELECT COUNT(*) FROM examen WHERE curso_id = ?", (curso_id,)
        ).fetchone()[0]

    def contar_calificaciones_curso(self, curso_id: int) -> int:
        return self._db.execute(
            "SELECT COUNT(*) FROM calificacion c JOIN examen e ON e.id = c.examen_id"
            " WHERE e.curso_id = ?",
            (curso_id,),
        ).fetchone()[0]

    def contar_calificaciones_examen(self, examen_id: int) -> int:
        return self._db.execute(
            "SELECT COUNT(*) FROM calificacion WHERE examen_id = ?", (examen_id,)
        ).fetchone()[0]

    def guardar_calificacion(self, c: Calificacion) -> None:
        """Alta o reemplazo: hay una sola calificación por alumno y examen."""
        self._db.execute(
            "INSERT INTO calificacion (examen_id, alumno_id, puntos, fecha) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (examen_id, alumno_id) DO UPDATE SET puntos = excluded.puntos,"
            " fecha = excluded.fecha",
            (c.examen_id, c.alumno_id, c.puntos, c.fecha.isoformat()),
        )

    def obtener_calificacion(self, examen_id: int, alumno_id: int) -> Calificacion | None:
        fila = self._db.execute(
            "SELECT * FROM calificacion WHERE examen_id = ? AND alumno_id = ?",
            (examen_id, alumno_id),
        ).fetchone()
        return _calificacion(fila) if fila else None

    def eliminar_calificacion(self, examen_id: int, alumno_id: int) -> None:
        self._db.execute(
            "DELETE FROM calificacion WHERE examen_id = ? AND alumno_id = ?",
            (examen_id, alumno_id),
        )

    def puntos_por_alumno(self, curso_id: int) -> dict[int, dict[int, float]]:
        """{alumno_id: {examen_id: puntos}} de los exámenes del curso (solo los capturados)."""
        por_alumno: dict[int, dict[int, float]] = {}
        filas = self._db.execute(
            "SELECT c.alumno_id, c.examen_id, c.puntos FROM calificacion c"
            " JOIN examen e ON e.id = c.examen_id WHERE e.curso_id = ?",
            (curso_id,),
        )
        for f in filas:
            por_alumno.setdefault(f["alumno_id"], {})[f["examen_id"]] = f["puntos"]
        return por_alumno

    # ---- calificación de tareas -------------------------------------------
    def obtener_tareas(self, curso_id: int, alumno_id: int) -> CalificacionTareas | None:
        fila = self._db.execute(
            "SELECT * FROM calificacion_tareas WHERE curso_id = ? AND alumno_id = ?",
            (curso_id, alumno_id),
        ).fetchone()
        return _tareas(fila) if fila else None

    def guardar_tareas(self, c: CalificacionTareas) -> None:
        """Alta o reemplazo: hay una sola calificación de tareas por alumno y curso."""
        self._db.execute(
            "INSERT INTO calificacion_tareas (curso_id, alumno_id, puntos, fecha) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (curso_id, alumno_id) DO UPDATE SET puntos = excluded.puntos,"
            " fecha = excluded.fecha",
            (c.curso_id, c.alumno_id, c.puntos, c.fecha.isoformat()),
        )

    def eliminar_tareas(self, curso_id: int, alumno_id: int) -> None:
        self._db.execute(
            "DELETE FROM calificacion_tareas WHERE curso_id = ? AND alumno_id = ?",
            (curso_id, alumno_id),
        )

    def tareas_por_alumno(self, curso_id: int) -> dict[int, float]:
        """{alumno_id: puntos} de los alumnos del curso con calificación de tareas capturada."""
        filas = self._db.execute(
            "SELECT alumno_id, puntos FROM calificacion_tareas WHERE curso_id = ?", (curso_id,)
        )
        return {f["alumno_id"]: f["puntos"] for f in filas}

    # ---- calificación del proyecto final ----------------------------------------
    def obtener_proyecto(self, curso_id: int, alumno_id: int) -> CalificacionProyecto | None:
        fila = self._db.execute(
            "SELECT * FROM calificacion_proyecto WHERE curso_id = ? AND alumno_id = ?",
            (curso_id, alumno_id),
        ).fetchone()
        return _proyecto(fila) if fila else None

    def guardar_proyecto(self, c: CalificacionProyecto) -> None:
        """Alta o reemplazo: hay una sola calificación de proyecto por alumno y curso."""
        self._db.execute(
            "INSERT INTO calificacion_proyecto (curso_id, alumno_id, puntos, fecha) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (curso_id, alumno_id) DO UPDATE SET puntos = excluded.puntos,"
            " fecha = excluded.fecha",
            (c.curso_id, c.alumno_id, c.puntos, c.fecha.isoformat()),
        )

    def eliminar_proyecto(self, curso_id: int, alumno_id: int) -> None:
        self._db.execute(
            "DELETE FROM calificacion_proyecto WHERE curso_id = ? AND alumno_id = ?",
            (curso_id, alumno_id),
        )

    def proyecto_por_alumno(self, curso_id: int) -> dict[int, float]:
        """{alumno_id: puntos} de los alumnos del curso con calificación de proyecto capturada."""
        filas = self._db.execute(
            "SELECT alumno_id, puntos FROM calificacion_proyecto WHERE curso_id = ?", (curso_id,)
        )
        return {f["alumno_id"]: f["puntos"] for f in filas}

    def contar_proyecto_curso(self, curso_id: int) -> int:
        return self._db.execute(
            "SELECT COUNT(*) FROM calificacion_proyecto WHERE curso_id = ?", (curso_id,)
        ).fetchone()[0]

    # ---- ponderaciones de la calificación final ---------------------------------
    def obtener_ponderaciones(self, curso_id: int) -> Ponderaciones | None:
        """Las ponderaciones guardadas del curso, o None si nunca se guardaron."""
        f = self._db.execute("SELECT * FROM ponderacion WHERE curso_id = ?", (curso_id,)).fetchone()
        if f is None:
            return None
        return Ponderaciones(f["participaciones"], f["examenes"], f["tareas"], f["proyecto"])

    def guardar_ponderaciones(self, curso_id: int, p: Ponderaciones) -> None:
        self._db.execute(
            "INSERT INTO ponderacion (curso_id, participaciones, examenes, tareas, proyecto)"
            " VALUES (?, ?, ?, ?, ?) ON CONFLICT (curso_id) DO UPDATE SET"
            " participaciones = excluded.participaciones, examenes = excluded.examenes,"
            " tareas = excluded.tareas, proyecto = excluded.proyecto",
            (curso_id, p.participaciones, p.examenes, p.tareas, p.proyecto),
        )

    # ---- equipos de proyecto ----------------------------------------------
    def siguiente_numero_equipo(self, curso_id: int) -> int:
        """Máximo histórico + 1: los equipos vacíos no se borran, así que un número no se reutiliza."""
        return self._db.execute(
            "SELECT COALESCE(MAX(numero), 0) + 1 FROM equipo WHERE curso_id = ?", (curso_id,)
        ).fetchone()[0]

    def crear_equipo(self, curso_id: int, numero: int, nombre: str = "", proyecto: str = "") -> None:
        self._db.execute(
            "INSERT INTO equipo (curso_id, numero, nombre, proyecto) VALUES (?, ?, ?, ?)",
            (curso_id, numero, nombre, proyecto),
        )

    def actualizar_equipo(self, curso_id: int, numero: int, nombre: str, proyecto: str) -> None:
        self._db.execute(
            "UPDATE equipo SET nombre = ?, proyecto = ? WHERE curso_id = ? AND numero = ?",
            (nombre, proyecto, curso_id, numero),
        )

    def datos_equipos(self, curso_id: int) -> dict[int, tuple[str, str]]:
        """{número: (nombre, título del proyecto)} de todos los equipos del curso."""
        filas = self._db.execute(
            "SELECT numero, nombre, proyecto FROM equipo WHERE curso_id = ?", (curso_id,)
        )
        return {f["numero"]: (f["nombre"], f["proyecto"]) for f in filas}

    def agregar_miembro_equipo(self, curso_id: int, alumno_id: int, numero: int) -> None:
        self._db.execute(
            "INSERT INTO miembro_equipo (curso_id, alumno_id, numero) VALUES (?, ?, ?)",
            (curso_id, alumno_id, numero),
        )

    def quitar_miembro_equipo(self, curso_id: int, alumno_id: int) -> None:
        self._db.execute(
            "DELETE FROM miembro_equipo WHERE curso_id = ? AND alumno_id = ?", (curso_id, alumno_id)
        )

    def equipo_de(self, curso_id: int, alumno_id: int) -> int | None:
        fila = self._db.execute(
            "SELECT numero FROM miembro_equipo WHERE curso_id = ? AND alumno_id = ?",
            (curso_id, alumno_id),
        ).fetchone()
        return fila["numero"] if fila else None

    def equipos_por_alumno(self, curso_id: int) -> dict[int, int]:
        """{alumno_id: número de equipo} de los alumnos del curso que tienen equipo."""
        filas = self._db.execute(
            "SELECT alumno_id, numero FROM miembro_equipo WHERE curso_id = ?", (curso_id,)
        )
        return {f["alumno_id"]: f["numero"] for f in filas}

    def miembros_por_equipo(self, curso_id: int) -> dict[int, list[Alumno]]:
        """{número: miembros por nombre} solo de los equipos que tienen al menos un miembro."""
        filas = self._db.execute(
            "SELECT m.numero, a.* FROM miembro_equipo m JOIN alumno a ON a.id = m.alumno_id"
            " WHERE m.curso_id = ? ORDER BY m.numero, a.nombre_norm",
            (curso_id,),
        )
        equipos: dict[int, list[Alumno]] = {}
        for f in filas:
            equipos.setdefault(f["numero"], []).append(_alumno(f))
        return equipos

    def contar_tareas_curso(self, curso_id: int) -> int:
        return self._db.execute(
            "SELECT COUNT(*) FROM calificacion_tareas WHERE curso_id = ?", (curso_id,)
        ).fetchone()[0]

