# Plan: Exportar e importar la base entre máquinas

Spec: `SPEC-base.md`. Tareas: `tasks/todo-base.md`. (Archivos con sufijo, igual que los módulos anteriores: `plan.md`/`todo.md` pertenecen a otro trabajo y no se tocan.)

## Resumen
Configuración gana «Exportar base…» e «Importar base…». Exportar copia el `.db`. Importar tiene dos modos: **Reemplazar todo** y **Fusionar** (vista previa, conflictos a elegir, confirmación, deshacer).

## Decisiones de arquitectura
- **Un solo mecanismo de copia.** Exportar y respaldar usan `Connection.backup`. Reemplazar también: `origen.backup(conexion_viva)` sustituye el contenido sin cerrar la conexión de la app, así que la UI solo refresca la vista.
- **Fusionar con la base importada abierta como segunda conexión de solo lectura** (copia temporal ya migrada) y comparación por clave natural en Python (ver tabla del SPEC). Nunca por `id`. Los `id` de la base local se asignan al insertar.
- **El SQL va en `core/repository.py`/`core/database.py`** (regla 2). `core/importar_base.py` solo arma el plan y lo aplica llamando al repositorio.
- **Plan de fusión = datos inmutables** (`PlanFusion`: agregados, conflictos con `opcion` elegible, dudosos) que la UI muestra y devuelve con las decisiones. `aplicar(plan)` no recalcula nada: lo que se previsualizó es lo que se aplica.
- **Deshacer = restaurar el respaldo previo** a la importación (se conserva la ruta en el servicio hasta la siguiente importación o hasta cerrar).
- **Totales nunca se importan:** solo eventos; el total sale de `total_con_piso`.
- **Fusionar nunca borra** y corre en una transacción (`BEGIN`/`ROLLBACK` ante cualquier error).

## Orden y dependencias
```
T1 exportar/validar ─┬─ T2 reemplazar ─ T3 UI exportar+reemplazar ──[Checkpoint A]
                     └─ T4 plan base de fusión ─ T5 conflictos ─ T6 participaciones y equipos
                                                         └──────── T7 aplicar fusión ─ T8 UI fusionar ──[Checkpoint B]
                                                                                              T9 cierre
```
Primero la rebanada vertical más simple y útil (T1–T3: ya permite pasar todo de la laptop a aquí). La fusión es lo riesgoso y va después, por partes.

## Riesgos
| Riesgo | Impacto | Mitigación |
|---|---|---|
| Reemplazar con `backup` sobre la conexión viva falla con transacciones abiertas | Alto | `commit()` antes; prueba con conexión en archivo real, no solo `:memory:` |
| Archivo de versión anterior sin columnas nuevas | Medio | Migrar siempre una **copia temporal**, nunca el archivo del usuario |
| Participaciones duplicadas ambiguas | Medio | Las decide la persona (mantener ambas / descartar); omisión = descartar; trabajo a futuro: id por evento |
| Fusión a medias por error | Alto | Una transacción + respaldo previo + prueba de falla a mitad |
| Datos reales en tests | Alto | Solo datos ficticios (`100000001`); bases generadas con `tmp_path` |

## Pendiente de confirmar al implementar
- Punto de entrada: `main.py` (existe en la raíz).
