# Plan de implementación: equipos para el proyecto final (módulo `equipos`)

Spec: `SPEC-equipos.md`. Mapa: `MAPA-proyecto.md`. Tareas en `tasks/todo.md`.
(Los planes anteriores viven en `tasks/plan-tareas.md` y `tasks/plan-tareas-importacion.md`. El módulo `proyecto` tendrá su propio plan cuando `equipos` esté terminado.)

## Resumen
Un cuarto modo «Proyecto» en el selector de la pantalla Curso. En él, un botón «Formar equipos» activa la selección múltiple y permite crear equipos (número incremental por curso que nunca se reutiliza, desde 1 alumno), y el clic derecho «Separar» saca a un miembro. La tabla, solo en este modo, se agrupa por equipo con **filas de encabezado coloreadas** («Equipo 2 · 3 alumnos»), dos tonos alternados, y los alumnos sin equipo al final. No toca calificaciones.

## Decisiones de arquitectura
- **Reglas en el servicio, SQL en el repositorio.** `formar_equipo` devuelve un resultado (formado, o «ya tienen equipo» con quién y cuál) sin escribir nada si rechaza. Separar y deshacer devuelven lo necesario para revertir (`{alumno_id: número}`).
- **El número nunca se reutiliza sin tocar `curso`:** los equipos vacíos no se borran; el siguiente número es `MAX(numero)+1` en `equipo`. La vista ignora los equipos sin miembros.
- **Un alumno, un equipo:** la PK `(curso_id, alumno_id)` de `miembro_equipo` lo garantiza aun si el servicio fallara.
- **Tabla agrupada = filas de encabezado en el mismo `Treeview`** (variante C elegida). Las filas de encabezado llevan iid `equipo_N` (los alumnos usan su id como texto) y toda la lógica que reacciona a filas (clic, doble clic, selección, resaltado, menú contextual) las ignora explícitamente. La agrupación vive en una función pura (`agrupar_por_equipo`) fácil de probar sin UI.
- **Orden:** por equipo y, dentro de cada uno, por la columna elegida (nombre por omisión); los equipos conservan su orden por número. En los otros tres modos nada cambia.
- **Colores solo en `tema.py`:** `COLOR_PROYECTO` (+ hover) para el modo y dos pares de tonos (encabezado fuerte y fila suave) para equipos; `configurar_estilo()` los entrega a las etiquetas del `Treeview`.
- **El modo «Proyecto» no tiene campo de registro todavía** (llega con el módulo `proyecto`): la franja de registro se reemplaza por la ayuda y las herramientas de equipo.

## Grafo de dependencias

```
tablas equipo y miembro_equipo + modelos + R16 en CLAUDE.md (T1)
        │
        ▼
servicio: formar, separar, deshacer, consultas, equipo en el resumen (T2)
        │
        ▼
cuarto modo «Proyecto»: selector, F2 de cuatro, color, columna «Equipo»,
tabla agrupada con encabezados coloreados (T3)
        │
        ▼
«Formar equipos»: selección múltiple, barra, crear, rechazo y deshacer (T4)
        │
        ▼
clic derecho «Separar» (una o varias filas) y deshacer (T5)
        │
        ▼
documentación y versión 1.4.0 (T6)
```

Orden: T1 → T2 → T3 → T4 → T5 → T6. T3 es la rebanada vertical más riesgosa (cambia cómo se dibuja la tabla): va antes de las acciones para fallar pronto.

## Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|---|---|---|
| Las filas de encabezado se cuelan en el clic, la selección, el resaltado o el conteo | Alto | Prefijo propio de iid, un solo punto que decide «¿es alumno?», y pruebas de UI específicas para cada reacción |
| El orden por otra columna se rompe con grupos | Medio | Orden dentro de cada equipo en `agrupar_por_equipo`, probado como función pura |
| El clic en una fila deja de cargar al alumno en otros modos | Alto | La selección múltiple y el cambio de clic solo existen con «Formar equipos» activo; pruebas de regresión del clic en los demás modos |
| Los tonos de equipo chocan con la selección azul o el resaltado verde | Medio | Revisar capturas en claro y oscuro con selección y resaltado (se hizo el prototipo; se repite en la UI real) |
| Cambiar de tres a cuatro modos rompe las pruebas de F2 y del selector | Bajo | Ajustarlas solo donde el ciclo cambie |
| `Treeview` con selección múltiple y el evento `<ButtonRelease-1>` existente | Medio | Separar el manejador de clic por modo y probarlo con Ctrl/Mayús |

## Preguntas abiertas
- ¿Hacer clic en el encabezado de un equipo debería **seleccionar a todos sus miembros** (útil para separar a todos o ver el equipo)? La spec dice que el encabezado no hace nada; lo dejo así salvo que pidas lo contrario.
