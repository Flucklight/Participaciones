"""Lee el Excel de lista de inscripción (FES Aragón) y lo convierte en un modelo.

Formato esperado (hoja única):
    - Encabezado con filas "Ciclo Escolar:", "Carrera:", "Materia:" y "Grupo:"
      (la etiqueta en una celda y el valor en otra celda de la misma fila).
    - Una fila de títulos con "No. Cuenta" y "Nombre", seguida de los alumnos.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

from core.errores import ErrorImportacion
from core.models import FilaLista, ListaInscripcion
from core.normalizacion import limpiar_nombre, normalizar

_ETIQUETAS = {
    "CICLO ESCOLAR:": "ciclo",
    "CARRERA:": "carrera",
    "MATERIA:": "materia",
    "GRUPO:": "grupo",
}


def _texto(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


def leer_lista(ruta: str | Path) -> ListaInscripcion:
    try:
        libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    except Exception as error:  # archivo inexistente, corrupto o no es .xlsx
        raise ErrorImportacion(f"No se pudo abrir el archivo: {error}") from error

    try:
        filas = [[_texto(c) for c in fila] for fila in libro.worksheets[0].iter_rows(values_only=True)]
    finally:
        libro.close()

    encabezado: dict[str, str] = {}
    fila_titulos: int | None = None
    col_cuenta = col_nombre = -1

    for i, fila in enumerate(filas):
        normalizadas = [normalizar(c) for c in fila]
        if "NO. CUENTA" in normalizadas and "NOMBRE" in normalizadas:
            fila_titulos = i
            col_cuenta = normalizadas.index("NO. CUENTA")
            col_nombre = normalizadas.index("NOMBRE")
            break
        for j, celda in enumerate(normalizadas):
            campo = _ETIQUETAS.get(celda)
            if campo:
                valor = next((c for c in fila[j + 1:] if c), "")
                encabezado[campo] = valor

    faltantes = [c for c in ("ciclo", "materia", "grupo") if not encabezado.get(c)]
    if fila_titulos is None:
        raise ErrorImportacion("No se encontró la tabla de alumnos (columnas 'No. Cuenta' y 'Nombre').")
    if faltantes:
        raise ErrorImportacion(f"Falta en el encabezado: {', '.join(faltantes)}.")

    alumnos: list[FilaLista] = []
    vistas: set[str] = set()
    for fila in filas[fila_titulos + 1:]:
        cuenta = fila[col_cuenta] if col_cuenta < len(fila) else ""
        nombre = limpiar_nombre(fila[col_nombre]) if col_nombre < len(fila) else ""
        if not cuenta and not nombre:
            continue
        numero = len(alumnos) + 1
        if not cuenta.isdigit():
            raise ErrorImportacion(f"Número de cuenta inválido en el alumno {numero}: '{cuenta}'.")
        if not nombre:
            raise ErrorImportacion(f"El alumno con cuenta {cuenta} no tiene nombre.")
        if cuenta in vistas:
            raise ErrorImportacion(f"El número de cuenta {cuenta} aparece repetido en la lista.")
        vistas.add(cuenta)
        alumnos.append(FilaLista(numero, cuenta, nombre))

    if not alumnos:
        raise ErrorImportacion("La lista no contiene alumnos.")

    return ListaInscripcion(
        ciclo=encabezado["ciclo"],
        carrera=encabezado.get("carrera", ""),
        materia=encabezado["materia"],
        grupo=encabezado["grupo"],
        alumnos=alumnos,
    )
