# Plan de implementación: calificación de tareas (módulo `tareas`)

Spec aprobada: `SPEC-tareas.md`. Mapa: `MAPA-tareas.md`. Tareas en `tasks/todo.md`.
(Los planes anteriores, de exámenes, están completos y viven en el historial de git, commits `f4bff6c` y `d0b92d0`.)

## Resumen
Una calificación de tareas por alumno y curso (sin tope, ≥ 0), capturable desde un tercer modo «Tareas» del registro rápido, visible como columna en la tabla del curso, como fila en el historial del alumno y como columna en la exportación. Es un valor ya promediado que se guarda tal cual; no se calcula nada. Independiente de décimas y exámenes.

## Grafo de dependencias

```
tabla calificacion_tareas + modelo + R14 en CLAUDE.md (T1)
        │
        ▼
servicio: registrar, reemplazo en dos pasos, deshacer, establecer/eliminar,
          `tareas` en el resumen, conteo al eliminar curso (T2)
        │
   ┌────┴─────────────┬───────────────────┐
   ▼                  ▼                   ▼
selector de 3 modos  exportación (T5)   historial (T6)
y captura (T3)
   │
   ▼
reemplazo, deshacer, clic en fila, columna (T4)
   └────────────┬──────────────────────────┘
                ▼
   diálogo de eliminar curso, docs y versión (T7)
```

Orden: T1 → T2 → T3 → T4; T5 y T6 dependen solo de T2 y pueden ir en cualquier orden; T7 al final.

## Decisiones de arquitectura
- **Una tabla nueva, sin tocar las existentes** (`CREATE TABLE IF NOT EXISTS`, sin migración). Clave primaria `(curso_id, alumno_id)`: una sola calificación vigente.
- **Mismo patrón que exámenes**, no una abstracción nueva: el servicio ya tiene `_identificar`, la validación de puntos (`_puntos_validados`) y el reemplazo en dos pasos. Tareas los reutiliza; el resultado es un `ResultadoTareas` propio (sin `examen`), para no ensuciar `ResultadoCalificacion`.
- **Modos de la pantalla Curso:** hoy `_modo` es `"participacion" | "examen"`. Pasa a incluir `"tareas"`; `_alternar_modo` (F2) recorre los tres en ciclo. La fila de «Examen» (lista, «＋ Nuevo», «⋯») solo se muestra en modo Examen. El reemplazo pendiente y el deshacer se generalizan para cubrir ambos tipos de calificación sin duplicar la franja de confirmación.
- **Un solo estado de deshacer:** lo último guardado (participación, examen o tareas) es lo que «Deshacer» revierte, como ya ocurre entre participación y examen.
- **Color del modo Tareas** en `tema.py` (verde azulado, par claro/oscuro con texto blanco legible), sin valores sueltos en las vistas.
- Se mantiene: SQL solo en `core/repository.py`, `core/` sin importar `ui_*`, la UI no calcula.

## Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|---|---|---|
| `vista_curso.py` (≈ 900 líneas) crece con un tercer modo | Media | T3 concentra el estado del modo en pocos métodos; si el archivo se vuelve inmanejable, extraer el panel de registro a su propio módulo dentro de T3 |
| Las pruebas actuales asumen un F2 de dos modos y `_modo` binario | Media | Se ajustan solo esas pruebas (F2 en ciclo); el resto de la suite debe pasar sin tocarse |
| Regresión en participaciones o exámenes | Alta | Suite completa en cada checkpoint; `test_registro.py`, `test_calificaciones.py` y las UI de curso sin modificar salvo lo del F2 |
| Reemplazo pendiente compartido entre exámenes y tareas | Media | Un único `_pendiente` con el tipo de calificación; pruebas de cambiar de modo con un reemplazo sin confirmar |
| Tabla del curso más ancha (columna nueva) | Baja | Ya tiene desplazamiento horizontal; columna angosta |

## Preguntas abiertas
Ninguna para este módulo. La importación (`tareas-importacion`) tiene su propia spec y preguntas.
