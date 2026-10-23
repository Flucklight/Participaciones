# Plan de implementación: calificación del proyecto final (módulo `proyecto`)

Spec: `SPEC-proyecto.md`. Mapa: `MAPA-proyecto.md`. Tareas en `tasks/todo.md`.
(Los planes anteriores viven en `tasks/plan-tareas.md`, `tasks/plan-tareas-importacion.md` y `tasks/plan-equipos.md`. `equipos` ya está en `main`: este módulo solo **lee** los equipos a través del servicio.)

## Resumen
Una calificación de proyecto por alumno y curso (sin tope, ≥ 0), capturable desde el modo «Proyecto → Evaluar»: a **un alumno** (cuenta o nombre) o a **todo un equipo** (escribiendo «equipo N» o con el botón «Usar equipo N»), lo que copia la misma nota a cada miembro. Si algún miembro ya tenía otra nota se avisa («2 de 4 miembros… se cambiarán a 9.5») y se pide confirmar; «Deshacer» devuelve las notas previas de todos. Se ve como columna «Proyecto» en la tabla, fila «Proyecto final» en el historial y columnas «Equipo» y «Proyecto» en la exportación. Independiente de décimas, exámenes y tareas; la nota no se sincroniza con el equipo después de calificar.

## Decisiones de arquitectura
- **Es el módulo de tareas con un destino más.** Se copia el patrón de `registrar_tareas` (identificación compartida `_identificar`, `_puntos_validados`, reemplazo en dos pasos, `deshacer`, `establecer`, `eliminar`). Lo nuevo es el destino «equipo N».
- **El servicio decide el destino.** `registrar_proyecto(curso_id, consulta, puntos, …)` reconoce «equipo N» / «e N» (un número solo sigue siendo número de cuenta); si no, identifica al alumno como siempre. La UI solo pasa lo que se escribió.
- **Una sola forma de resultado** (`ResultadoProyecto`): a quién(es) se aplicó, el equipo si lo hubo, el conteo para la advertencia («N de M») y `anteriores` (`{alumno_id: calificación previa o None}`) que `deshacer_proyecto` restaura. Calificar a un alumno es el caso de un solo miembro: **un solo camino de código** para guardar y deshacer.
- **Sin vínculo nota–equipo:** se guarda la nota del alumno; no hay columna de equipo en `calificacion_proyecto` (si hiciera falta sería un cambio de modelo que se pregunta antes).
- **La advertencia cuenta solo diferencias:** un miembro con la misma nota que la nueva no cuenta como reemplazo.
- **«Evaluar» es el modo «Proyecto» sin «Formar equipos» activo.** Ya existe `_formando`: apagado = evaluar (se ve el campo de registro, el clic en una fila carga al alumno); encendido = formar (se oculta el registro). Así no se agrega un tercer estado ni un selector nuevo.
- **Estado de deshacer:** `_ultimo_proyecto` se suma a los otros cuatro estados; cada guardado nuevo borra los demás (el mismo patrón).
- **Orden de columnas:** «Tareas» · «Proyecto» · exámenes · «Última» en la tabla; en la exportación «Tareas» · «Equipo» · «Proyecto» · exámenes.
- **Colores solo en `tema.py`:** se reutilizan `COLOR_PROYECTO` y `COLOR_AVISO`; no hacen falta colores nuevos.

## Grafo de dependencias

```
tabla calificacion_proyecto + modelos + R17 en CLAUDE.md (T1)
        │
        ▼
servicio: alumno individual (registrar, reemplazo, deshacer, establecer, eliminar, conteo) (T2)
        │
        ▼
servicio: equipo («equipo N», copiar a miembros, «N de M», deshacer de todos) (T3)
        │
        ▼
UI: evaluar a un alumno (campo, reemplazo, deshacer; clic en fila carga la nota) (T4)
        │
        ▼
UI: evaluar a un equipo («equipo N», «Usar equipo N», advertencia N de M) (T5)
        │
   ┌────┴─────────────────┐
   ▼                      ▼
columna «Proyecto»     exportación
y historial (T6)       y eliminar curso (T7)
        └────────┬─────────┘
                 ▼
     documentación y versión 1.5.0 (T8)
```

Orden: T1 → T2 → T3 → T4 → T5; T6 y T7 dependen solo de T2 (pueden ir en cualquier orden); T8 al final.

## Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|---|---|---|
| Reemplazar notas de varios alumnos sin querer | Alto | Advertencia con el conteo «N de M», nada se guarda hasta confirmar y «Deshacer» restaura a **todos**; pruebas del conteo y del deshacer |
| «equipo 3» confundido con cuenta o nombre | Medio | Reconocimiento estricto (`equipo N` / `e N`, mayúsculas indiferentes) en el servicio, probado; un número solo sigue siendo cuenta |
| La nota de equipo se cree «sincronizada» | Medio | No hay vínculo; pruebas: agregar o sacar a alguien no cambia notas, y corregir a uno no mueve al resto |
| Cambiar la lógica de `_formando` rompe lo ya hecho de equipos | Alto | Las 100+ pruebas de equipos son la red; solo cambia qué se muestra al apagar «Formar equipos» |
| El estado de deshacer se pisa entre capturas distintas | Medio | El mismo patrón de limpieza cruzada; pruebas de «otra captura reemplaza lo deshacible» también con proyecto |
| Un equipo con miembros sin inscripción vigente o borrados | Bajo | Los miembros salen del servicio de equipos (siempre inscritos); prueba con equipo de 1 alumno y con oyentes |
| El historial y la exportación cambian de columnas y rompen pruebas | Medio | Ajustar solo expectativas de orden; la suite actual es la regresión |

## Preguntas abiertas
Ninguna bloqueante. Los supuestos de la spec (1–11) se mantienen; el plan sigue exactamente lo que la persona aprobó (sintaxis «equipo N», «Usar equipo N», sin sincronización, columna «Equipo» en la exportación).
