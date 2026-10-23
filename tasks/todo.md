# Calificación del proyecto final (módulo `proyecto`)

Cada tarea termina con `.venv\Scripts\python.exe -m pytest` en verde. Arranque manual: `.venv\Scripts\python.exe main.py`.

## Fase 1: Núcleo (sin UI)

- [ ] **T1: Tabla, modelos y regla documentada** (S)
  - Descripción: crear `calificacion_proyecto`, las dataclasses `CalificacionProyecto` y `ResultadoProyecto`, `ResumenAlumno.proyecto`, y documentar R17 y el modelo en `CLAUDE.md` antes de seguir.
  - Aceptación:
    - [ ] `conectar()` crea la tabla en una base nueva y en una existente sin perder datos.
    - [ ] Una calificación por `(curso_id, alumno_id)`; borrar curso o alumno la borra en cascada.
    - [ ] `CLAUDE.md` tiene el modelo y R17.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_proyecto.py -q`
  - Archivos: `core/database.py`, `core/models.py`, `CLAUDE.md`, `tests/test_proyecto.py`
  - Dependencias: ninguna

- [ ] **T2: Servicio para un alumno** (M)
  - Descripción: registrar (misma identificación que tareas), reemplazo en dos pasos, deshacer, establecer y eliminar desde el historial, `proyecto` en el resumen del curso y conteo al eliminar un curso. Un solo camino de guardado/deshacer que el equipo reutilizará.
  - Aceptación:
    - [ ] Negativo, `nan` y texto lanzan `ErrorDominio`; 0 y puntos extra se aceptan.
    - [ ] Si ya existe una nota distinta, devuelve `CONFIRMAR_REEMPLAZO` con la anterior y no guarda hasta repetir con `reemplazar=True`.
    - [ ] Deshacer restaura la anterior o elimina la calificación si no había.
    - [ ] Ambiguo y «no existe» se comportan como en tareas; alumno no inscrito se rechaza.
    - [ ] `resumen_curso` trae `proyecto` (0 sin captura); no cambia décimas, exámenes ni tareas.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_proyecto.py tests/test_tareas.py -q`
  - Archivos: `core/services.py`, `core/repository.py`, `core/models.py`, `tests/test_proyecto.py`
  - Dependencias: T1

- [ ] **T3: Servicio para un equipo** (M)
  - Descripción: reconocer «equipo N» / «e N» en la consulta, copiar la nota a todos los miembros, advertencia «N de M miembros ya tienen otra calificación», deshacer de todos.
  - Aceptación:
    - [ ] «equipo 3», «Equipo 3» y «e 3» califican a todo el equipo 3; un número solo sigue siendo cuenta; equipo inexistente o sin miembros se rechaza con mensaje claro.
    - [ ] Sin miembros con otra nota se guarda de inmediato; si alguno tiene otra distinta devuelve `CONFIRMAR_REEMPLAZO` con el conteo `N de M` y no guarda; las notas iguales no cuentan.
    - [ ] `deshacer_proyecto` devuelve a **todos** sus notas previas (o las elimina).
    - [ ] Corregir a un alumno no cambia al resto; sacar o agregar a alguien al equipo no cambia notas.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_proyecto.py tests/test_equipos.py -q`
  - Archivos: `core/services.py`, `core/models.py`, `tests/test_proyecto.py`
  - Dependencias: T2

### Checkpoint 1: Núcleo
- [ ] Suite completa en verde (472 pruebas previas intactas).
- [ ] Una base `.db` existente abre y conserva sus datos.
- [ ] Revisión con la persona antes de seguir a la UI.

## Fase 2: Modo evaluar

- [ ] **T4: Evaluar a un alumno** (M)
  - Descripción: en «Proyecto» con «Formar equipos» apagado se ve el campo de registro («Calificación del proyecto», botón «Registrar proyecto»); mismo flujo que tareas: identificación, reemplazo «Ya tiene X en el proyecto; se cambiará a Y», «Deshacer», clic en fila carga la nota actual.
  - Aceptación:
    - [ ] Apagar «Formar equipos» muestra el registro; encenderlo lo oculta (como ahora) y el clic vuelve a seleccionar.
    - [ ] Guardar a un alumno muestra «<Alumno> · Proyecto: 8»; reemplazo con confirmar/cancelar; deshacer restaura.
    - [ ] «Deshacer» revierte solo lo último (participación, examen, tareas, proyecto o equipos); otra captura reemplaza lo deshacible.
    - [ ] F2 y el cambio de modo conservan lo que ya funcionaba.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_proyecto.py tests/test_ui_equipos.py -q`
  - Archivos: `ui_desktop/vista_curso.py`, `tests/test_ui_proyecto.py`, `tests/test_ui_equipos*.py` (ajustar donde cambie lo visible)
  - Dependencias: T2

- [ ] **T5: Evaluar a un equipo** (M)
  - Descripción: escribir «equipo N» califica a todo el equipo; botón «Usar equipo N» junto al campo cuando el alumno cargado tiene equipo; advertencia «N de M» con Reemplazar/Cancelar; deshacer de todos; franja «Equipo 3 · Proyecto: 9.5 (4 alumnos)».
  - Aceptación:
    - [ ] «equipo 3» + «9.5» + Enter pone 9.5 a los 4 y la franja lo dice; todo posible sin mouse.
    - [ ] «Usar equipo N» solo se habilita si el alumno cargado tiene equipo y pone «equipo N» en el campo.
    - [ ] Si 2 de 4 tenían otra nota: «2 de 4 miembros del equipo 3 ya tienen calificación; se cambiarán a 9.5», no guarda hasta confirmar; «Deshacer» devuelve las 4 notas previas.
    - [ ] Corregir a un solo alumno no mueve al resto del equipo.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_proyecto.py -q`
  - Archivos: `ui_desktop/vista_curso.py`, `tests/test_ui_proyecto.py`
  - Dependencias: T3, T4

### Checkpoint 2: Modo evaluar
- [ ] Suite completa en verde.
- [ ] Flujo manual: evaluar a un alumno y a un equipo, reemplazar con confirmación, deshacer, corregir uno, clic en fila, F2 en cuatro modos.
- [ ] Revisión con la persona antes de seguir.

## Fase 3: Ver y exportar

- [ ] **T6: Columna «Proyecto» y historial** (M)
  - Descripción: columna «Proyecto» entre «Tareas» y los exámenes (0 sin captura, ordenable); en el historial la sección pasa a «Exámenes, tareas y proyecto» con la fila «Proyecto final» (con «· Equipo N» si tiene) que se califica, corrige y quita.
  - Aceptación:
    - [ ] La tabla muestra «Proyecto» y se ordena por ella (descendente primero).
    - [ ] La fila «Proyecto final» del historial se puede calificar, corregir y quitar (con confirmación; vuelve a valer 0) y no altera las demás filas.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_curso.py tests/test_ui_historial.py -q`
  - Archivos: `ui_desktop/vista_curso.py`, `ui_desktop/vista_historial.py`, `tests/test_ui_curso.py`, `tests/test_ui_historial.py`
  - Dependencias: T2

- [ ] **T7: Exportación y eliminar curso** (M)
  - Descripción: columnas «Equipo» (número o vacío) y «Proyecto» (número) en `.xlsx` y `.csv`; el diálogo de eliminar curso cuenta las calificaciones de proyecto.
  - Aceptación:
    - [ ] «Tareas» · «Equipo» · «Proyecto» · exámenes, en ese orden, con y sin exámenes; oyentes excluidos por defecto; curso sin datos exporta Proyecto 0 y Equipo vacío.
    - [ ] Eliminar un curso informa cuántas calificaciones de proyecto se pierden y exige confirmar si solo hay proyectos.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_exportacion.py tests/test_ui_cursos.py -q`
  - Archivos: `exporters/curso.py`, `ui_desktop/dialogos.py`, `ui_desktop/vista_cursos.py`, `tests/test_exportacion.py`, `tests/test_ui_cursos.py`
  - Dependencias: T2

## Fase 4: Cierre

- [ ] **T8: Documentación y versión** (S)
  - Descripción: `CLAUDE.md` (interfaz: modo evaluar, columna, historial, exportación, R17 completa), `README.md`, versión 1.5.0 y ejecutable.
  - Aceptación:
    - [ ] Documentación coherente con R17 y con lo construido.
    - [ ] Suite completa en verde; `scripts\construir_exe.ps1` genera el ejecutable.
  - Verificación: suite completa y `scripts\construir_exe.ps1`
  - Archivos: `CLAUDE.md`, `README.md`, `core/version.py`
  - Dependencias: T5, T6, T7

### Checkpoint 3: Listo
- [ ] Listo para revisión y commit.
