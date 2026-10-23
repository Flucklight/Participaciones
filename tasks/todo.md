# Equipos para el proyecto final (módulo `equipos`)

Cada tarea termina con `.venv\Scripts\python.exe -m pytest` en verde. Arranque manual: `.venv\Scripts\python.exe main.py`.

## Fase 1: Núcleo (sin UI)

- [x] **T1: Tablas, modelos y regla documentada** (S)
  - Descripción: crear `equipo` y `miembro_equipo`, las dataclasses `Equipo`/`ResultadoEquipo` y `ResumenAlumno.equipo`, y documentar R16 y el modelo en `CLAUDE.md` antes de seguir.
  - Aceptación:
    - [x] `conectar()` crea las tablas en una base nueva y en una existente sin perder datos.
    - [x] La PK impide que un alumno esté en dos equipos del mismo curso; borrar curso o alumno limpia en cascada.
    - [x] `CLAUDE.md` tiene el modelo y R16.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_equipos.py -q`
  - Archivos: `core/database.py`, `core/models.py`, `CLAUDE.md`, `tests/test_equipos.py`
  - Dependencias: ninguna

- [x] **T2: Servicio de equipos** (M)
  - Descripción: `formar_equipo`, `separar_de_equipo`, `deshacer_equipo`, `deshacer_separacion`, `equipos_del_curso`, `equipo_de`; `resumen_curso` trae `equipo`.
  - Aceptación:
    - [x] Forma con 1 o más alumnos; rechaza lista vacía y alumnos no inscritos.
    - [x] Numeración 1, 2, 3 por curso, independiente entre cursos; **no se reutiliza** tras separar a todos.
    - [x] Si alguien ya tiene equipo: no crea ni mueve nada y dice quién y en cuál.
    - [x] Separar uno o varios; separar a quien no tiene equipo no falla; deshacer revierte ambas operaciones.
    - [x] Décimas, exámenes y tareas no cambian.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_equipos.py tests/test_cursos.py -q`
  - Archivos: `core/services.py`, `core/repository.py`, `core/models.py`, `tests/test_equipos.py`
  - Dependencias: T1

### Checkpoint 1: Núcleo
- [ ] Suite completa en verde (371 pruebas previas intactas).
- [ ] Una base `.db` existente abre y conserva sus datos.
- [ ] Revisión con la persona antes de seguir a la UI.

## Fase 2: Sección «Proyecto»

- [x] **T3: Modo «Proyecto» y tabla agrupada por equipo** (L: el riesgo está en la tabla)
  - Descripción: cuarto modo (F2 recorre cuatro), color ciruela, columna «Equipo» solo en este modo, y la tabla agrupada con filas de encabezado coloreadas (variante C). Sin campo de registro todavía.
  - Aceptación:
    - [x] El selector tiene cuatro modos y F2 los recorre en ciclo; los otros tres modos no cambian.
    - [x] En «Proyecto» la tabla muestra «Equipo», agrupa por número con encabezados «Equipo N · M alumnos», tonos alternados y los sin equipo al final.
    - [x] Los encabezados no reaccionan a clic, doble clic ni selección; el filtro y «Mostrar oyentes» los ocultan si el equipo queda vacío.
    - [x] Ordenar por otra columna ordena dentro de cada equipo.
    - [x] Colores solo desde `tema.py`; se ve bien en claro y oscuro.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_equipos.py tests/test_ui_curso.py -q` y captura en claro y oscuro
  - Archivos: `ui_desktop/tema.py`, `ui_desktop/tabla.py`, `ui_desktop/vista_curso.py`, `tests/test_ui_equipos.py`, `tests/test_ui_curso.py`
  - Dependencias: T2

- [x] **T4: Formar equipos** (M)
  - Descripción: botón «Formar equipos» (activar/desactivar), selección múltiple con Ctrl/Mayús sin cargar al alumno, barra «N seleccionados», «Crear equipo con N alumnos», rechazo si alguien ya tiene equipo, franja y «Deshacer».
  - Aceptación:
    - [x] Con el modo activo se pueden seleccionar varios alumnos; el clic ya no carga al alumno.
    - [x] «Crear» asigna el siguiente número, resalta a los miembros y la tabla se reagrupa; deshabilitado sin selección; 1 alumno forma equipo de 1.
    - [x] Incluir a alguien con equipo rechaza, dice quién y en cuál, y no cambia nada.
    - [x] «Deshacer» elimina el equipo recién creado; desactivar el modo o cambiar de modo limpia la selección.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_equipos.py -q`
  - Archivos: `ui_desktop/vista_curso.py`, `tests/test_ui_equipos.py`
  - Dependencias: T3

- [x] **T5: Separar con clic derecho** (S)
  - Descripción: menú contextual «Separar del equipo N» sobre filas con equipo (una o varias seleccionadas), solo con «Formar equipos» activo, con deshacer.
  - Aceptación:
    - [x] Clic derecho en un miembro ofrece «Separar del equipo N» y lo deja sin equipo; con varias seleccionadas separa a todas.
    - [x] Sin equipo o en un encabezado no hay menú; si se separa a todos el equipo desaparece y su número no se reutiliza.
    - [x] «Deshacer» devuelve a los miembros a su equipo.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_equipos.py -q`
  - Archivos: `ui_desktop/vista_curso.py`, `tests/test_ui_equipos.py`
  - Dependencias: T4

- [x] **T5.1: Ajustes tras la revisión de la persona** (M)
  - Descripción: el clic simple selecciona al formar (sin Ctrl); «Crear equipo» debajo de «Formar equipos» a la izquierda, con «Sacar de equipo»; clic derecho con «Agregar a ▸» y la lista de equipos formados.
  - Aceptación:
    - [x] Formando, un clic suma al alumno a la selección y otro lo quita; Mayús/Ctrl y el orden por encabezado siguen igual; el doble clic no abre historial.
    - [x] «Crear equipo con N» va justo debajo de «Formar equipos» y «Sacar de equipo (N)» a su derecha, con la misma lógica que «Separar».
    - [x] «Agregar a ▸» lista los equipos con miembros; solo se ofrece a quien no tiene equipo; se puede deshacer; no revive equipos vacíos.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_equipos_agregar.py tests/test_ui_equipos_ajustes.py -q`
  - Archivos: `core/services.py`, `core/models.py`, `ui_desktop/vista_curso.py`, `SPEC-equipos.md`, `CLAUDE.md`, pruebas
  - Dependencias: T5

### Checkpoint 2: Sección «Proyecto»
- [x] Suite completa en verde (444 pasadas, 3 omitidas).
- [ ] Flujo manual: formar equipos, ver los colores en claro y oscuro, separar, deshacer, F2 en cuatro modos.

## Fase 3: Cierre

- [ ] **T6: Documentación y versión** (S)
  - Descripción: `CLAUDE.md` (interfaz, paleta, F2 de cuatro modos), `README.md`, versión 1.4.0 y ejecutable.
  - Aceptación:
    - [ ] Documentación coherente con R16 y con lo construido.
    - [ ] Suite completa en verde; `scripts\construir_exe.ps1` genera el ejecutable.
  - Verificación: suite completa y `scripts\construir_exe.ps1`
  - Archivos: `CLAUDE.md`, `README.md`, `core/version.py`
  - Dependencias: T5

### Checkpoint 3: Listo
- [ ] Listo para revisión y commit.
