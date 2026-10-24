# Plan de implementación: eliminar alumno oyente (módulo `eliminar-alumno`)

Spec aprobada: `SPEC-eliminar-alumno.md`. Tareas en `tasks/todo-eliminar-alumno.md`.

## Resumen
Acción «Eliminar alumno» en la pantalla Curso, solo para oyentes, desde un botón junto a «Agregar alumno» y desde el clic derecho. Quita al oyente de **ese** curso con todo lo suyo ahí; si no queda en otro curso, borra también a la persona. Confirma con conteos y se puede deshacer (restaura todo).

## Decisiones de arquitectura
- **Sin cambios de esquema.** Los datos por curso (`participacion`, `calificacion` de exámenes de ese curso, `calificacion_tareas`, `calificacion_proyecto`, `miembro_equipo`) se borran explícitamente por `(curso_id, alumno_id)`, porque el `ON DELETE CASCADE` solo actúa al borrar el alumno o el curso. Todo en una transacción.
- **Instantánea para deshacer** (`InstantaneaAlumno`, dataclass en `models.py`): alumno completo, tipo de inscripción, participaciones (con fecha y nota), calificaciones de exámenes del curso, tareas, proyecto, número de equipo y si el alumno se borró. La arma el servicio con los `obtener_*`/`listar_*` que ya existen; el repositorio solo agrega el borrado por curso y la restauración.
- **El servicio devuelve la instantánea** y la UI la guarda en `_ultima_eliminacion`, igual que `_ultimo_proyecto`/`_ultima_equipo`: revierte solo lo último y se invalida en la siguiente captura (se suma a las asignaciones que ya limpian los demás `_ultimo_*`).
- **Restauración atómica:** valida antes de escribir (cuenta libre, equipo existente, curso existente, alumno no reinscrito) y falla con `ErrorDominio` sin dejar nada a medias. Las participaciones vuelven con otros `id`; el total se recalcula con `total_con_piso`, que depende de (fecha, id), por eso se reinsertan en su orden original.
- **Regla en el servicio**, no solo en la UI: `tipo != oyente` → `ErrorDominio`.
- **Resumen para confirmar** (`resumen_eliminacion`) lo calcula el servicio; la UI solo lo muestra.
- **UI:** el clic derecho hoy solo existe con «Formar equipos» activo; `_menu_equipos` queda intacto y se agrega un `_menu_alumno` para el modo normal. En «Formar equipos» no aparece la acción.
- Colores solo en `tema.py` (rojo de peligro ya existe).

## Grafo de dependencias

```
repositorio: contar, borrar por curso, restaurar (T1)
        │
        ▼
servicio: resumen, eliminar, deshacer + R20 en CLAUDE.md (T2)
        │
        ▼
diálogo de confirmación (T3)
        │
        ▼
botón + clic derecho + franja con «Deshacer» (T4)
        │
        ▼
documentación y versión 1.6.2 (T5)
```

Orden estricto T1 → T2 → T3 → T4 → T5.

## Riesgos
| Riesgo | Mitigación |
|---|---|
| Restaurar deja datos a medias | Validar todo antes de escribir y una sola transacción; prueba con cuenta ocupada |
| Total distinto tras deshacer (orden de participaciones) | Reinsertar en orden (fecha, id) y probar que el total antes = después |
| Borrar de más (otros cursos) | Pruebas con el oyente inscrito en dos cursos y con otros alumnos intactos |
| Interferir con el menú de equipos | `_menu_equipos` no se modifica; prueba de que el modo equipos sigue igual |
| Deshacer en conflicto con otros `_ultimo_*` | Una sola variable más y las mismas limpiezas que el resto |

## Puntos de verificación
- Tras T2: lógica completa probada sin UI.
- Tras T4: prueba manual de punta a punta (`main.py`): crear oyente, darle participaciones/examen/equipo, eliminar, deshacer.
- Tras T5: suite completa y `scripts/construir_exe.ps1` solo si lo pides.
