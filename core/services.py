"""Reglas de negocio. La interfaz (de escritorio o web) solo llama a esta clase."""

from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter
from collections.abc import Iterable
from datetime import date

from .calificacion_final import POR_OMISION, DesgloseFinal, Ponderaciones, calificacion_final, desglose_final
from .errores import ErrorDominio
from .models import (
    Alumno,
    ArchivoCalificaciones,
    Calificacion,
    CalificacionProyecto,
    CalificacionTareas,
    CoincidenciaOyente,
    Curso,
    Equipo,
    EstadoEquipo,
    EstadoLinea,
    EstadoRegistro,
    Examen,
    LineaExamen,
    LineaHistorial,
    LineaImportacion,
    ListaInscripcion,
    Participacion,
    ResultadoCalificacion,
    ResultadoEquipo,
    ResultadoImportacion,
    ResultadoImportacionTareas,
    ResultadoProyecto,
    ResultadoRegistro,
    ResultadoTareas,
    ResumenAlumno,
    TipoInscripcion,
    VistaPreviaImportacion,
    VistaPreviaTareas,
)
from .normalizacion import es_numero_de_cuenta, limpiar_nombre, normalizar
from .promedio import promedio_examenes
from .puntaje import acumulados
from .repository import Repositorio


class ServicioParticipaciones:
    def __init__(self, repo: Repositorio) -> None:
        self._repo = repo

    # ================= cursos =================
    def listar_cursos(self, incluir_archivados: bool = False) -> list[Curso]:
        return self._repo.listar_cursos(incluir_archivados)

    def crear_curso(self, ciclo: str, materia: str, grupo: str, carrera: str = "") -> Curso:
        curso = self._curso_validado(None, ciclo, materia, grupo, carrera)
        with self._repo.transaccion():
            return self._repo.insertar_curso(curso)

    def editar_curso(
        self, curso_id: int, ciclo: str, materia: str, grupo: str, carrera: str = ""
    ) -> Curso:
        actual = self._curso_o_error(curso_id)
        curso = self._curso_validado(curso_id, ciclo, materia, grupo, carrera)
        curso.archivado = actual.archivado
        with self._repo.transaccion():
            self._repo.actualizar_curso(curso)
        return curso

    def archivar_curso(self, curso_id: int, archivado: bool = True) -> Curso:
        curso = self._curso_o_error(curso_id)
        curso.archivado = archivado
        with self._repo.transaccion():
            self._repo.actualizar_curso(curso)
        return curso

    def resumen_eliminacion(self, curso_id: int) -> tuple[int, int]:
        """(alumnos inscritos, participaciones) que se perderían al eliminar."""
        self._curso_o_error(curso_id)
        return (
            self._repo.contar_alumnos_curso(curso_id),
            self._repo.contar_participaciones_curso(curso_id),
        )

    def resumen_eliminacion_examenes(self, curso_id: int) -> tuple[int, int]:
        """(exámenes, calificaciones) que se perderían al eliminar el curso."""
        self._curso_o_error(curso_id)
        return (
            self._repo.contar_examenes_curso(curso_id),
            self._repo.contar_calificaciones_curso(curso_id),
        )

    def resumen_eliminacion_tareas(self, curso_id: int) -> int:
        """Cuántas calificaciones de tareas se perderían al eliminar el curso."""
        self._curso_o_error(curso_id)
        return self._repo.contar_tareas_curso(curso_id)

    def resumen_eliminacion_proyecto(self, curso_id: int) -> int:
        """Cuántas calificaciones de proyecto se perderían al eliminar el curso."""
        self._curso_o_error(curso_id)
        return self._repo.contar_proyecto_curso(curso_id)

    def eliminar_curso(self, curso_id: int) -> None:
        """Eliminación definitiva. La confirmación es responsabilidad de la UI.

        Borra inscripciones, participaciones, exámenes y calificaciones del curso. Los alumnos
        se conservan.
        """
        self._curso_o_error(curso_id)
        with self._repo.transaccion():
            self._repo.eliminar_curso(curso_id)

    def contar_alumnos(self, curso_id: int) -> int:
        return self._repo.contar_alumnos_curso(curso_id)

    def _curso_validado(
        self, curso_id: int | None, ciclo: str, materia: str, grupo: str, carrera: str
    ) -> Curso:
        ciclo, materia, grupo = limpiar_nombre(ciclo), limpiar_nombre(materia), limpiar_nombre(grupo)
        if not (ciclo and materia and grupo):
            raise ErrorDominio("Ciclo, materia y grupo son obligatorios.")
        existente = self._repo.buscar_curso_por_clave(ciclo, materia, grupo)
        if existente and existente.id != curso_id:
            raise ErrorDominio(f"Ya existe el curso {existente.titulo}.")
        return Curso(curso_id, ciclo, limpiar_nombre(carrera), materia, grupo)

    def _curso_o_error(self, curso_id: int) -> Curso:
        curso = self._repo.obtener_curso(curso_id)
        if curso is None:
            raise ErrorDominio("El curso no existe.")
        return curso

    # ================= alumnos =================
    def resumen_curso(self, curso_id: int) -> list[ResumenAlumno]:
        self._curso_o_error(curso_id)
        filas = self._repo.resumen_curso(curso_id)
        pesos = self.ponderaciones_de(curso_id)
        for f in filas:  # la final nunca se guarda: se calcula con lo que hay y las ponderaciones del curso
            f.final = calificacion_final(f.total, f.prom_examenes, f.tareas, f.proyecto, pesos)
        return filas

    # ================= calificación final =================
    def ponderaciones_de(self, curso_id: int) -> Ponderaciones:
        """Las ponderaciones del curso; sin ninguna guardada, las de omisión (10 / 0 / 20 / 40)."""
        return self._repo.obtener_ponderaciones(curso_id) or POR_OMISION

    def establecer_ponderaciones(
        self, curso_id: int, participaciones: float, examenes: float, tareas: float, proyecto: float
    ) -> Ponderaciones:
        """Guarda las ponderaciones del curso: cada una de 0 a 100 %; la suma puede pasar de 100."""
        self._curso_o_error(curso_id)
        pesos = Ponderaciones(
            self._porcentaje_validado(participaciones, "participaciones"),
            self._porcentaje_validado(examenes, "exámenes"),
            self._porcentaje_validado(tareas, "tareas"),
            self._porcentaje_validado(proyecto, "proyecto"),
        )
        with self._repo.transaccion():
            self._repo.guardar_ponderaciones(curso_id, pesos)
        return pesos

    @staticmethod
    def _porcentaje_validado(valor: float, nombre: str) -> float:
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            raise ErrorDominio(f"La ponderación de {nombre} debe ser un número entre 0 y 100.") from None
        if not math.isfinite(numero) or not 0 <= numero <= 100:
            raise ErrorDominio(f"La ponderación de {nombre} debe ser un número entre 0 y 100.")
        return numero

    def ponderacion_examenes_pendiente(self, curso_id: int) -> bool:
        """¿El curso ya tiene exámenes y nunca se asignó su ponderación? (hay que recordarlo)."""
        self._curso_o_error(curso_id)
        return self._repo.contar_examenes_curso(curso_id) > 0 and self._repo.obtener_ponderaciones(curso_id) is None

    def desglose_final(self, curso_id: int, alumno_id: int) -> DesgloseFinal:
        """Los cuatro componentes de la calificación final de un alumno, con su aporte."""
        fila = next((f for f in self.resumen_curso(curso_id) if f.alumno.id == alumno_id), None)
        if fila is None:
            raise ErrorDominio("El alumno no está inscrito en este curso.")
        return desglose_final(
            fila.total, fila.prom_examenes, fila.tareas, fila.proyecto, self.ponderaciones_de(curso_id)
        )

    def buscar_alumnos_en_curso(self, curso_id: int, consulta: str) -> list[Alumno]:
        """Para el autocompletado del registro rápido."""
        consulta = consulta.strip()
        if not consulta:
            return []
        if es_numero_de_cuenta(consulta):
            return [
                a for a in self._repo.buscar_alumnos([], curso_id)
                if a.num_cuenta and a.num_cuenta.startswith(consulta)
            ]
        return self._repo.buscar_alumnos(normalizar(consulta).split(), curso_id)

    def editar_alumno(
        self, alumno_id: int, nombre_completo: str, num_cuenta: str | None
    ) -> Alumno:
        alumno = self._alumno_o_error(alumno_id)
        nombre = limpiar_nombre(nombre_completo)
        if not nombre:
            raise ErrorDominio("El nombre es obligatorio.")
        cuenta = self._cuenta_validada(num_cuenta)
        if cuenta:
            otro = self._repo.buscar_alumno_por_cuenta(cuenta)
            if otro and otro.id != alumno_id:
                raise ErrorDominio(f"El número de cuenta {cuenta} ya pertenece a {otro.nombre_completo}.")
        alumno.nombre_completo, alumno.num_cuenta = nombre, cuenta
        with self._repo.transaccion():
            self._repo.actualizar_alumno(alumno)
        return alumno

    def crear_alumno_en_curso(
        self,
        curso_id: int,
        nombre_completo: str,
        tipo: TipoInscripcion = TipoInscripcion.OYENTE,
        num_cuenta: str | None = None,
    ) -> Alumno:
        """Da de alta un alumno (p. ej. oyente) e inscribe en el curso.

        Si el número de cuenta ya existe en el sistema se reutiliza ese alumno.
        """
        self._curso_o_error(curso_id)
        nombre = limpiar_nombre(nombre_completo)
        cuenta = self._cuenta_validada(num_cuenta)
        with self._repo.transaccion():
            alumno = self._repo.buscar_alumno_por_cuenta(cuenta) if cuenta else None
            if alumno is None:
                if not nombre:
                    raise ErrorDominio("El nombre es obligatorio.")
                alumno = self._repo.insertar_alumno(Alumno(None, nombre, cuenta))
            if self._repo.obtener_tipo_inscripcion(curso_id, alumno.id) is not None:
                raise ErrorDominio(f"{alumno.nombre_completo} ya está en este curso.")
            self._repo.guardar_inscripcion(curso_id, alumno.id, tipo)
        return alumno

    def inscribir_alumno_existente(
        self, curso_id: int, alumno_id: int, tipo: TipoInscripcion = TipoInscripcion.REGULAR
    ) -> None:
        self._curso_o_error(curso_id)
        self._alumno_o_error(alumno_id)
        with self._repo.transaccion():
            if self._repo.obtener_tipo_inscripcion(curso_id, alumno_id) is not None:
                raise ErrorDominio("El alumno ya está inscrito en este curso.")
            self._repo.guardar_inscripcion(curso_id, alumno_id, tipo)

    def cambiar_tipo(self, curso_id: int, alumno_id: int, tipo: TipoInscripcion) -> None:
        if self._repo.obtener_tipo_inscripcion(curso_id, alumno_id) is None:
            raise ErrorDominio("El alumno no está inscrito en este curso.")
        with self._repo.transaccion():
            self._repo.guardar_inscripcion(curso_id, alumno_id, tipo)

    def cursos_de_alumno(self, alumno_id: int) -> list[Curso]:
        return self._repo.cursos_de_alumno(alumno_id)

    def tipo_inscripcion(self, curso_id: int, alumno_id: int) -> TipoInscripcion:
        tipo = self._repo.obtener_tipo_inscripcion(curso_id, alumno_id)
        if tipo is None:
            raise ErrorDominio("El alumno no está inscrito en este curso.")
        return tipo

    def obtener_alumno(self, alumno_id: int) -> Alumno:
        return self._alumno_o_error(alumno_id)

    def _alumno_o_error(self, alumno_id: int) -> Alumno:
        alumno = self._repo.obtener_alumno(alumno_id)
        if alumno is None:
            raise ErrorDominio("El alumno no existe.")
        return alumno

    @staticmethod
    def _cuenta_validada(num_cuenta: str | None) -> str | None:
        if num_cuenta is None or not num_cuenta.strip():
            return None
        cuenta = num_cuenta.strip()
        if not cuenta.isdigit():
            raise ErrorDominio("El número de cuenta solo puede contener dígitos.")
        return cuenta

    # ================= participaciones =================
    def registrar(
        self,
        curso_id: int,
        consulta: str,
        decimas: float,
        fecha: date | None = None,
        nota: str = "",
    ) -> ResultadoRegistro:
        """Registro rápido: identifica al alumno por cuenta o nombre y suma décimas."""
        self._curso_o_error(curso_id)
        decimas = self._decimas_validadas(decimas)
        alumno, estado, candidatos = self._identificar(curso_id, consulta)
        if alumno:
            return self.registrar_para_alumno(curso_id, alumno.id, decimas, fecha, nota)
        return ResultadoRegistro(estado, decimas, candidatos=candidatos)

    def _identificar(
        self, curso_id: int, consulta: str
    ) -> tuple[Alumno | None, EstadoRegistro, list[Alumno]]:
        """Identifica al alumno del registro rápido por cuenta o nombre (también parcial).

        Devuelve (alumno, ...) si hay una única coincidencia; si no, (None, AMBIGUO o
        NO_EXISTE, candidatos). Nunca adivina entre varias coincidencias.
        """
        consulta = consulta.strip()
        if not consulta:
            raise ErrorDominio("Escribe un número de cuenta o un nombre.")

        if es_numero_de_cuenta(consulta):
            alumno = self._repo.buscar_alumno_en_curso_por_cuenta(curso_id, consulta)
            if alumno:
                return alumno, EstadoRegistro.GUARDADO, []
            global_ = self._repo.buscar_alumno_por_cuenta(consulta)
            return None, EstadoRegistro.NO_EXISTE, [global_] if global_ else []

        tokens = normalizar(consulta).split()
        en_curso = self._repo.buscar_alumnos(tokens, curso_id)
        if len(en_curso) == 1:
            return en_curso[0], EstadoRegistro.GUARDADO, []
        if len(en_curso) > 1:
            exactos = [a for a in en_curso if normalizar(a.nombre_completo) == normalizar(consulta)]
            if len(exactos) == 1:
                return exactos[0], EstadoRegistro.GUARDADO, []
            return None, EstadoRegistro.AMBIGUO, en_curso

        ids_curso = {a.id for a in en_curso}
        otros = [a for a in self._repo.buscar_alumnos(tokens) if a.id not in ids_curso]
        return None, EstadoRegistro.NO_EXISTE, otros

    def registrar_para_alumno(
        self,
        curso_id: int,
        alumno_id: int,
        decimas: float,
        fecha: date | None = None,
        nota: str = "",
    ) -> ResultadoRegistro:
        """Suma décimas a un alumno ya identificado (inscrito en el curso)."""
        decimas = self._decimas_validadas(decimas)
        alumno = self._alumno_o_error(alumno_id)
        if self._repo.obtener_tipo_inscripcion(curso_id, alumno_id) is None:
            raise ErrorDominio(f"{alumno.nombre_completo} no está inscrito en este curso.")
        with self._repo.transaccion():
            antes = self._repo.total_alumno(curso_id, alumno_id)
            participacion = self._repo.insertar_participacion(
                Participacion(None, curso_id, alumno_id, decimas, fecha or date.today(), nota.strip())
            )
            total = self._repo.total_alumno(curso_id, alumno_id)
        return ResultadoRegistro(
            EstadoRegistro.GUARDADO, decimas, alumno, participacion, total,
            decimas_aplicadas=round(total - antes, 4),
        )

    def deshacer(self, participacion_id: int) -> Participacion:
        """Elimina una participación (p. ej. el último registro rápido)."""
        participacion = self._repo.obtener_participacion(participacion_id)
        if participacion is None:
            raise ErrorDominio("La participación ya no existe.")
        with self._repo.transaccion():
            self._repo.eliminar_participacion(participacion_id)
        return participacion

    def historial(self, curso_id: int, alumno_id: int) -> list[Participacion]:
        return self._repo.listar_participaciones(curso_id, alumno_id)

    def historial_detallado(self, curso_id: int, alumno_id: int) -> list[LineaHistorial]:
        """Participaciones (más reciente primero) con efecto real y total acumulado."""
        cronologicas = list(reversed(self._repo.listar_participaciones(curso_id, alumno_id)))
        totales = acumulados(p.decimas for p in cronologicas)
        lineas, anterior = [], 0.0
        for participacion, total in zip(cronologicas, totales):
            lineas.append(LineaHistorial(participacion, round(total - anterior, 4), total))
            anterior = total
        lineas.reverse()
        return lineas

    def total_alumno(self, curso_id: int, alumno_id: int) -> float:
        return self._repo.total_alumno(curso_id, alumno_id)

    def agregar_participacion(
        self, curso_id: int, alumno_id: int, decimas: float, fecha: date, nota: str = ""
    ) -> Participacion:
        """Alta manual desde el historial (permite fechas anteriores)."""
        return self.registrar_para_alumno(curso_id, alumno_id, decimas, fecha, nota).participacion

    def editar_participacion(
        self, participacion_id: int, decimas: float, fecha: date, nota: str = ""
    ) -> Participacion:
        participacion = self._repo.obtener_participacion(participacion_id)
        if participacion is None:
            raise ErrorDominio("La participación ya no existe.")
        participacion.decimas = self._decimas_validadas(decimas)
        participacion.fecha, participacion.nota = fecha, nota.strip()
        with self._repo.transaccion():
            self._repo.actualizar_participacion(participacion)
        return participacion

    @staticmethod
    def _decimas_validadas(decimas: float) -> float:
        try:
            valor = float(decimas)
        except (TypeError, ValueError):
            raise ErrorDominio("Las décimas deben ser un número.") from None
        if not math.isfinite(valor) or valor == 0:
            raise ErrorDominio("Las décimas deben ser un número distinto de cero.")
        return valor

    # ================= exámenes =================
    def listar_examenes(self, curso_id: int) -> list[Examen]:
        self._curso_o_error(curso_id)
        return self._repo.listar_examenes(curso_id)

    def crear_examen(self, curso_id: int, nombre: str) -> Examen:
        self._curso_o_error(curso_id)
        nombre = self._nombre_examen_validado(curso_id, None, nombre)
        with self._repo.transaccion():
            return self._repo.insertar_examen(Examen(None, curso_id, nombre))

    def renombrar_examen(self, examen_id: int, nombre: str) -> Examen:
        examen = self._examen_o_error(examen_id)
        examen.nombre = self._nombre_examen_validado(examen.curso_id, examen_id, nombre)
        with self._repo.transaccion():
            self._repo.actualizar_examen(examen)
        return examen

    def resumen_eliminacion_examen(self, examen_id: int) -> int:
        """Cuántas calificaciones se perderían al eliminar el examen."""
        self._examen_o_error(examen_id)
        return self._repo.contar_calificaciones_examen(examen_id)

    def eliminar_examen(self, examen_id: int) -> None:
        """Eliminación definitiva. La confirmación es responsabilidad de la UI."""
        self._examen_o_error(examen_id)
        with self._repo.transaccion():
            self._repo.eliminar_examen(examen_id)

    def _examen_o_error(self, examen_id: int) -> Examen:
        examen = self._repo.obtener_examen(examen_id)
        if examen is None:
            raise ErrorDominio("El examen no existe.")
        return examen

    def _nombre_examen_validado(self, curso_id: int, examen_id: int | None, nombre: str) -> str:
        nombre = " ".join(nombre.split())
        if not nombre:
            raise ErrorDominio("El examen necesita un nombre.")
        existente = self._repo.buscar_examen_por_nombre(curso_id, nombre)
        if existente and existente.id != examen_id:
            raise ErrorDominio(f"Ya existe el examen «{existente.nombre}» en este curso.")
        return nombre

    # ================= calificaciones =================
    def registrar_calificacion(
        self,
        curso_id: int,
        examen_id: int,
        consulta: str,
        puntos: float,
        fecha: date | None = None,
        reemplazar: bool = False,
    ) -> ResultadoCalificacion:
        """Registro rápido de examen: identifica al alumno igual que `registrar`."""
        self._curso_o_error(curso_id)
        examen = self._examen_del_curso(curso_id, examen_id)
        puntos = self._puntos_validados(puntos)
        alumno, estado, candidatos = self._identificar(curso_id, consulta)
        if alumno:
            return self.registrar_calificacion_para_alumno(
                curso_id, examen_id, alumno.id, puntos, fecha, reemplazar
            )
        return ResultadoCalificacion(estado, puntos, examen=examen, candidatos=candidatos)

    def registrar_calificacion_para_alumno(
        self,
        curso_id: int,
        examen_id: int,
        alumno_id: int,
        puntos: float,
        fecha: date | None = None,
        reemplazar: bool = False,
    ) -> ResultadoCalificacion:
        """Califica a un alumno ya identificado.

        Si ya tenía calificación en ese examen no la cambia hasta que se repita con
        `reemplazar=True` (la UI avisa y pide confirmar antes).
        """
        examen = self._examen_del_curso(curso_id, examen_id)
        puntos = self._puntos_validados(puntos)
        alumno = self._alumno_o_error(alumno_id)
        if self._repo.obtener_tipo_inscripcion(curso_id, alumno_id) is None:
            raise ErrorDominio(f"{alumno.nombre_completo} no está inscrito en este curso.")
        anterior = self._repo.obtener_calificacion(examen_id, alumno_id)
        if anterior and not reemplazar:
            return ResultadoCalificacion(
                EstadoRegistro.CONFIRMAR_REEMPLAZO, puntos, alumno, examen, anterior,
                self.promedio_examenes_alumno(curso_id, alumno_id),
            )
        with self._repo.transaccion():
            self._repo.guardar_calificacion(
                Calificacion(examen_id, alumno_id, puntos, fecha or date.today())
            )
        return ResultadoCalificacion(
            EstadoRegistro.GUARDADO, puntos, alumno, examen, anterior,
            self.promedio_examenes_alumno(curso_id, alumno_id),
        )

    def deshacer_calificacion(
        self, examen_id: int, alumno_id: int, anterior: Calificacion | None
    ) -> None:
        """Restaura la calificación previa, o la elimina si no había ninguna."""
        with self._repo.transaccion():
            if anterior is None:
                self._repo.eliminar_calificacion(examen_id, alumno_id)
            else:
                self._repo.guardar_calificacion(anterior)

    def calificacion_de(self, examen_id: int, alumno_id: int) -> Calificacion | None:
        return self._repo.obtener_calificacion(examen_id, alumno_id)

    def historial_examenes(self, curso_id: int, alumno_id: int) -> list[LineaExamen]:
        """Todos los exámenes del curso, en orden de creación, con la calificación del alumno."""
        self._curso_o_error(curso_id)
        return [
            LineaExamen(e, self._repo.obtener_calificacion(e.id, alumno_id))
            for e in self._repo.listar_examenes(curso_id)
        ]

    def establecer_calificacion(
        self, curso_id: int, examen_id: int, alumno_id: int, puntos: float, fecha: date
    ) -> Calificacion:
        """Alta o corrección desde el historial (el profesor ya eligió el examen y confirmó)."""
        self.registrar_calificacion_para_alumno(
            curso_id, examen_id, alumno_id, puntos, fecha, reemplazar=True
        )
        return self._repo.obtener_calificacion(examen_id, alumno_id)

    def eliminar_calificacion(self, examen_id: int, alumno_id: int) -> None:
        """Quita la calificación: el examen vuelve a valer 0. La confirmación es de la UI."""
        if self._repo.obtener_calificacion(examen_id, alumno_id) is None:
            raise ErrorDominio("Ese examen no tiene calificación.")
        with self._repo.transaccion():
            self._repo.eliminar_calificacion(examen_id, alumno_id)

    def promedio_examenes_alumno(self, curso_id: int, alumno_id: int) -> float | None:
        examenes = self._repo.listar_examenes(curso_id)
        puntos = self._repo.puntos_por_alumno(curso_id).get(alumno_id, {})
        return promedio_examenes([puntos.get(e.id, 0.0) for e in examenes])

    def _examen_del_curso(self, curso_id: int, examen_id: int) -> Examen:
        examen = self._examen_o_error(examen_id)
        if examen.curso_id != curso_id:
            raise ErrorDominio("El examen no pertenece a este curso.")
        return examen

    @staticmethod
    def _puntos_validados(puntos: float) -> float:
        try:
            valor = float(puntos)
        except (TypeError, ValueError):
            raise ErrorDominio("La calificación debe ser un número.") from None
        if not math.isfinite(valor) or valor < 0:
            raise ErrorDominio("La calificación debe ser un número mayor o igual a 0.")
        return valor

    # ================= calificación de tareas =================
    def registrar_tareas(
        self,
        curso_id: int,
        consulta: str,
        puntos: float,
        fecha: date | None = None,
        reemplazar: bool = False,
    ) -> ResultadoTareas:
        """Registro rápido de tareas: identifica al alumno igual que `registrar`."""
        self._curso_o_error(curso_id)
        puntos = self._puntos_validados(puntos)
        alumno, estado, candidatos = self._identificar(curso_id, consulta)
        if alumno:
            return self.registrar_tareas_para_alumno(curso_id, alumno.id, puntos, fecha, reemplazar)
        return ResultadoTareas(estado, puntos, candidatos=candidatos)

    def registrar_tareas_para_alumno(
        self,
        curso_id: int,
        alumno_id: int,
        puntos: float,
        fecha: date | None = None,
        reemplazar: bool = False,
    ) -> ResultadoTareas:
        """Califica las tareas de un alumno ya identificado.

        Si ya tenía calificación no la cambia hasta que se repita con `reemplazar=True`
        (la UI avisa y pide confirmar antes).
        """
        self._curso_o_error(curso_id)
        puntos = self._puntos_validados(puntos)
        alumno = self._alumno_o_error(alumno_id)
        if self._repo.obtener_tipo_inscripcion(curso_id, alumno_id) is None:
            raise ErrorDominio(f"{alumno.nombre_completo} no está inscrito en este curso.")
        anterior = self._repo.obtener_tareas(curso_id, alumno_id)
        if anterior and not reemplazar:
            return ResultadoTareas(EstadoRegistro.CONFIRMAR_REEMPLAZO, puntos, alumno, anterior)
        with self._repo.transaccion():
            self._repo.guardar_tareas(
                CalificacionTareas(curso_id, alumno_id, puntos, fecha or date.today())
            )
        return ResultadoTareas(EstadoRegistro.GUARDADO, puntos, alumno, anterior)

    def deshacer_tareas(
        self, curso_id: int, alumno_id: int, anterior: CalificacionTareas | None
    ) -> None:
        """Restaura la calificación previa, o la elimina si no había ninguna."""
        with self._repo.transaccion():
            if anterior is None:
                self._repo.eliminar_tareas(curso_id, alumno_id)
            else:
                self._repo.guardar_tareas(anterior)

    def tareas_de(self, curso_id: int, alumno_id: int) -> CalificacionTareas | None:
        return self._repo.obtener_tareas(curso_id, alumno_id)

    def establecer_tareas(
        self, curso_id: int, alumno_id: int, puntos: float, fecha: date
    ) -> CalificacionTareas:
        """Alta o corrección desde el historial (el profesor ya eligió y confirmó)."""
        self.registrar_tareas_para_alumno(curso_id, alumno_id, puntos, fecha, reemplazar=True)
        return self._repo.obtener_tareas(curso_id, alumno_id)

    def eliminar_tareas(self, curso_id: int, alumno_id: int) -> None:
        """Quita la calificación: las tareas vuelven a valer 0. La confirmación es de la UI."""
        if self._repo.obtener_tareas(curso_id, alumno_id) is None:
            raise ErrorDominio("Este alumno no tiene calificación de tareas.")
        with self._repo.transaccion():
            self._repo.eliminar_tareas(curso_id, alumno_id)

    # ================= importación =================
    def previsualizar_importacion(self, lista: ListaInscripcion) -> VistaPreviaImportacion:
        """Analiza sin escribir: qué se creará y qué coincide con oyentes sin cuenta."""
        curso = self._repo.buscar_curso_por_clave(
            limpiar_nombre(lista.ciclo), limpiar_nombre(lista.materia), limpiar_nombre(lista.grupo)
        )
        nuevos = existentes = 0
        coincidencias: list[CoincidenciaOyente] = []
        for fila in lista.alumnos:
            if self._repo.buscar_alumno_por_cuenta(fila.num_cuenta):
                existentes += 1
                continue
            nuevos += 1
            for oyente in self._repo.buscar_alumnos_sin_cuenta_por_nombre(fila.nombre_completo):
                coincidencias.append(CoincidenciaOyente(fila, oyente))
        return VistaPreviaImportacion(curso, nuevos, existentes, coincidencias)

    def importar_lista(
        self, lista: ListaInscripcion, vinculos: dict[str, int] | None = None
    ) -> ResultadoImportacion:
        """Crea/actualiza el curso, los alumnos y sus inscripciones (regulares).

        `vinculos` asigna número de cuenta -> id de un oyente sin cuenta que el
        profesor confirmó que es la misma persona. Sin confirmación no se fusiona.
        Reimportar no duplica alumnos ni borra participaciones.
        """
        vinculos = vinculos or {}
        ciclo, materia, grupo = (
            limpiar_nombre(lista.ciclo), limpiar_nombre(lista.materia), limpiar_nombre(lista.grupo),
        )
        if not (ciclo and materia and grupo):
            raise ErrorDominio("La lista no trae ciclo, materia y grupo.")

        creados = nuevas = vinculados = 0
        try:
            with self._repo.transaccion():
                curso = self._repo.buscar_curso_por_clave(ciclo, materia, grupo)
                curso_creado = curso is None
                if curso is None:
                    curso = self._repo.insertar_curso(
                        Curso(None, ciclo, limpiar_nombre(lista.carrera), materia, grupo)
                    )
                for fila in lista.alumnos:
                    alumno = self._repo.buscar_alumno_por_cuenta(fila.num_cuenta)
                    if alumno is None and fila.num_cuenta in vinculos:
                        alumno = self._vincular_oyente(vinculos[fila.num_cuenta], fila.num_cuenta)
                        vinculados += 1
                    elif alumno is None:
                        alumno = self._repo.insertar_alumno(
                            Alumno(None, fila.nombre_completo, fila.num_cuenta)
                        )
                        creados += 1
                    if self._repo.obtener_tipo_inscripcion(curso.id, alumno.id) is None:
                        nuevas += 1
                    self._repo.guardar_inscripcion(curso.id, alumno.id, TipoInscripcion.REGULAR)
        except sqlite3.IntegrityError as error:
            raise ErrorDominio(f"No se pudo importar la lista: {error}") from error
        return ResultadoImportacion(curso, curso_creado, creados, nuevas, vinculados)

    def _vincular_oyente(self, alumno_id: int, num_cuenta: str) -> Alumno:
        oyente = self._repo.obtener_alumno(alumno_id)
        if oyente is None or oyente.num_cuenta is not None:
            raise ErrorDominio("El oyente a vincular no existe o ya tiene número de cuenta.")
        oyente.num_cuenta = num_cuenta
        self._repo.actualizar_alumno(oyente)
        return oyente

    # ================= calificación del proyecto final =================
    _EQUIPO_EN_CONSULTA = re.compile(r"\s*(?:equipo|e)\s*(\d+)\s*", re.IGNORECASE)

    @classmethod
    def _equipo_en_consulta(cls, consulta: str) -> int | None:
        """«equipo 3», «Equipo 3» o «e 3» → 3. Un número solo es un número de cuenta, no un equipo."""
        coincidencia = cls._EQUIPO_EN_CONSULTA.fullmatch(consulta)
        return int(coincidencia.group(1)) if coincidencia else None

    def registrar_proyecto(
        self,
        curso_id: int,
        consulta: str,
        puntos: float,
        fecha: date | None = None,
        reemplazar: bool = False,
    ) -> ResultadoProyecto:
        """Registro rápido del proyecto: «equipo N» califica a todo el equipo; si no, identifica
        al alumno igual que `registrar` y califica solo a ese alumno."""
        self._curso_o_error(curso_id)
        puntos = self._puntos_validados(puntos)
        numero = self._equipo_en_consulta(consulta)
        if numero is not None:
            return self.registrar_proyecto_equipo(curso_id, numero, puntos, fecha, reemplazar)
        alumno, estado, candidatos = self._identificar(curso_id, consulta)
        if alumno:
            return self.registrar_proyecto_para_alumno(curso_id, alumno.id, puntos, fecha, reemplazar)
        return ResultadoProyecto(estado, puntos, candidatos=candidatos)

    def registrar_proyecto_para_alumno(
        self,
        curso_id: int,
        alumno_id: int,
        puntos: float,
        fecha: date | None = None,
        reemplazar: bool = False,
    ) -> ResultadoProyecto:
        """Califica el proyecto de un alumno ya identificado (inscrito en el curso)."""
        self._curso_o_error(curso_id)
        puntos = self._puntos_validados(puntos)
        alumno = self._alumno_o_error(alumno_id)
        if self._repo.obtener_tipo_inscripcion(curso_id, alumno_id) is None:
            raise ErrorDominio(f"{alumno.nombre_completo} no está inscrito en este curso.")
        return self._aplicar_proyecto(curso_id, [alumno], puntos, fecha, reemplazar, equipo=None)

    def registrar_proyecto_equipo(
        self,
        curso_id: int,
        numero: int,
        puntos: float,
        fecha: date | None = None,
        reemplazar: bool = False,
    ) -> ResultadoProyecto:
        """Copia la misma calificación a todos los miembros del equipo (no queda vínculo: lo que
        pase después con el equipo no cambia las notas)."""
        self._curso_o_error(curso_id)
        puntos = self._puntos_validados(puntos)
        miembros = self._repo.miembros_por_equipo(curso_id).get(numero)
        if not miembros:
            raise ErrorDominio(f"El equipo {numero} no existe o no tiene miembros.")
        return self._aplicar_proyecto(curso_id, miembros, puntos, fecha, reemplazar, equipo=numero)

    def _aplicar_proyecto(
        self,
        curso_id: int,
        alumnos: list[Alumno],
        puntos: float,
        fecha: date | None,
        reemplazar: bool,
        equipo: int | None,
    ) -> ResultadoProyecto:
        """Un solo camino para un alumno o un equipo. Si alguno ya tiene una nota distinta de la
        nueva no guarda nada hasta repetir con `reemplazar=True` (las iguales no cuentan)."""
        anteriores = {a.id: self._repo.obtener_proyecto(curso_id, a.id) for a in alumnos}
        con_otra = sum(1 for a in anteriores.values() if a is not None and a.puntos != puntos)
        if con_otra and not reemplazar:
            return ResultadoProyecto(
                EstadoRegistro.CONFIRMAR_REEMPLAZO, puntos, alumnos, equipo, con_otra, anteriores
            )
        fecha = fecha or date.today()
        with self._repo.transaccion():
            for alumno in alumnos:
                self._repo.guardar_proyecto(CalificacionProyecto(curso_id, alumno.id, puntos, fecha))
        return ResultadoProyecto(EstadoRegistro.GUARDADO, puntos, alumnos, equipo, 0, anteriores)

    def deshacer_proyecto(
        self, curso_id: int, anteriores: dict[int, CalificacionProyecto | None]
    ) -> None:
        """Deja a cada alumno con la calificación que tenía (o sin ella si no tenía)."""
        with self._repo.transaccion():
            for alumno_id, anterior in anteriores.items():
                if anterior is None:
                    self._repo.eliminar_proyecto(curso_id, alumno_id)
                else:
                    self._repo.guardar_proyecto(anterior)

    def proyecto_de(self, curso_id: int, alumno_id: int) -> CalificacionProyecto | None:
        return self._repo.obtener_proyecto(curso_id, alumno_id)

    def establecer_proyecto(
        self, curso_id: int, alumno_id: int, puntos: float, fecha: date
    ) -> CalificacionProyecto:
        """Alta o corrección desde el historial (la persona ya eligió y confirmó)."""
        self.registrar_proyecto_para_alumno(curso_id, alumno_id, puntos, fecha, reemplazar=True)
        return self._repo.obtener_proyecto(curso_id, alumno_id)

    def eliminar_proyecto(self, curso_id: int, alumno_id: int) -> None:
        """Quita la calificación: el proyecto vuelve a valer 0. La confirmación es de la UI."""
        if self._repo.obtener_proyecto(curso_id, alumno_id) is None:
            raise ErrorDominio("Este alumno no tiene calificación de proyecto.")
        with self._repo.transaccion():
            self._repo.eliminar_proyecto(curso_id, alumno_id)

    # ================= equipos de proyecto =================
    MAX_NOMBRE_EQUIPO = 60
    MAX_PROYECTO_EQUIPO = 120

    @classmethod
    def _datos_equipo(cls, nombre: str, proyecto: str) -> tuple[str, str]:
        """Limpia espacios y valida el largo del nombre del equipo y del título del proyecto."""
        nombre = " ".join(nombre.split())
        proyecto = " ".join(proyecto.split())
        if len(nombre) > cls.MAX_NOMBRE_EQUIPO:
            raise ErrorDominio(f"El nombre del equipo no puede pasar de {cls.MAX_NOMBRE_EQUIPO} caracteres.")
        if len(proyecto) > cls.MAX_PROYECTO_EQUIPO:
            raise ErrorDominio(f"El título del proyecto no puede pasar de {cls.MAX_PROYECTO_EQUIPO} caracteres.")
        return nombre, proyecto

    def formar_equipo(
        self, curso_id: int, alumno_ids: list[int], nombre: str = "", proyecto: str = ""
    ) -> ResultadoEquipo:
        """Forma un equipo nuevo (desde 1 alumno) con el siguiente número del curso, con su nombre y
        el título de su proyecto si se dan (opcionales).

        Si alguno ya tiene equipo no crea nada ni mueve a nadie: informa quién y en cuál.
        """
        self._curso_o_error(curso_id)
        nombre, proyecto = self._datos_equipo(nombre, proyecto)
        alumnos, con_equipo = self._alumnos_para_equipo(
            curso_id, alumno_ids, "Elige al menos un alumno para formar el equipo."
        )
        if con_equipo:
            return ResultadoEquipo(EstadoEquipo.YA_TIENEN_EQUIPO, con_equipo=con_equipo)
        with self._repo.transaccion():
            numero = self._repo.siguiente_numero_equipo(curso_id)
            self._repo.crear_equipo(curso_id, numero, nombre, proyecto)
            for alumno in alumnos:
                self._repo.agregar_miembro_equipo(curso_id, alumno.id, numero)
        return ResultadoEquipo(EstadoEquipo.FORMADO, numero, alumnos)

    def agregar_a_equipo(self, curso_id: int, numero: int, alumno_ids: list[int]) -> ResultadoEquipo:
        """Suma alumnos a un equipo que ya tiene miembros. Igual que al formar, si alguno ya tiene
        equipo no cambia nada (hay que separarlo antes) y se informa quién y en cuál."""
        self._curso_o_error(curso_id)
        if numero not in self._repo.miembros_por_equipo(curso_id):
            raise ErrorDominio(f"El equipo {numero} no existe o ya no tiene miembros.")
        alumnos, con_equipo = self._alumnos_para_equipo(
            curso_id, alumno_ids, "Elige al menos un alumno para agregar al equipo."
        )
        if con_equipo:
            return ResultadoEquipo(EstadoEquipo.YA_TIENEN_EQUIPO, con_equipo=con_equipo)
        with self._repo.transaccion():
            for alumno in alumnos:
                self._repo.agregar_miembro_equipo(curso_id, alumno.id, numero)
        return ResultadoEquipo(EstadoEquipo.AGREGADO, numero, alumnos)

    def _alumnos_para_equipo(
        self, curso_id: int, alumno_ids: list[int], mensaje_vacio: str
    ) -> tuple[list[Alumno], list[tuple[Alumno, int]]]:
        """Valida a los alumnos (sin repetir, inscritos) y separa a los que ya tienen equipo."""
        ids = list(dict.fromkeys(alumno_ids))
        if not ids:
            raise ErrorDominio(mensaje_vacio)
        alumnos = []
        for alumno_id in ids:
            alumno = self._alumno_o_error(alumno_id)
            if self._repo.obtener_tipo_inscripcion(curso_id, alumno_id) is None:
                raise ErrorDominio(f"{alumno.nombre_completo} no está inscrito en este curso.")
            alumnos.append(alumno)
        con_equipo = [
            (a, numero) for a in alumnos if (numero := self._repo.equipo_de(curso_id, a.id)) is not None
        ]
        return alumnos, con_equipo

    def separar_de_equipo(self, curso_id: int, alumno_ids: list[int]) -> dict[int, int]:
        """Saca a los alumnos de su equipo. Devuelve {alumno_id: equipo que tenía} de quienes
        sí estaban en uno (lo que necesita `deshacer_separacion`); los demás se ignoran."""
        self._curso_o_error(curso_id)
        separados: dict[int, int] = {}
        with self._repo.transaccion():
            for alumno_id in dict.fromkeys(alumno_ids):
                numero = self._repo.equipo_de(curso_id, alumno_id)
                if numero is not None:
                    self._repo.quitar_miembro_equipo(curso_id, alumno_id)
                    separados[alumno_id] = numero
        return separados

    def deshacer_separacion(self, curso_id: int, separados: dict[int, int]) -> None:
        """Devuelve a cada alumno a su equipo (salvo que ya esté en otro)."""
        with self._repo.transaccion():
            for alumno_id, numero in separados.items():
                if self._repo.equipo_de(curso_id, alumno_id) is None:
                    self._repo.agregar_miembro_equipo(curso_id, alumno_id, numero)

    def deshacer_equipo(self, curso_id: int, numero: int) -> None:
        """Deshace la formación de un equipo: libera a sus miembros. El número queda usado."""
        with self._repo.transaccion():
            for alumno in self._repo.miembros_por_equipo(curso_id).get(numero, []):
                self._repo.quitar_miembro_equipo(curso_id, alumno.id)

    def equipos_del_curso(self, curso_id: int) -> list[Equipo]:
        """Los equipos con al menos un miembro, por número, con su nombre y proyecto."""
        datos = self._repo.datos_equipos(curso_id)
        return [
            Equipo(curso_id, numero, miembros, *datos.get(numero, ("", "")))
            for numero, miembros in sorted(self._repo.miembros_por_equipo(curso_id).items())
        ]

    def editar_equipo(self, curso_id: int, numero: int, nombre: str, proyecto: str) -> Equipo:
        """Cambia el nombre y el título del proyecto de un equipo que tiene miembros (vacío los quita)."""
        self._curso_o_error(curso_id)
        miembros = self._repo.miembros_por_equipo(curso_id).get(numero)
        if not miembros:
            raise ErrorDominio(f"El equipo {numero} no existe o ya no tiene miembros.")
        nombre, proyecto = self._datos_equipo(nombre, proyecto)
        with self._repo.transaccion():
            self._repo.actualizar_equipo(curso_id, numero, nombre, proyecto)
        return Equipo(curso_id, numero, miembros, nombre, proyecto)

    def equipo_de(self, curso_id: int, alumno_id: int) -> int | None:
        return self._repo.equipo_de(curso_id, alumno_id)

    # ================= importar calificaciones de tareas =================
    def previsualizar_importacion_tareas(
        self, curso_id: int, archivo: ArchivoCalificaciones, clave_columna: str | None = None
    ) -> VistaPreviaTareas:
        """Dice qué pasaría al importar la columna elegida del archivo. No guarda nada.

        Identifica a cada fila con un alumno del curso (cuenta si el archivo la trae; si no, nombre)
        y nunca crea alumnos: exacta única → se aplica; por palabras única → dudosa (solo con
        confirmación); varias o ninguna → se omite.
        """
        curso = self._curso_o_error(curso_id)
        columna = self._columna_de_archivo(archivo, clave_columna)
        inscritos = [r.alumno for r in self._repo.resumen_curso(curso_id)]
        actuales = self._repo.tareas_por_alumno(curso_id)
        repetidos = {
            nombre
            for nombre, veces in Counter(normalizar(f.nombre_completo) for f in archivo.filas).items()
            if veces > 1
        }
        lineas = [
            self._linea_importacion(curso_id, f, columna, inscritos, actuales, repetidos)
            for f in archivo.filas
        ]
        self._omitir_alumnos_repetidos(lineas)
        mencionados = {l.alumno.id for l in lineas if l.alumno}
        return VistaPreviaTareas(
            columna, lineas, [a for a in inscritos if a.id not in mencionados],
            self._advertencia_grupo(curso, archivo),
        )

    def importar_tareas(
        self,
        curso_id: int,
        archivo: ArchivoCalificaciones,
        clave_columna: str | None = None,
        confirmadas: Iterable[int] = (),
        fecha: date | None = None,
    ) -> ResultadoImportacionTareas:
        """Guarda la columna elegida: las coincidencias claras y las dudosas que la persona confirmó
        (`confirmadas`: ids de alumno). Reemplaza sin preguntar; todo o nada. Devuelve lo necesario
        para `deshacer_importacion_tareas`."""
        vista = self.previsualizar_importacion_tareas(curso_id, archivo, clave_columna)
        confirmadas = set(confirmadas)
        aplicables = vista.claras + [l for l in vista.dudosas if l.alumno.id in confirmadas]
        fecha = fecha or date.today()
        anteriores: dict[int, CalificacionTareas | None] = {}
        with self._repo.transaccion():
            for linea in aplicables:
                if not linea.cambia:
                    continue
                anteriores[linea.alumno.id] = self._repo.obtener_tareas(curso_id, linea.alumno.id)
                self._repo.guardar_tareas(
                    CalificacionTareas(curso_id, linea.alumno.id, linea.puntos, fecha)
                )
        iguales = sum(1 for l in aplicables if not l.cambia)
        return ResultadoImportacionTareas(
            len(anteriores), iguales, len(vista.lineas) - len(aplicables), anteriores
        )

    def deshacer_importacion_tareas(
        self, curso_id: int, anteriores: dict[int, CalificacionTareas | None]
    ) -> None:
        """Deja las calificaciones como estaban antes de importar (o las elimina si no existían)."""
        with self._repo.transaccion():
            for alumno_id, anterior in anteriores.items():
                if anterior is None:
                    self._repo.eliminar_tareas(curso_id, alumno_id)
                else:
                    self._repo.guardar_tareas(anterior)

    @staticmethod
    def _columna_de_archivo(archivo: ArchivoCalificaciones, clave: str | None):
        if clave is None:
            return archivo.columna_sugerida
        for columna in archivo.columnas:
            if columna.clave == clave:
                return columna
        raise ErrorDominio(f"La columna «{clave}» no existe en el archivo.")

    def _linea_importacion(
        self, curso_id, fila, columna, inscritos, actuales, repetidos
    ) -> LineaImportacion:
        if normalizar(fila.nombre_completo) in repetidos:
            return LineaImportacion(
                fila, EstadoLinea.OMITIDA, motivo="El nombre está repetido en el archivo."
            )
        alumno, dudosa, motivo = self._coincidencia_por_nombre(curso_id, fila, inscritos)
        if alumno is None:
            return LineaImportacion(fila, EstadoLinea.OMITIDA, motivo=motivo)
        anterior = actuales.get(alumno.id)
        valor = fila.valores.get(columna.clave)
        if valor is None:
            motivo = "Sin dato en la columna elegida."
        elif isinstance(valor, str):
            motivo = f"El valor «{valor}» no es un número."
        else:
            try:
                puntos = self._puntos_validados(valor)
            except ErrorDominio as error:
                motivo = str(error)
            else:
                estado = EstadoLinea.DUDOSA if dudosa else EstadoLinea.APLICAR
                return LineaImportacion(fila, estado, alumno, puntos, anterior, motivo)
        return LineaImportacion(fila, EstadoLinea.OMITIDA, alumno, None, anterior, motivo)

    def _coincidencia_por_nombre(self, curso_id, fila, inscritos):
        """(alumno | None, es_dudosa, motivo) para una fila del archivo."""
        if fila.cuenta:
            alumno = self._repo.buscar_alumno_en_curso_por_cuenta(curso_id, fila.cuenta)
            if alumno:
                return alumno, False, ""
        nombre = normalizar(fila.nombre_completo)
        exactos = [a for a in inscritos if normalizar(a.nombre_completo) == nombre]
        if len(exactos) == 1:
            return exactos[0], False, ""
        if len(exactos) > 1:
            return None, False, "Varios alumnos del curso tienen ese nombre."
        palabras = set(nombre.split())
        parecidos = []
        for a in inscritos:
            otras = set(normalizar(a.nombre_completo).split())
            if palabras and otras and (palabras <= otras or otras <= palabras):
                parecidos.append(a)
        if len(parecidos) == 1:
            return parecidos[0], True, f"Coincide por palabras con {parecidos[0].nombre_completo}."
        if parecidos:
            nombres = ", ".join(a.nombre_completo for a in parecidos)
            return None, False, f"Varios alumnos del curso podrían ser: {nombres}."
        return None, False, "No coincide con ningún alumno del curso."

    @staticmethod
    def _omitir_alumnos_repetidos(lineas: list[LineaImportacion]) -> None:
        """Si varias filas apuntan al mismo alumno solo sobrevive una coincidencia exacta única."""
        por_alumno: dict[int, list[LineaImportacion]] = {}
        for linea in lineas:
            if linea.estado != EstadoLinea.OMITIDA:
                por_alumno.setdefault(linea.alumno.id, []).append(linea)
        for grupo in por_alumno.values():
            if len(grupo) < 2:
                continue
            exactas = [l for l in grupo if l.estado == EstadoLinea.APLICAR]
            for linea in grupo:
                if len(exactas) == 1 and linea is exactas[0]:
                    continue
                linea.estado = EstadoLinea.OMITIDA
                linea.puntos = None
                linea.motivo = "Otra fila del archivo corresponde al mismo alumno."

    @staticmethod
    def _advertencia_grupo(curso: Curso, archivo: ArchivoCalificaciones) -> str:
        if not archivo.grupo:
            return ""
        distinto = normalizar(archivo.grupo) != normalizar(curso.grupo) or (
            archivo.ciclo and normalizar(archivo.ciclo) != normalizar(curso.ciclo)
        )
        if not distinto:
            return ""
        ciclo = f" ({archivo.ciclo})" if archivo.ciclo else ""
        return (
            f"El archivo es del grupo {archivo.grupo}{ciclo}, pero el curso abierto es "
            f"{curso.grupo} ({curso.ciclo})."
        )
