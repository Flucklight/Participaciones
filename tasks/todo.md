# Tareas: calificaciones de exámenes

Cada tarea termina con `python -m pytest` en verde. Arranque manual: `python main.py`.

## Fase 1: Núcleo (sin UI)

- [x] **T1: Tablas, modelos y reglas documentadas** (S)
  - Descripción: crear `examen` y `calificacion`, dataclasses `Examen` y `Calificacion`, y documentar las reglas nuevas antes de seguir (lo exige `CLAUDE.md`).
  - Aceptación:
    - [x] `conectar()` crea las tablas en una base nueva y en una existente sin perder datos.
    - [x] `examen` único por `(curso_id, nombre_norm)`; borrar un curso borra sus exámenes y calificaciones en cascada.
    - [x] `CLAUDE.md` tiene el modelo de datos actualizado y las reglas R12 (exámenes y calificaciones) y R13 (promedio).
  - Verificación: `python -m pytest tests/test_examenes.py -q` (esquema, cascada, base antigua).
  - Archivos: `core/database.py`, `core/models.py`, `CLAUDE.md`, `tests/test_examenes.py`
  - Dependencias: ninguna

- [x] **T2: `promedio_examenes`** (XS)
  - Descripción: función pura, única fuente del promedio.
  - Aceptación:
    - [x] Media simple de los puntos; lista vacía devuelve `None`.
    - [x] Un examen sin capturar (0.0) cuenta; puntos extra (más de 100) se aceptan.
  - Verificación: `python -m pytest tests/test_promedio.py -q`
  - Archivos: `core/promedio.py`, `tests/test_promedio.py`
  - Dependencias: ninguna (paralelizable con T1)

- [x] **T3: Exámenes: repositorio y servicio (CRUD)** (M)
  - Descripción: crear, renombrar, listar y eliminar exámenes de un curso; contar las calificaciones que se perderían al eliminar.
  - Aceptación:
    - [x] Nombre vacío o duplicado (normalizado) en el curso lanza `ErrorDominio`.
    - [x] `resumen_eliminacion_examen` devuelve cuántas calificaciones se pierden; eliminar las borra.
    - [x] Todo el SQL está en `core/repository.py`.
  - Verificación: `python -m pytest tests/test_examenes.py -q`
  - Archivos: `core/repository.py`, `core/services.py`, `tests/test_examenes.py`
  - Dependencias: T1

- [x] **T4: Registrar calificación, reemplazo, deshacer y promedio en el resumen** (M)
  - Descripción: `registrar_calificacion` con el mismo flujo de identificación que las participaciones; reemplazo en dos pasos; `deshacer_calificacion`; `ResumenAlumno` con `prom_examenes`.
  - Aceptación:
    - [x] Calificación negativa lanza `ErrorDominio`; sin tope superior.
    - [x] Si ya existe, devuelve `CONFIRMAR_REEMPLAZO` con la nota anterior y no guarda hasta repetir con `reemplazar=True`.
    - [x] Deshacer restaura la nota anterior o elimina la calificación si no había.
    - [x] Ambiguo y «no existe» se comportan igual que en participaciones.
    - [x] `resumen_curso` trae `prom_examenes` (examen sin capturar = 0; curso sin exámenes: `None`).
    - [x] Registrar calificaciones no cambia `total_alumno`.
  - Verificación: `python -m pytest tests/test_calificaciones.py tests/test_registro.py -q`
  - Archivos: `core/services.py`, `core/repository.py`, `core/models.py`, `tests/test_calificaciones.py`
  - Dependencias: T2, T3

### Checkpoint 1: Núcleo
- [x] `python -m pytest` completo en verde (suite actual sin modificar).
- [x] Una base `.db` existente abre y conserva sus datos.
- [ ] Revisión con la persona antes de seguir a la UI.

## Fase 2: Registro rápido en la pantalla Curso

- [x] **T5: Selector segmentado y captura de examen** (M)
  - Descripción: selector `[Participación | Examen]`; en modo Examen aparece la lista de exámenes con «+ Nuevo» y el campo pasa a «Calificación»; guardar registra y muestra la franja de confirmación.
  - Aceptación:
    - [x] Alternar modo cambia campos, texto del botón («Registrar examen») y color.
    - [x] «+ Nuevo» abre un diálogo (nombre) y deja el examen seleccionado.
    - [x] Tras guardar, el foco vuelve al alumno y se conservan modo y examen.
    - [x] Ambiguo y «no existe» funcionan en modo Examen; el modo Participación no cambia.
    - [x] Un curso sin exámenes en modo Examen muestra un aviso claro.
  - Verificación: `python -m pytest tests/test_ui_curso.py -q` y manual: crear un examen y capturar tres alumnos.
  - Archivos: `ui_desktop/vista_curso.py`, `ui_desktop/dialogos_curso.py`, `tests/test_ui_curso.py`
  - Dependencias: T4

- [x] **T6: Deshacer, clic en fila, F2 y columnas de examen en la tabla** (M)
  - Descripción: completar la experiencia del modo Examen.
  - Aceptación:
    - [x] Si ya hay calificación: franja «Ya tiene X en <examen>; se cambiará a Y» con Reemplazar y Cancelar antes de guardar. (Adelantado en T5.)
    - [x] «Deshacer» restaura la nota anterior en modo Examen.
    - [x] Clic en fila en modo Examen carga al alumno y su calificación actual, con foco en la calificación; en modo Participación sigue como antes.
    - [x] F2 alterna el modo.
    - [x] La tabla tiene una columna «Examen - <nombre>» por examen (0 si no hay captura), ordenable; sin columna de promedio. (Cambio pedido tras probar T6.)
  - Verificación: `python -m pytest tests/test_ui_curso.py -q` y manual con teclado.
  - Archivos: `ui_desktop/vista_curso.py`, `ui_desktop/tabla.py`, `tests/test_ui_curso.py`
  - Dependencias: T5

### Checkpoint 2: Registro completo
- [x] Suite completa en verde.
- [x] Flujo manual: crear examen, capturar una tanda, reemplazar con confirmación, deshacer, clic en fila (confirmado por la persona).
- [ ] Revisión con la persona antes de exportación e historial.

## Fase 3: Exportación, historial y cierre

- [x] **T7: Exportación con columnas de examen y promedio** (M)
  - Descripción: `.xlsx` y `.csv` incluyen una columna por examen y el «Promedio exámenes» como números.
  - Aceptación:
    - [x] Columnas de examen en orden de creación; sin capturar = 0; todo numérico.
    - [x] El promedio exportado coincide con `prom_examenes` del resumen; un curso sin exámenes no agrega columnas.
    - [x] Oyentes excluidos por defecto; CSV con BOM; los errores de archivo abierto siguen siendo `ErrorDominio`.
  - Verificación: `python -m pytest tests/test_exportacion.py -q`
  - Archivos: `exporters/curso.py`, `core/services.py`, `tests/test_exportacion.py`
  - Dependencias: T4

- [x] **T8: Sección «Exámenes» en el historial del alumno** (M)
  - Descripción: lista las calificaciones del alumno en el curso seleccionado; editar y eliminar con confirmación.
  - Aceptación:
    - [x] Muestra cada examen con su calificación (0 si no está capturado).
    - [x] Editar valida que sea mayor o igual a 0; eliminar pide confirmación; ambos actualizan la vista.
    - [x] Las participaciones y las tarjetas de resumen no cambian.
  - Verificación: `python -m pytest tests/test_ui_historial.py -q` y manual.
  - Archivos: `core/services.py`, `ui_desktop/vista_historial.py`, `ui_desktop/dialogos_historial.py`, `tests/test_ui_historial.py`
  - Dependencias: T4

- [x] **T9: Gestión de exámenes, documentación y versión** (S)
  - Descripción: menú para renombrar y eliminar exámenes del curso (confirmación con el conteo de calificaciones), actualizar `README.md` y subir `core/version.py`.
  - Aceptación:
    - [x] Renombrar sin repetir nombre; eliminar muestra cuántas calificaciones se pierden y exige confirmación.
    - [x] `README.md` y `CLAUDE.md` (Interfaz y Exportación) coherentes con lo construido.
    - [x] Versión incrementada.
  - Verificación: `python -m pytest` completo y manual.
  - Archivos: `ui_desktop/vista_curso.py`, `ui_desktop/dialogos_curso.py`, `README.md`, `CLAUDE.md`, `core/version.py`
  - Dependencias: T6, T7, T8

### Checkpoint final
- [x] Todos los criterios de éxito de `SPEC.md` cumplidos (cubiertos por pruebas automáticas).
- [x] `python -m pytest` en verde; `scripts/construir_exe.ps1` genera el ejecutable.
- [ ] Listo para revisión y commit.
