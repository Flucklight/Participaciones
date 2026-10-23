# Plan de implementación: importar calificaciones de tareas (módulo `tareas-importacion`)

Spec: `SPEC-tareas-importacion.md`. Mapa: `MAPA-tareas.md`. Tareas en `tasks/todo.md`.
(El plan del módulo `tareas`, completo y fusionado en `main`, quedó en `tasks/plan-tareas.md` y `tasks/todo-tareas.md`.)

## Resumen
Un botón «Importar tareas» en la pantalla Curso lee un `.xlsx` o `.csv` de otra plataforma, muestra una vista previa (quién cambia, quién queda igual, dudosos, omitidos) y, solo al confirmar, reemplaza la calificación de tareas de cada alumno identificado **por nombre**. Se puede deshacer la importación completa. Reutiliza el servicio de `tareas` para validar y guardar.

## Decisiones de arquitectura
- **Lector sin base ni UI** (`importers/calificaciones_plataforma.py`, como `lista_aragon.py`): localiza alumnos por su forma (apellidos y nombres no vacíos, «@» en la 3.ª columna, algún número), no por posiciones fijas; devuelve columnas numéricas con rótulo y filas con `valores` por rótulo. Cubre las dos disposiciones (xlsx y csv).
- **Coincidencia por nombre en el servicio** (regla de negocio): exacta única → aplica; por palabras única → dudosa (solo con confirmación); varias o ninguna → omitida. Nunca crea alumnos. Si el archivo trae columna de cuenta, tiene prioridad (supuesto 1b).
- **Tres pasos en el servicio:** `previsualizar_importacion_tareas` (no escribe), `importar_tareas(confirmadas)` (una transacción) y `deshacer_importacion_tareas`. La vista previa y la importación comparten el mismo cálculo para que nunca difieran.
- **Lectura única de calificaciones** del curso (`tareas_por_alumno` ya existe) para calcular «antes → después» sin consultas por alumno.
- **UI delgada:** `DialogoImportarTareas` solo muestra lo que devuelve el servicio; el botón y la franja de «Deshacer importación» viven en `vista_curso.py`.

## Grafo de dependencias

```
modelos + lector xlsx/csv (T1) ──► servicio: vista previa y coincidencia (T2)
                                        │
                                        ▼
                         importar y deshacer, transacción (T3)
                                        │
                                        ▼
                    diálogo con vista previa y botón en Curso (T4)
                                        │
                                        ▼
                  franja «Deshacer importación», docs R15 y versión (T5)
```

Orden: T1 → T2 → T3 → T4 → T5. Se documenta R15 en `CLAUDE.md` al iniciar T2 (el proyecto exige proponer la regla antes de implementarla).

## Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|---|---|---|
| Dos disposiciones distintas (xlsx y csv) y más que puedan venir | Alto | Detectar alumnos por forma; pruebas con ambas disposiciones ficticias y muestras reales opcionales por variable de entorno |
| Nombres que no coinciden (orden, acentos, segundo nombre) | Medio | Coincidencia exacta → por palabras (dudosa, confirmada a mano); lo demás se lista, nunca se adivina |
| Fórmula sin valor calculado guardado en el xlsx | Medio | Leer con `data_only=True`; celda vacía = «sin dato», no cambia lo existente |
| Sobrescribir calificaciones por error | Alto | Vista previa obligatoria, «antes → después», deshacer de toda la importación |
| Datos reales filtrándose a código o commits | Alto | Fixtures ficticias; muestras reales solo por variable de entorno; `.gitignore` ya excluye `*.xlsx` y `*.csv` |

## Preguntas abiertas
Ninguna. Decisiones de la persona recogidas en la spec.
