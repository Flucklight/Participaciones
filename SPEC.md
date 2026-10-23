# Spec: Calificaciones de exámenes en la pantalla Curso

Estado: **BORRADOR para aprobación** (no hay código ni cambios a `CLAUDE.md` todavía).

## Objetivo

Hoy la app solo contabiliza participaciones (décimas acumulables). Se agrega la captura de **calificaciones de exámenes** en el mismo flujo de registro rápido de la pantalla Curso, para que el profesor lleve en un solo lugar participaciones y exámenes.

Usuario: el profesor, que captura muchas filas seguidas, con teclado.

Decisiones ya tomadas con el usuario:
- Un examen se califica como **calificación** (no son décimas): no se acumula ni tiene piso.
- Los exámenes **no tienen tope máximo** (puede haber puntos extra). Cada examen solo tiene nombre (ej. «Parcial 1», «Final»).
- Un curso puede tener **varios exámenes**, con nombre.
- Diseño: **selector segmentado** `[Participación | Examen]` en el registro rápido. En modo Examen aparece la lista de exámenes del curso con «+ Nuevo examen», y el campo de décimas pasa a «Calificación».
- La exportación incluye una columna por examen y el **promedio solo de los exámenes**.

## Supuestos (corrígeme ahora o procedo con ellos)

1. Una calificación por alumno y examen. Capturar otra vez **reemplaza** la anterior, pero **antes de confirmar** la app advierte («Ya tiene 35 en Parcial 1; se cambiará a 42») y el cambio se puede **deshacer**. *(Confirmado.)*
2. Rango válido: `calificación ≥ 0`, **sin tope superior**. Se permiten decimales (ej. 8.5). Sin negativos. *(Confirmado.)*
3. **Promedio de exámenes** = media de las calificaciones **sin normalizar** (puntos tal como se capturaron; sin tope, así que los puntos extra cuentan) sobre **todos** los exámenes del curso. Un examen sin calificación **vale 0** y cuenta en el promedio; en pantalla y exportación se muestra 0 mientras no se capture. Un curso sin exámenes no tiene promedio (vacío). *(Confirmado.)*
4. Los exámenes y calificaciones son independientes de las décimas: **no modifican** `total_con_piso` ni su regla. *(Confirmado: opción a.)*
5. Los oyentes pueden tener calificaciones y se excluyen de exportaciones por defecto, igual que hoy.
6. Eliminar un examen borra sus calificaciones y exige confirmación indicando cuántas se pierden (igual que eliminar un curso). Eliminar un curso borra sus exámenes en cascada.
7. Renombrar un examen es libre mientras el nombre normalizado no se repita en el curso.
8. Sin migración manual: el esquema usa `CREATE TABLE IF NOT EXISTS`, así que las tablas nuevas se crean al abrir una base existente.

## Modelo de datos (cambio propuesto)

```
examen(id PK, curso_id FK→curso ON DELETE CASCADE, nombre, nombre_norm, UNIQUE(curso_id, nombre_norm))
calificacion(examen_id FK→examen ON DELETE CASCADE, alumno_id FK→alumno ON DELETE CASCADE,
             puntos REAL, fecha TEXT, PRIMARY KEY (examen_id, alumno_id))
```

`nombre` se compara normalizado (sin acentos/mayúsculas/espacios sobrantes), como los nombres de alumno. No se guarda el promedio: se calcula siempre (regla 4 de `CLAUDE.md`).

## Reglas de negocio nuevas (se agregarán a `CLAUDE.md` al implementar)

- R12 Exámenes y calificaciones (supuestos 1–7).
- R13 Cálculo del promedio de exámenes en **una sola función** `core/promedio.py::promedio_examenes`; repositorio, servicios y exportador la usan, la UI no recalcula.
- Actualizar la sección Interfaz (registro rápido con selector) y Exportación (columnas de examen y promedio).

## Interfaz

Registro rápido (pantalla Curso):

```
Modo Participación:                       Modo Examen:
[■ Participación][ Examen ]               [ Participación][■ Examen ]
Alumno:  [______________]                 Examen: [Parcial 1 ▼] [+ Nuevo]
Décimas: [____] Nota: [____]              Alumno: [______________]
                    [Registrar]           Calificación: [____]     [Registrar]
```

- El modo se distingue también con color/título del botón de registrar («Registrar examen»).
- Tras guardar, el foco vuelve al campo de alumno y se **conserva el modo y el examen elegido** (se captura una tanda de un mismo examen).
- Si el alumno ya tiene calificación en ese examen, se muestra la advertencia de reemplazo y se pide confirmar antes de guardar (franja con «Confirmar» / «Cancelar»); después queda disponible «Deshacer».
- **Clic en una fila** con el selector en modo Examen carga al alumno y **su calificación actual** en el campo para modificarla (en modo Participación se conserva el comportamiento actual).
- Operable con teclado: **F2** alterna el modo. *(Confirmado.)*
- Reglas de identificación del alumno idénticas al registro actual (cuenta o nombre, parcial, ambiguo pide elegir, no existe ofrece crear). Se reutiliza ese flujo.
- Franja de confirmación no bloqueante: «Ana Pérez · Parcial 1: 42».
- Tabla de alumnos: **una columna por examen**, nombrada «Examen - <nombre>» (se agrega al crear el examen; sin capturar muestra 0). No hay columna de promedio en pantalla. *(Cambio confirmado tras probar la primera versión, que solo mostraba «Prom. exámenes».)* El promedio vive en la exportación.
- Historial de alumno: sección «Exámenes» con sus calificaciones (editar/eliminar con confirmación). *(Incluida en esta entrega.)*
- Crear/editar/eliminar examen desde el diálogo «+ Nuevo» y un menú de exámenes del curso.

## Comandos

```
Pruebas:   python -m pytest
Una prueba: python -m pytest tests/test_examenes.py -q
Ejecutar:  python main.py
Empaquetar: powershell -File scripts/construir_exe.ps1   (subir core/version.py antes)
```

## Estructura (archivos a tocar o crear)

```
core/database.py        → tablas examen y calificacion
core/models.py          → Examen, Calificacion (dataclasses); ResumenAlumno gana prom_examenes
core/promedio.py        → promedio_examenes (única fuente del cálculo)
core/repository.py      → todo el SQL de examenes y calificaciones
core/services.py        → crear/editar/eliminar examen, registrar_calificacion, deshacer, historial de examenes
exporters/curso.py      → columnas por examen y promedio (xlsx y csv)
ui_desktop/vista_curso.py → selector segmentado y campos del modo Examen
ui_desktop/dialogos_curso.py → dialogo de examen (nombre)
ui_desktop/vista_historial.py → seccion Examenes
tests/test_examenes.py, test_promedio.py, test_ui_curso.py (ampliar), test_exportacion.py (ampliar)
CLAUDE.md, README.md    → documentar reglas y alcance
```

## Estilo de código

Español sin acentos ni ñ, type hints, dataclasses en `core/models.py`, SQL solo en el repositorio, errores como `ErrorDominio`:

```python
@dataclass
class Examen:
    id: int | None
    curso_id: int
    nombre: str


def promedio_examenes(puntos: list[float]) -> float | None:
    """Media de los puntos de todos los examenes del curso (sin capturar = 0); None si no hay examenes."""
    if not puntos:
        return None
    return sum(puntos) / len(puntos)
```

## Estrategia de pruebas

pytest, datos ficticios (`100000001`, nombres inventados). Cada regla lleva su prueba:
- `promedio_examenes`: calificaciones por encima de 100 (puntos extra), examen sin capturar cuenta como 0, curso sin exámenes (None).
- Servicio: calificación negativa rechazada (sin tope superior); reemplazo de calificación existente solo tras confirmar (la advertencia trae la nota anterior); deshacer; examen duplicado por nombre normalizado; eliminar examen devuelve cuántas calificaciones se pierden; borrar curso en cascada.
- Independencia: registrar exámenes no cambia `total_alumno` ni `total_con_piso`.
- Exportación: columnas de examen como **números**, promedio numérico, oyentes excluidos por defecto, `.csv` con BOM.
- UI (humo, como `test_ui_curso.py`): alternar modo (clic y F2), clic en fila en modo Examen carga la calificación actual, conservar examen tras guardar, foco vuelve a alumno, avisos de ambiguo/no existe en modo Examen.
- Regresión: toda la suite actual debe seguir pasando sin cambios.

## Límites

- **Siempre:** correr `python -m pytest` antes de cada commit; SQL solo en `core/repository.py`; `core/` sin importar `ui_*`; actualizar `CLAUDE.md` y `README.md` en el mismo cambio; datos ficticios en tests.
- **Preguntar antes:** cambiar el esquema de tablas existentes (alumno, curso, inscripcion, participacion); añadir dependencias; cambiar la regla del piso de 0; cambiar el formato de exportación actual de forma que rompa hojas existentes.
- **Nunca:** guardar el promedio ni totales; copiar datos reales de alumnos; mezclar calificaciones con `decimas` ni con `total_con_piso`; borrar datos sin confirmación explícita.

## Criterios de éxito

1. Puedo crear «Parcial 1», cambiar a modo Examen, capturar 42 para un alumno y ver «Parcial 1: 42» sin usar el mouse tras elegir el examen.
2. Capturar otra vez al mismo alumno reemplaza la nota y avisa la anterior; deshacer la restaura.
3. Una calificación negativa se rechaza con mensaje claro; una mayor a 100 (puntos extra) se acepta.
4. El promedio coincide con el cálculo manual (ej. 3 exámenes, con 42, 70 y uno sin capturar → (42 + 70 + 0) / 3 ≈ 37.33).
5. Participaciones y totales se comportan exactamente como antes.
6. La exportación `.xlsx` y `.csv` trae una columna por examen y el promedio como números; los oyentes siguen excluidos por defecto.
7. Una base `.db` existente abre sin errores y conserva todos sus datos.
8. La suite completa pasa.

## Preguntas abiertas

1. **Supuestos 5–8** (oyentes con calificaciones y excluidos por defecto, borrar examen con confirmación, cascada al borrar curso, renombrar examen sin repetir nombre, tablas creadas sin migración): no los comentaste; los tomo como aceptados salvo que digas lo contrario.
