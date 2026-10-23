# Plan de implementación: calificación final por suma ponderada (módulo `calificacion-final`)

Spec aprobada: `SPEC-calificacion-final.md`. Tareas en `tasks/todo.md`.
(Los planes anteriores viven en `tasks/plan-tareas.md`, `tasks/plan-tareas-importacion.md`, `tasks/plan-equipos.md` y `tasks/plan-proyecto.md`.)

## Resumen
Una **calificación final** calculada siempre (nunca guardada) como suma ponderada de participaciones (décimas × 10), promedio de exámenes, tareas y proyecto, con ponderaciones **editables por curso** (por omisión 10 / 0 / 20 / 40; las de exámenes se asigna al crear el primer examen). Se ve como columnas «Final» (0–100) y «Final /10» en la tabla del curso, como tarjeta con desglose en el historial y como columna en la exportación.

## Decisiones de arquitectura
- **Una sola función pura** (`core/calificacion_final.py`), como `promedio.py` y `puntaje.py`: recibe los cuatro componentes y las ponderaciones y devuelve el valor exacto; el redondeo (mitad hacia arriba, con `Decimal`, no el redondeo por banca de `round`) y la equivalencia a 0–10 viven ahí. El servicio la llama; la UI y el exportador solo muestran.
- **El desglose lo arma el servicio** (`desglose_final`): componente, valor en escala 0–100, ponderación y aporte, de modo que el historial no calcula nada y los aportes suman exactamente la final (antes de redondear).
- **`ResumenAlumno.final`** trae el valor **exacto** (la tabla ordena por él); la UI redondea al dibujar. La exportación entrega el entero redondeado.
- **Ponderaciones: tabla propia `ponderacion`**, sin tocar `curso`. «Sin fila» (por omisión 10/0/20/40) se distingue de «fila guardada con exámenes en 0 %»: así se sabe si hay que recordar asignar la de exámenes y no se insiste cuando la persona decidió 0.
- **Todo cálculo con los mismos datos que ya existen:** décimas con piso (`total_con_piso`), `promedio_examenes`, tareas y proyecto; la final no modifica ninguno.
- **Recordatorio de exámenes** como una consulta del servicio (`ponderacion_examenes_pendiente`: el curso tiene exámenes y no hay fila guardada) que la UI usa al crear un examen y al abrir un curso; no bloquea.
- **Colores solo en `tema.py`** (se reutilizan los existentes).

## Grafo de dependencias

```
función pura: fórmula, redondeo, /10, desglose (T1)
        │
        ▼
tabla ponderacion + servicio + final en el resumen + R18 en CLAUDE.md (T2)
        │
   ┌────┼─────────────┬──────────────┐
   ▼    ▼             ▼              ▼
columnas  diálogo y   historial     exportación
«Final»   botón «⚖»   (T6)          (T7)
(T3)      (T4)
            │
            ▼
   asignar exámenes al crear el primero + recordatorio (T5)
   └─────────────┴──────────────┴──────────────┘
                         ▼
          documentación y versión 1.6.0 (T8)
```

Orden: T1 → T2 → T3 → T4 → T5; T6 y T7 dependen solo de T2 (pueden ir en cualquier orden); T8 al final.

## Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|---|---|---|
| Redondeo distinto al esperado (`round` de Python redondea 2.5 → 2) | Alto | `Decimal` con `ROUND_HALF_UP` en la función pura; pruebas con 87.5, 2.5, 0.5, 87.49 y valores con error binario (p. ej. 0.1 + 0.2) |
| Escalas mezcladas (décimas vs 0–100) | Alto | Una sola conversión (× 10) en la función pura, probada; el desglose muestra cada componente ya en escala 0–100 |
| Cursos existentes quedan con final «incompleta» sin avisar | Medio | Distinguir «sin fila» de «guardado en 0» y recordar en la franja al abrir el curso con exámenes |
| Pedir la ponderación al crear un examen interrumpe el flujo o rompe pruebas de exámenes | Medio | El diálogo no bloquea (Cancelar deja el examen creado); en las pruebas de exámenes se cancela o se acepta de forma explícita |
| Insertar columnas rompe posiciones en pruebas de tabla, historial y exportación | Medio | Ajustar solo las expectativas de posición; la suite actual (599) es la regresión |
| La final se «guarda» sin querer (p. ej. en el historial o la exportación) | Alto | Regla de límites: nada la persiste; prueba de que no existe ninguna tabla ni columna con la final |
| Tabla más ancha con dos columnas más | Bajo | Anchos compactos y desplazamiento horizontal que ya existe |

## Preguntas abiertas
Ninguna. La persona respondió las tres abiertas de la spec y la aprobó.
