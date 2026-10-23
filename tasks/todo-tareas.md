# Tareas: calificación de tareas (módulo `tareas`)

Cada tarea termina con `.venv\Scripts\python.exe -m pytest` en verde. Arranque manual: `.venv\Scripts\python.exe main.py`.

## Fase 1: Núcleo (sin UI)

- [x] **T1: Tabla, modelo y regla documentada** (S)
  - Descripción: crear `calificacion_tareas`, la dataclass `CalificacionTareas`, y documentar R14 en `CLAUDE.md` antes de seguir (lo exige el proyecto al cambiar el modelo).
  - Aceptación:
    - [x] `conectar()` crea la tabla en una base nueva y en una existente sin perder datos.
    - [x] Una calificación por `(curso_id, alumno_id)`; borrar el curso la borra en cascada.
    - [x] `CLAUDE.md` tiene el modelo actualizado y la regla R14.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_tareas.py -q`
  - Archivos: `core/database.py`, `core/models.py`, `CLAUDE.md`, `tests/test_tareas.py`
  - Dependencias: ninguna

- [x] **T2: Servicio de tareas** (M)
  - Descripción: registrar (con la misma identificación que participaciones), reemplazo en dos pasos, deshacer, establecer y eliminar desde el historial, `tareas` en el resumen del curso y conteo al eliminar un curso.
  - Aceptación:
    - [x] Negativo, `nan` y texto lanzan `ErrorDominio`; 0 y puntos extra se aceptan.
    - [x] Si ya existe, devuelve `CONFIRMAR_REEMPLAZO` con la nota anterior y no guarda hasta repetir con `reemplazar=True`.
    - [x] Deshacer restaura la anterior o elimina la calificación si no había.
    - [x] Ambiguo y «no existe» se comportan igual que en participaciones; alumno no inscrito se rechaza.
    - [x] `resumen_curso` trae `tareas` (0 sin captura); no cambia `total` ni `prom_examenes`.
    - [x] El conteo de lo que se pierde al eliminar un curso incluye las calificaciones de tareas.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_tareas.py tests/test_registro.py tests/test_cursos.py -q`
  - Archivos: `core/services.py`, `core/repository.py`, `core/models.py`, `tests/test_tareas.py`, `tests/test_cursos.py`
  - Dependencias: T1

### Checkpoint 1: Núcleo
- [x] Suite completa en verde sin modificar pruebas existentes (salvo ampliar `test_cursos.py`).
- [x] Una base `.db` existente abre y conserva sus datos.
- [x] Revisión con la persona antes de seguir a la UI.

## Fase 2: Pantalla Curso

- [x] **T3: Selector de tres modos y captura de tareas** (M)
  - Descripción: el selector pasa a `[Participación | Examen | Tareas]`; modo Tareas con campo «Calificación de tareas», botón «Registrar tareas» y color propio; F2 recorre los tres en ciclo; ambiguo y «no existe» funcionan.
  - Aceptación:
    - [x] Alternar modo cambia campos, texto y color del botón; la lista de exámenes solo aparece en modo Examen.
    - [x] F2 recorre Participación → Examen → Tareas → Participación.
    - [x] Guardar muestra «<Alumno> · Tareas: X», limpia los campos, vuelve el foco al alumno y conserva el modo.
    - [x] Los modos Participación y Examen no cambian (pruebas actuales pasan; solo se ajusta la de F2).
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_curso.py -q` y manual: capturar tres alumnos en modo Tareas.
  - Archivos: `ui_desktop/vista_curso.py`, `ui_desktop/tema.py`, `tests/test_ui_curso.py`
  - Dependencias: T2

- [x] **T4: Reemplazo, deshacer, clic en fila y columna «Tareas»** (M)
  - Descripción: completar la experiencia del modo Tareas y mostrar la columna en la tabla.
  - Aceptación:
    - [x] Con calificación previa: franja «Ya tiene X en tareas; se cambiará a Y» con Reemplazar y Cancelar; no guarda hasta confirmar.
    - [x] «Deshacer» restaura la anterior o elimina la calificación.
    - [x] En modo Tareas, elegir un alumno (clic en fila o sugerencia) trae su calificación actual.
    - [x] Columna «Tareas» entre Décimas y los exámenes (0 sin captura), ordenable.
    - [x] Cambiar de modo con un reemplazo sin confirmar lo descarta sin guardar nada.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_curso.py -q` y manual con teclado.
  - Archivos: `ui_desktop/vista_curso.py`, `tests/test_ui_curso.py`
  - Dependencias: T3

### Checkpoint 2: Registro completo
- [x] Suite completa en verde.
- [x] Flujo manual: capturar, reemplazar con confirmación, deshacer, clic en fila, F2 en ciclo.
- [x] Revisión con la persona antes de exportación e historial.

## Fase 3: Exportación, historial y cierre

- [x] **T5: Exportación con columna «Tareas»** (S)
  - Descripción: `.xlsx` y `.csv` incluyen «Tareas» como número, después de «Décimas» y antes de las columnas de examen.
  - Aceptación:
    - [x] Siempre presente; 0 sin captura; numérica en ambos formatos.
    - [x] Orden correcto con y sin exámenes; la columna de fecha y la de cuenta conservan su formato.
    - [x] Oyentes excluidos por defecto; con «Incluir oyentes» salen con su calificación.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_exportacion.py -q`
  - Archivos: `exporters/curso.py`, `tests/test_exportacion.py`
  - Dependencias: T2

- [x] **T6: Fila «Tareas» en el historial del alumno** (S)
  - Descripción: la sección pasa a «Exámenes y tareas»; su primera fila es «Tareas» (calificación y fecha) y funcionan «Calificar / editar» y «Quitar calificación».
  - Aceptación:
    - [x] Muestra 0 y «—» si no hay captura; editar valida ≥ 0 y fecha; quitar pide confirmación y vuelve a 0.
    - [x] Las filas de examen y sus pruebas actuales siguen funcionando.
    - [x] La sección sigue visible en la ventana de 720 px.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_historial.py -q` y manual.
  - Archivos: `ui_desktop/vista_historial.py`, `ui_desktop/dialogos_historial.py`, `tests/test_ui_historial.py`
  - Dependencias: T2

- [x] **T7: Eliminar curso, documentación y versión** (S)
  - Descripción: el diálogo de eliminar curso informa también las calificaciones de tareas; actualizar `README.md` y `CLAUDE.md` (Interfaz y Exportación); subir `core/version.py`.
  - Aceptación:
    - [x] El diálogo cuenta las calificaciones de tareas y, si las hay, exige escribir ELIMINAR.
    - [x] `README.md` y `CLAUDE.md` coherentes con lo construido; versión incrementada.
  - Verificación: `.venv\Scripts\python.exe -m pytest` completo y manual.
  - Archivos: `ui_desktop/dialogos.py`, `ui_desktop/vista_cursos.py`, `README.md`, `CLAUDE.md`, `core/version.py`, `tests/test_ui_cursos.py`
  - Dependencias: T4, T5, T6

### Checkpoint final
- [x] Todos los criterios de éxito de `SPEC-tareas.md` cumplidos (cubiertos por pruebas automáticas).
- [x] Suite completa en verde; `scripts\construir_exe.ps1` genera el ejecutable.
- [x] Listo para revisión y commit.
