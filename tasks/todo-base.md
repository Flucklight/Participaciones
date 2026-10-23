# Tareas: exportar e importar la base (SPEC-base.md)

Prueba general: `python -m pytest -q`. Cada tarea termina con la suite completa en verde.

## Fase 1: Reemplazar todo (rebanada completa laptop → aquí)

- [x] **T1 · Exportar y validar** (S)
  - Aceptación: `exportar_base(conexion, destino)` crea un `.db` abrible con los mismos conteos y no modifica el origen; destino inexistente o abierto → `ErrorDominio`. `validar_base(ruta)` rechaza archivo no SQLite, sin tablas de la app o con esquema más nuevo; acepta uno de 1.4.0 (migrado en copia temporal).
  - Verifica: `python -m pytest tests/test_exportar_base.py -q`
  - Archivos: `core/database.py`, `core/services.py`, `tests/test_exportar_base.py`
- [x] **T2 · Reemplazar todo con respaldo y deshacer** (M) · depende de T1
  - Aceptación: `resumen_reemplazo(ruta)` da conteos (cursos, alumnos, participaciones) de lo local que se perdería; `reemplazar_base(ruta)` hace respaldo previo, deja la base local idéntica al archivo (mismos conteos, totales y finales por alumno) sin cerrar la conexión; `deshacer_importacion()` restaura el respaldo; un archivo inválido no toca nada.
  - Verifica: `python -m pytest tests/test_reemplazar_base.py -q` (con base en archivo real)
  - Archivos: `core/database.py`, `core/services.py`, `tests/test_reemplazar_base.py`
- [x] **T3 · UI: Exportar e Importar (reemplazar)** (M) · depende de T2
  - Aceptación: Configuración muestra «Exportar base…» (selector de guardado, nombre sugerido `participaciones_export_AAAAMMDD_HHMMSS.db`) e «Importar base…» (selector de archivo → diálogo con modo; «Reemplazar todo» pide confirmación con los conteos; errores con mensaje en español; «Deshacer importación»; la vista se refresca). Sin reglas en la UI.
  - Verifica: `python -m pytest tests/test_ui_base.py -q` + prueba manual: exportar y reemplazar entre dos bases
  - Archivos: `ui_desktop/vista_configuracion.py`, `ui_desktop/dialogos_base.py` (nuevo), `tests/test_ui_base.py`

### Checkpoint A
- [ ] Suite completa en verde
- [ ] Flujo manual: exportar de una base con datos de prueba, reemplazar en otra, comprobar tablas, Final y equipos; deshacer devuelve lo anterior
- [ ] Revisión con la persona antes de seguir

## Fase 2: Fusionar

- [x] **T4 · Plan de fusión: lo que solo agrega** (M) · depende de T1
  - Aceptación: `PlanFusion` por clave natural: cursos (ciclo+materia+grupo, archivados incluidos), alumnos (cuenta), inscripciones, exámenes (curso+nombre_norm) y calificaciones/tareas/proyecto/ponderación que **no existen** localmente. Previsualizar no cambia la base. Conteos de «se agregan» por entidad.
  - Verifica: `python -m pytest tests/test_fusion_plan.py -q`
  - Archivos: `core/importar_base.py` (nuevo), `core/repository.py`, `core/models.py`, `tests/test_fusion_plan.py`
- [x] **T5 · Conflictos de valores y personas dudosas** (M) · depende de T4
  - Aceptación: calificación/tareas/proyecto/ponderación con valor distinto, y tipo de inscripción distinto, salen como conflicto «antes → después» (iguales no cuentan; por omisión se conserva lo local). Oyentes sin cuenta con el mismo `nombre_norm` salen como **dudosos** y no se unen sin confirmar.
  - Verifica: `python -m pytest tests/test_fusion_conflictos.py -q`
  - Archivos: `core/importar_base.py`, `core/repository.py`, `tests/test_fusion_conflictos.py`
- [x] **T6 · Participaciones posiblemente duplicadas y equipos** (M) · depende de T5
  - Aceptación: participaciones nuevas se agregan; las de igual alumno+curso+fecha+décimas+nota se marcan con opción «Mantener ambas» / «Descartar la importada» (omisión: descartar). Equipos con el mismo (curso, número) y miembros distintos → conflicto a elegir (omisión: local); equipos nuevos se agregan respetando «un alumno en un solo equipo».
  - Verifica: `python -m pytest tests/test_fusion_participaciones.py tests/test_fusion_equipos.py -q`
  - Archivos: `core/importar_base.py`, `core/repository.py`, `tests/test_fusion_participaciones.py`, `tests/test_fusion_equipos.py`
- [x] **T7 · Aplicar la fusión** (M) · depende de T6
  - Aceptación: `fusionar_base(ruta, decisiones)` hace respaldo previo y aplica solo lo previsualizado y confirmado, en una transacción; falla a mitad → no queda nada; no borra nada local; reimportar el mismo archivo dos veces no cambia nada la segunda vez; totales recalculados con `total_con_piso`; «Deshacer importación» restaura.
  - Verifica: `python -m pytest tests/test_fusion_aplicar.py -q`
  - Archivos: `core/importar_base.py`, `core/services.py`, `tests/test_fusion_aplicar.py`
- [x] **T8 · UI: vista previa y confirmación de la fusión** (M) · depende de T7, T3
  - Aceptación: el modo «Fusionar» muestra resumen por entidad, tabla «antes → después» con casilla/selector por conflicto, selector por duplicado y por dudoso, y «Aplicar N cambios»; nada se guarda sin confirmar; tras aplicar, franja «Deshacer importación».
  - Verifica: `python -m pytest tests/test_ui_base_fusion.py -q` + prueba manual con dos bases de datos ficticias
  - Archivos: `ui_desktop/dialogos_base.py`, `ui_desktop/vista_configuracion.py`, `tests/test_ui_base_fusion.py`

### Checkpoint B
- [ ] Suite completa en verde
- [ ] Manual: laptop (datos de prueba) → aquí con datos distintos; revisar conflictos, duplicados y equipos; aplicar; deshacer
- [ ] Revisión con la persona antes del cierre

## Fase 3: Cierre

- [ ] **T9 · Documentación y versión 1.6.1** (S) · depende de T8
  - Aceptación: R19 agregada a `CLAUDE.md` (y la sección de Configuración en Interfaz), `README.md` coherente, `core/version.py` = `1.6.1`; «trabajo a futuro» anotado: identificador por evento en `participacion`.
  - Verifica: `python -m pytest -q`; `powershell scripts/construir_exe.ps1` genera el ejecutable
  - Archivos: `CLAUDE.md`, `README.md`, `core/version.py`
