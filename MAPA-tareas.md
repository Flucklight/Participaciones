# Mapa de capacidades: calificación de tareas

Estado: **aprobado** por la persona. Índice de las specs de esta iniciativa.

La calificación de tareas es el **promedio ya calculado** en otra plataforma; esta app solo lo guarda y lo muestra. No se guardan tareas individuales.

| Módulo (id) | Responsabilidad | Depende de | Spec |
|---|---|---|---|
| `tareas` | Una calificación de tareas por alumno y curso (sin tope, ≥ 0): tablas, reglas, modo «Tareas» en el registro rápido, columna en la tabla del curso, sección en el historial y columna en la exportación | — | `SPEC-tareas.md` |
| `tareas-importacion` | Leer el archivo de la plataforma (.xlsx o .csv, identificado por número de cuenta), previsualizar y aplicar al grupo completo | `tareas` | `SPEC-tareas-importacion.md` (pendiente: se escribe tras aprobar `SPEC-tareas.md` y con un archivo de muestra) |

Orden de construcción: `tareas` → `tareas-importacion`.

Frontera entre módulos: `tareas-importacion` solo llama al servicio de `tareas` para guardar (la misma regla de reemplazo y validación); no escribe SQL ni duplica reglas.

Nota: la spec anterior (`SPEC.md`, exámenes) ya está comiteada y no se modifica.
