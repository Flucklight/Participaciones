# Plan de implementación: calificaciones de exámenes

Spec: `SPEC.md` (aprobada). Tareas en `tasks/todo.md` (lista de verificación).

## Resumen
Agregar exámenes por curso (solo nombre, sin tope) y una calificación por alumno y examen, capturables desde el registro rápido de la pantalla Curso con un selector segmentado `[Participación | Examen]`. El promedio de exámenes es la media simple de los puntos sobre **todos** los exámenes del curso (sin capturar = 0). Independiente de las décimas y de `total_con_piso`.

## Grafo de dependencias

```
tablas examen/calificacion + modelos + CLAUDE.md (T1)
        │
        ├── promedio_examenes (T2) ──┐
        │                            ▼
        └── repositorio + servicio de examenes (T3)
                     │
                     ▼
        registrar calificacion + reemplazo + deshacer + promedio en resumen (T4)
                     │
     ┌───────────────┼────────────────┐
     ▼               ▼                ▼
 UI selector     Exportacion     Historial
 T5 -> T6        (T7)            examenes (T8)
     └───────────────┴────────────────┘
                     ▼
        gestion de examenes + docs + version (T9)
```

Orden: base de datos y reglas (T1–T4) → UI del registro (T5–T6) → exportación (T7) → historial (T8) → cierre (T9). T7 y T8 dependen solo de T4 y pueden ir en cualquier orden.

## Decisiones de arquitectura
- **Dos tablas nuevas, sin tocar las existentes.** `ESQUEMA` usa `CREATE TABLE IF NOT EXISTS`, así que una base vieja las gana al abrir; no hay migración.
- **Una sola fuente del promedio:** `core/promedio.py::promedio_examenes(puntos)`. Los exámenes sin calificación se pasan como `0.0`; la lista completa la arma el servicio/repositorio. La UI y el exportador no calculan.
- **Reemplazo en dos pasos, sin estado en la UI:** `registrar_calificacion` devuelve `EstadoRegistro.CONFIRMAR_REEMPLAZO` con la nota anterior; la UI muestra la franja «Ya tiene X; se cambiará a Y» y, si el usuario confirma, llama de nuevo con `reemplazar=True`. Deshacer restaura la nota anterior (o borra la calificación si no había).
- **Se reutiliza el flujo de identificación de alumno** (cuenta, nombre parcial, ambiguo, no existe) del registro de participaciones: la parte común se extrae en `services.py`, no se duplica.
- **UI:** el selector vive en `vista_curso.py`; el modo y el examen elegido se conservan tras guardar. El clic en fila en modo Examen carga la calificación actual del alumno.
- Se mantiene la regla de `CLAUDE.md`: SQL solo en `core/repository.py`, `core/` sin importar `ui_*`.

## Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|---|---|---|
| `vista_curso.py` (508 líneas) se vuelve difícil de seguir al añadir modos | Media | T5 aísla el estado del modo en un pequeño conjunto de métodos; si crece, extraer el panel de registro a su propio módulo en la misma tarea |
| Regresión en el registro de participaciones | Alta | La suite actual (`test_ui_curso.py`, `test_registro.py`) debe pasar sin modificarse en cada checkpoint |
| Exportador asume columnas fijas | Media | T7 parametriza el encabezado por los exámenes del curso y reutiliza `_numero`, con pruebas xlsx y csv |
| Pruebas UI frágiles (diálogos modales) | Media | Seguir los helpers existentes de `tests/test_ui_curso.py` (`buscar_dialogo`, etc.) |
| Nombres de examen con acentos/mayúsculas duplicados | Baja | `nombre_norm` con `core/normalizacion.py`, único por curso |

## Preguntas abiertas
Ninguna. Los supuestos 5–8 de la spec se tomaron como aceptados.
