# Mapa de capacidades: proyecto final por equipos

Estado: **la persona eligió dividirlo en dos módulos** (falta su visto bueno al mapa completo junto con las specs). Índice de las specs de esta iniciativa.

El proyecto final se califica **por equipo**, pero la calificación se guarda **por alumno** (una por alumno y curso, sin tope, ≥ 0): calificar a un equipo la copia a todos sus miembros, y después se puede corregir a cada uno por separado. Los equipos se forman y se separan solo en la sección «Proyecto».

| Módulo (id) | Responsabilidad | Depende de | Spec |
|---|---|---|---|
| `equipos` | Formar equipos con varios alumnos (número incremental por curso, que no se reutiliza), separar miembros con clic derecho, y la sección «Proyecto» (cuarto modo) que ordena la tabla por equipo y número | — | `SPEC-equipos.md` |
| `proyecto` | Calificación del proyecto final: captura individual o por equipo (se copia a todos los miembros), reemplazo con confirmación y deshacer, columna en la tabla, fila en el historial, columnas en la exportación | `equipos` | `SPEC-proyecto.md` |

Orden de construcción: `equipos` → `proyecto`.

Frontera entre módulos: `proyecto` solo **lee** los equipos a través del servicio (quiénes son los miembros de un equipo); no escribe SQL de equipos ni duplica sus reglas. `equipos` no sabe nada de calificaciones. Al terminar `equipos` la sección «Proyecto» ya existe y funciona para formar equipos; `proyecto` le agrega el modo de evaluar.

Nota: las specs anteriores (`SPEC.md` exámenes, `SPEC-tareas*.md`) ya están comiteadas y no se modifican.
