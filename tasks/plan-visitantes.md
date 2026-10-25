# Plan de implementación: visitantes de otro grupo (módulo `visitantes`)

Spec aprobada: `SPEC-visitantes.md`. Tareas en `tasks/todo-visitantes.md`.

## Resumen
Un regular de un grupo puede ser **Visitante** en otro grupo de la misma materia y ciclo. Todo lo que se le capture desde el grupo visitado se guarda en su grupo de origen; el grupo visitado lo muestra y lo captura. Es un **cambio de modelo** (tipo nuevo y vínculo al origen), así que `CLAUDE.md` se actualiza primero (T1).

## Decisiones de arquitectura
- **Los datos nunca se duplican.** Los visitantes no tienen filas de participaciones, calificaciones ni tareas/proyecto en el grupo visitado; solo `inscripcion` (con el origen) y, si la hay, su `miembro_equipo` allí.
- **Un único punto de redirección:** `ServicioParticipaciones._curso_de_datos(curso_id, alumno_id)` devuelve el curso donde viven los datos (el origen si es visitante, si no el mismo). Los servicios de captura y de historial lo llaman; no se repite la lógica.
- **Esquema:** se agrega `VISITANTE` a `TipoInscripcion` y la columna `curso_origen_id` a `inscripcion` (`REFERENCES curso(id) ON DELETE CASCADE`, NULL para regular/oyente). El `CHECK` de `tipo` obliga a **reconstruir la tabla** `inscripcion` (SQLite no altera CHECK): crear nueva, copiar, borrar, renombrar, en una transacción y **con un respaldo automático antes** (`respaldar`). La alternativa de dejar `tipo='oyente'` más una tabla `visita` evita la migración pero crea dos formas de representar lo mismo; se descarta.
- **Borrar el curso de origen** borra las inscripciones de visita por la cascada; lo que no cascada es el `miembro_equipo` del visitante en el grupo visitado, que el repositorio borra explícitamente antes. El servicio cuenta los visitantes para el diálogo (R1).
- **Exámenes:** correspondencia por **nombre normalizado** entre el examen del grupo visitado y el del origen, sin crear nada. La resolución vive en el servicio; sin homónimo → `ErrorDominio` con el mensaje de la spec.
- **Lectura (`resumen_curso`) del grupo visitado:** para las filas de visitante, el repositorio toma la fila del origen y la presenta con `tipo=VISITANTE`, `equipo` del grupo visitado y `calificaciones` reindexadas a los ids de los exámenes del grupo visitado (por nombre; los que no existan allá no aparecen). La **final** se calcula con las ponderaciones y los exámenes del **origen**: el servicio la hace con `calificacion_final`, que sigue siendo la única función.
- **Equipos:** `formar_equipo`/`agregar_a_equipo` consultan los demás cursos (origen y visitas) del alumno antes de aceptar; si ya está en un equipo en otro, devuelven `YA_TIENEN_EQUIPO` indicando grupo y número (mismo estado que hoy, con el grupo en el mensaje). «Equipo N» califica en el origen a quien sea visitante.
- **Nota automática:** al registrar una participación a un visitante desde el grupo visitado, el servicio antepone «Grupo <grupo del curso visitado>» a la nota capturada.
- **Eliminar (R20):** `_oyente_en_curso` acepta también visitantes; la instantánea incluye `curso_origen_id`; para un visitante no hay datos que borrar salvo equipo, y nunca se toca el origen. «Deshacer» restaura inscripción de visita y equipo.
- **Colores y etiquetas solo en `tema.py`** (un par nuevo para «Visitante»).

## Grafo de dependencias

```
modelo + migración + R21 en CLAUDE.md (T1)
        │
        ▼
alta y vínculo: candidatos, inscribir_visitante, _curso_de_datos (T2)
        │
   ┌────┴─────────────────────────┐
   ▼                              ▼
capturas redirigidas (T3)    lectura: resumen, historial, final (T4)
   │                              │
   └────────────┬─────────────────┘
                ▼
     equipos entre los dos grupos (T5)
                │
        ┌───────┼────────────┐
        ▼       ▼            ▼
 eliminar    exportar    fusión de base
 visita y    (T7)        (T8)
 curso (T6)
        └───────┴────────────┘
                ▼
        interfaz (T9)
                ▼
     documentación y versión 1.7.0 (T10)
```

Orden: T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 (T3 y T4 pueden ir en cualquier orden; T6, T7 y T8 dependen de T5 y son independientes entre sí).

## Riesgos
| Riesgo | Mitigación |
|---|---|
| La reconstrucción de `inscripcion` pierde datos o deja una base a medias | Respaldo automático antes, una sola transacción, pruebas con una base 1.6.x real de prueba (ficticia) y con la base vacía |
| Una captura sigue yendo al grupo visitado por olvidar `_curso_de_datos` | Prueba por cada servicio de captura (participación, examen, tareas, proyecto, equipo) más una que cuenta filas en el grupo visitado = 0 |
| Final distinta vista desde A y desde B | Prueba que compara las dos finales; el cálculo de visitantes usa siempre las ponderaciones del origen |
| Cascada de borrado deja `miembro_equipo` huérfanos | Prueba de borrar el origen con visitante en un equipo del grupo visitado |
| R19 (exportar/fusionar) rechaza o duplica visitas | Pruebas de exportar con visitas, fusionar y reimportar (idempotente) y migrar un archivo 1.6.x |
| Reglas de equipo entre grupos rompen formar equipos existente | Las pruebas de equipos existentes siguen en verde; la regla nueva solo se activa si hay otra inscripción de la misma materia y ciclo |

## Puntos de verificación
- Tras T1: bases antiguas abren sin pérdida y la suite sigue en verde.
- Tras T5: toda la lógica de negocio probada sin UI.
- Tras T8: exportar/fusionar/migrar completos.
- Tras T9: prueba manual con `main.py` (dos grupos, un regular visitante, capturar desde ambos).
- Tras T10: suite completa y commit.
