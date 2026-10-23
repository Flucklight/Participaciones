# Importar tareas: calificaciones desde archivo (módulo `tareas-importacion`)

Cada tarea termina con `.venv\Scripts\python.exe -m pytest` en verde. Arranque manual: `.venv\Scripts\python.exe main.py`.

## Fase 1: Lector y vista previa (sin UI)

- [x] **T1: Lector de xlsx/csv y modelos** (M)
  - Descripción: `importers/calificaciones_plataforma.py` lee ambas disposiciones y devuelve un `ArchivoCalificaciones` (columnas numéricas con rótulo, filas de alumnos, grupo/ciclo si existen); agrega `conftest` con generadores ficticios.
  - Aceptación:
    - [x] Localiza alumnos por forma, sin posiciones fijas; ignora «Media de la clase», `Fecha`, `Puntos` y filas vacías.
    - [x] Lista las columnas numéricas con su rótulo (incluida la sin encabezado) y sugiere la de más a la derecha.
    - [x] `.csv` con coma o punto y coma, con y sin BOM; lee grupo y ciclo del xlsx.
    - [x] Archivo ajeno, inexistente o sin alumnos → `ErrorImportacion` claro; fórmula sin valor → «sin dato».
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_importar_tareas.py -q`
  - Archivos: `importers/calificaciones_plataforma.py`, `core/models.py`, `tests/conftest.py`, `tests/test_importar_tareas.py`
  - Dependencias: ninguna

- [x] **T2: Servicio de vista previa y coincidencia por nombre** (M)
  - Descripción: documentar R15 en `CLAUDE.md`; `previsualizar_importacion_tareas(curso_id, archivo, columna)` clasifica filas (aplicar / dudosa / omitida) y cuenta cambian, quedan igual y no tocados. No escribe.
  - Aceptación:
    - [x] Exacta única aplica; por palabras única es dudosa; varias o ninguna se omite; nombre repetido en el archivo se omite.
    - [x] Cuenta en el archivo, si existe, tiene prioridad; nunca se crean alumnos.
    - [x] Valor negativo o no numérico se omite con motivo; celda vacía no cambia lo existente.
    - [x] Verificación de grupo si el archivo lo trae.
    - [x] No guarda nada.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_importar_tareas.py -q`
  - Archivos: `core/services.py`, `core/repository.py`, `core/models.py`, `CLAUDE.md`, `tests/test_importar_tareas.py`
  - Dependencias: T1

### Checkpoint 1: Lector y vista previa
- [x] Suite completa en verde (343 pasadas, 3 omitidas); con `PLATAFORMA_REAL` y `PLATAFORMA_REAL_CSV` las muestras reales también.
- [ ] Revisión con la persona antes de seguir a guardar y a la UI.

## Fase 2: Guardar y deshacer

- [x] **T3: Importar y deshacer** (M)
  - Descripción: `importar_tareas(..., confirmadas)` aplica en una transacción lo claro más las dudosas confirmadas; `deshacer_importacion_tareas` restaura o elimina.
  - Aceptación:
    - [x] Reemplaza sin pedir confirmación por alumno; fecha de captura = hoy.
    - [x] Una dudosa no confirmada no se aplica.
    - [x] Alumnos fuera del archivo intactos; décimas y exámenes sin cambios.
    - [x] Deshacer deja los valores exactamente como estaban; un error a medias no deja nada guardado.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_importar_tareas.py tests/test_tareas.py -q`
  - Archivos: `core/services.py`, `core/repository.py`, `tests/test_importar_tareas.py`
  - Dependencias: T2

## Fase 3: Pantalla Curso

- [x] **T4: Diálogo con vista previa y botón** (M)
  - Descripción: botón «⬆ Importar tareas» junto a «Exportar»; `DialogoImportarTareas` elige archivo, columna, muestra el resumen, la tabla «antes → después» y casillas de dudosas; aplicar.
  - Aceptación:
    - [x] Cambiar la columna actualiza la vista previa; cancelar no guarda nada.
    - [x] «Aplicar N cambios» guarda y recarga la tabla del curso.
    - [x] Archivo inválido muestra el mensaje sin cerrar la app.
    - [x] Colores solo desde `tema.py`.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_curso.py -q`
  - Archivos: `ui_desktop/dialogos_tareas.py`, `ui_desktop/vista_curso.py`, `tests/test_ui_curso.py`
  - Dependencias: T3

- [ ] **T5: Deshacer importación, docs y versión** (S)
  - Descripción: franja «✓ Tareas importadas: N actualizadas, M omitidas» con «Deshacer importación»; `CLAUDE.md` (pantalla), `README.md`, versión 1.3.0.
  - Aceptación:
    - [ ] Deshacer restaura la tabla; otra captura o salir de la pantalla la deshabilita.
    - [ ] Documentación coherente con R15.
  - Verificación: suite completa; `scripts\construir_exe.ps1`.
  - Archivos: `ui_desktop/vista_curso.py`, `CLAUDE.md`, `README.md`, `core/version.py`, `tests/test_ui_curso.py`
  - Dependencias: T4

### Checkpoint 2: Completo
- [ ] Suite completa en verde; ejecutable generado.
- [ ] Flujo manual con las muestras reales: elegir columna, revisar dudosas, aplicar, deshacer.
- [ ] Listo para revisión y commit.
