"""Reglas de negocio. La interfaz (de escritorio o web) solo llama a esta clase."""

from __future__ import annotations

import math
import sqlite3
from datetime import date

from .errores import ErrorDominio
from .models import (
    Alumno,
    CoincidenciaOyente,
    Curso,
    EstadoRegistro,
    LineaHistorial,
    ListaInscripcion,
    Participacion,
    ResultadoImportacion,
    ResultadoRegistro,
    ResumenAlumno,
    TipoInscripcion,
    VistaPreviaImportacion,
)
from .normalizacion import es_numero_de_cuenta, limpiar_nombre, normalizar
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

    def eliminar_curso(self, curso_id: int) -> None:
        """Eliminación definitiva. La confirmación es responsabilidad de la UI.

        Borra inscripciones y participaciones del curso. Los alumnos se conservan.
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
        consulta = consulta.strip()
        if not consulta:
            raise ErrorDominio("Escribe un número de cuenta o un nombre.")

        if es_numero_de_cuenta(consulta):
            alumno = self._repo.buscar_alumno_en_curso_por_cuenta(curso_id, consulta)
            if alumno:
                return self.registrar_para_alumno(curso_id, alumno.id, decimas, fecha, nota)
            global_ = self._repo.buscar_alumno_por_cuenta(consulta)
            return ResultadoRegistro(
                EstadoRegistro.NO_EXISTE, decimas, candidatos=[global_] if global_ else []
            )

        tokens = normalizar(consulta).split()
        en_curso = self._repo.buscar_alumnos(tokens, curso_id)
        if len(en_curso) == 1:
            return self.registrar_para_alumno(curso_id, en_curso[0].id, decimas, fecha, nota)
        if len(en_curso) > 1:
            exactos = [a for a in en_curso if normalizar(a.nombre_completo) == normalizar(consulta)]
            if len(exactos) == 1:
                return self.registrar_para_alumno(curso_id, exactos[0].id, decimas, fecha, nota)
            return ResultadoRegistro(EstadoRegistro.AMBIGUO, decimas, candidatos=en_curso)

        ids_curso = {a.id for a in en_curso}
        otros = [a for a in self._repo.buscar_alumnos(tokens) if a.id not in ids_curso]
        return ResultadoRegistro(EstadoRegistro.NO_EXISTE, decimas, candidatos=otros)

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
