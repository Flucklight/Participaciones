"""Reglas de negocio. La interfaz (de escritorio o web) solo llama a esta clase."""

from __future__ import annotations

import math
import sqlite3
from datetime import date

from .errores import ErrorDominio
from .models import (
    Alumno,
    Calificacion,
    CoincidenciaOyente,
    Curso,
    EstadoRegistro,
    Examen,
    LineaExamen,
    LineaHistorial,
    ListaInscripcion,
    Participacion,
    ResultadoCalificacion,
    ResultadoImportacion,
    ResultadoRegistro,
    ResumenAlumno,
    TipoInscripcion,
    VistaPreviaImportacion,
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
        return self._repo.resumen_curso(curso_id)

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
