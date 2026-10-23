# Spec: Calificación de tareas (módulo `tareas`)

Estado: **BORRADOR, con las preguntas abiertas ya respondidas; falta la aprobación explícita** (sin código ni cambios a `CLAUDE.md` todavía). Índice: `MAPA-tareas.md`.

## Objetivo

Además de décimas de participación y exámenes, el profesor lleva la **calificación de tareas** de cada alumno. Esa calificación ya viene promediada de otra plataforma: la app **solo la guarda y la muestra**, no calcula nada sobre tareas.

Usuario: el profesor, que captura o corrige la calificación de un alumno durante o después de clase, con teclado.

Decisiones ya tomadas con el usuario:
- **Una sola calificación de tareas por alumno y curso** (el promedio vigente). Subir otra vez **reemplaza** el valor, con advertencia previa y opción de deshacer, igual que en exámenes.
- **Sin tope**: cualquier número ≥ 0, con decimales.
- Aparece en: registro rápido (nuevo modo «Tareas»), **columna «Tareas»** en la tabla del curso, **historial** del alumno y **exportación** (.xlsx y .csv).
- La captura por archivo vive en otro módulo (`tareas-importacion`).

## Supuestos (corrígeme ahora o procedo con ellos)

1. Una tarea sin calificación **vale 0** (como los exámenes), y se muestra 0 en pantalla y exportación mientras no se capture.
2. La calificación de tareas es **independiente** de décimas y exámenes: no modifica `total_con_piso` ni el «Promedio exámenes» (R13), y no entra en ningún promedio.
3. Se guarda con su **fecha de captura** (hoy por defecto; editable desde el historial). Solo hay un valor vigente: no se conserva el historial de cambios.
4. Los **oyentes** pueden tener calificación de tareas y se excluyen de la exportación por defecto, igual que el resto.
5. Eliminar un curso borra su calificación de tareas, y el diálogo de eliminación informa cuántas se pierden.
6. Se reutiliza la identificación de alumno del registro rápido (cuenta, nombre parcial, varias coincidencias, no existe → crear regular u oyente).
7. Sin migración manual: la tabla nueva se crea sola al abrir una base existente (`CREATE TABLE IF NOT EXISTS`).

## Modelo de datos (cambio propuesto)

```
calificacion_tareas(curso_id FK→curso ON DELETE CASCADE, alumno_id FK→alumno ON DELETE CASCADE,
                    puntos REAL, fecha TEXT, PRIMARY KEY (curso_id, alumno_id))
```

No se guarda ningún promedio calculado por la app: el valor es el que el profesor captura o importa.

## Reglas de negocio nuevas (se agregarán a `CLAUDE.md` al implementar)

- **R14 Calificación de tareas:** supuestos 1–6 arriba; una por alumno y curso, `>= 0`, sin tope; reemplazo con advertencia y confirmación; deshacer.
- Actualizar Modelo de datos, Interfaz (modo «Tareas», columna, historial) y Exportación (columna «Tareas»).

## Interfaz

**Registro rápido** — el selector pasa a tres modos `[Participación | Examen | Tareas]`:

```
Modo Tareas:
[ Participación ][ Examen ][■ Tareas ]
Alumno: [______________]  Calificación de tareas: [____]  [Registrar tareas]
```

- No hay lista de exámenes: es una sola calificación por alumno.
- Color propio del modo (propuesta: cian/verde azulado, distinto del azul de participaciones, el índigo de exámenes y el ámbar de avisos).
- **F2 recorre los tres modos** en ciclo: Participación → Examen → Tareas → Participación.
- Misma mecánica que exámenes: tras guardar, foco al campo de alumno y se conserva el modo; si el alumno ya tenía calificación, la franja avisa «Ya tiene X en tareas; se cambiará a Y» con «Reemplazar» / «Cancelar» (no guarda hasta confirmar); «Deshacer» restaura la anterior o elimina la calificación.
- En modo Tareas, elegir a un alumno (clic en fila o sugerencia) **carga su calificación actual** para corregirla.
- Franja de confirmación no bloqueante: «Ana Pérez · Tareas: 8.4».

**Tabla del curso:** una columna **«Tareas»** entre «Décimas» y las columnas de examen; muestra 0 si no hay captura; ordenable.

**Historial del alumno:** la sección de calificaciones pasa a llamarse «Exámenes y tareas»; su primera fila es **«Tareas»** (calificación y fecha, 0 y «—» si no hay) y después los exámenes. «Calificar / editar» y «Quitar calificación» funcionan igual sobre cualquier fila.

**Exportación:** columna «Tareas» en el «Resumen» (xlsx y csv), después de «Décimas» y antes de las columnas de examen, como **número**; siempre presente (sin tareas capturadas vale 0).

## Comandos

```
Pruebas:    .venv\Scripts\python.exe -m pytest
Una prueba: .venv\Scripts\python.exe -m pytest tests/test_tareas.py -q
Ejecutar:   .venv\Scripts\python.exe main.py
Empaquetar: powershell -ExecutionPolicy Bypass -File scripts\construir_exe.ps1   (subir core/version.py antes)
```

## Estructura (archivos a tocar o crear)

```
core/database.py        → tabla calificacion_tareas
core/models.py          → CalificacionTareas; ResumenAlumno gana `tareas: float`; resultado de registro de tareas
core/repository.py      → todo el SQL de calificacion_tareas
core/services.py        → registrar_tareas / registrar_tareas_para_alumno (reemplazo en dos pasos), deshacer_tareas,
                          tareas_de, establecer_tareas, eliminar_tareas; conteo al eliminar un curso
exporters/curso.py      → columna «Tareas»
ui_desktop/tema.py      → color del modo Tareas
ui_desktop/vista_curso.py → selector de 3 modos, registro, columna, F2 en ciclo
ui_desktop/vista_historial.py, dialogos_historial.py → fila «Tareas» en la sección de calificaciones
ui_desktop/dialogos.py, vista_cursos.py → el diálogo de eliminar curso cuenta las tareas
tests/test_tareas.py, test_ui_curso.py, test_ui_historial.py, test_exportacion.py, test_cursos.py (ampliar)
CLAUDE.md, README.md    → documentar reglas y alcance; subir core/version.py
```

## Estilo de código

Español sin acentos ni ñ, type hints, dataclasses en `core/models.py`, SQL solo en el repositorio, errores como `ErrorDominio`, el mismo patrón que exámenes:

```python
@dataclass
class CalificacionTareas:
    """Calificación de tareas de un alumno en un curso (una por alumno y curso; sin tope)."""

    curso_id: int
    alumno_id: int
    puntos: float
    fecha: date
```

## Estrategia de pruebas

pytest, datos ficticios (`100000001`, nombres inventados). Cada regla lleva su prueba:
- Esquema: la tabla se crea en base nueva y en una existente sin perder datos; PK única; cascada al borrar curso.
- Servicio: negativo, `nan` y texto rechazados; 0 y puntos extra aceptados; reemplazo solo tras confirmar (la advertencia trae la nota anterior); deshacer restaura o elimina; identificación (cuenta, nombre parcial, ambiguo, no existe); alumno no inscrito rechazado; independencia de `total_alumno` y de `prom_examenes`.
- Resumen: `tareas` = 0 sin captura; refleja lo capturado.
- Exportación: columna «Tareas» numérica en xlsx y csv; oyentes excluidos por defecto; orden de columnas con y sin exámenes; un curso sin ningún dato exporta 0.
- UI (humo, patrones de `test_ui_curso.py`): alternar modos (clic y F2 en ciclo), registrar, reemplazar con confirmación, deshacer, clic en fila carga la calificación actual, columna y orden, historial (editar, quitar con confirmación), diálogo de eliminar curso con conteo.
- Regresión: toda la suite actual (229 pruebas) debe seguir pasando; el selector de dos modos pasa a tres, así que las pruebas de exámenes y de F2 se ajustan solo donde cambie el ciclo.

## Límites

- **Siempre:** correr `.venv\Scripts\python.exe -m pytest` antes de cada commit; SQL solo en `core/repository.py`; `core/` sin importar `ui_*`; actualizar `CLAUDE.md` y `README.md` en el mismo cambio; datos ficticios en pruebas; colores solo en `tema.py`.
- **Preguntar antes:** cambiar tablas existentes (alumno, curso, inscripcion, participacion, examen, calificacion); añadir dependencias; cambiar la regla del piso de 0 o la del promedio de exámenes.
- **Nunca:** calcular o guardar un promedio de tareas (se guarda el valor recibido); mezclar tareas con `decimas`, `total_con_piso` o el promedio de exámenes; copiar datos reales de alumnos; borrar datos sin confirmación explícita.

## Criterios de éxito

1. En modo Tareas, escribir cuenta y «8.4» y presionar Enter guarda la calificación y la franja dice «<Alumno> · Tareas: 8.4»; todo es posible sin usar el mouse tras elegir el modo (F2).
2. Capturar de nuevo al mismo alumno advierte «Ya tiene 8.4 en tareas; se cambiará a 9» y no guarda hasta confirmar; «Deshacer» restaura 8.4.
3. Una calificación negativa o no numérica se rechaza con mensaje claro; 0 y valores sobre 10 (o 100) se aceptan.
4. La tabla del curso muestra la columna «Tareas» (0 sin captura) y se puede ordenar por ella.
5. En el historial, la fila «Tareas» se puede calificar, corregir y quitar (con confirmación; vuelve a valer 0).
6. El `.xlsx` y el `.csv` traen «Tareas» como número, antes de las columnas de examen, y los oyentes siguen excluidos por defecto.
7. Décimas, exámenes y su promedio se comportan exactamente como antes.
8. Una base `.db` existente abre sin errores y conserva todos sus datos; eliminar un curso informa cuántas calificaciones de tareas se pierden.
9. La suite completa pasa.

## Preguntas abiertas

Ninguna. Respuestas de la persona: (1) sin captura se muestra **0**; (2) **F2 recorre los tres modos en ciclo**; (3) color **verde azulado**; (4) la fila «Tareas» va **junto a los exámenes**. Los supuestos 3–7 se toman como aceptados.
