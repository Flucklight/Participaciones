# Visitantes de otro grupo (módulo `visitantes`)

Cada tarea termina con `.venv\Scripts\python.exe -m pytest` en verde. Arranque manual: `.venv\Scripts\python.exe main.py`.
Las pruebas de interfaz tardan (~10 min la suite completa): correr solo el archivo afectado durante el desarrollo y la suite completa **sin otra ventana de pruebas abierta** al cerrar.

## Fase 1: Modelo y alta

- [x] **T1: Modelo, migración y regla documentada** (M)
  - Descripción: documentar R21 y el modelo en `CLAUDE.md` primero. `TipoInscripcion.VISITANTE`; columna `curso_origen_id` en `inscripcion` (FK con cascada) y reconstrucción de la tabla en `_migrar` con respaldo previo; `guardar_inscripcion`/`obtener_tipo_inscripcion` y `ResumenAlumno` conocen el origen.
  - Aceptación:
    - [x] Una base nueva trae la columna y acepta `tipo='visitante'`; una base 1.6.x se migra sin perder cursos, alumnos, inscripciones ni datos, y deja un respaldo.
    - [x] Migrar dos veces no cambia nada; un visitante sin origen es rechazado por el esquema.
    - [x] La validación de R19 (`_estructura`) reconoce el esquema nuevo y sigue rechazando bases más nuevas.
    - [x] `CLAUDE.md` tiene el modelo y R21.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_visitantes.py tests/test_exportar_base.py tests/test_reemplazar_base.py -q`
  - Archivos: `CLAUDE.md`, `core/database.py`, `core/models.py`, `core/repository.py`, `tests/test_visitantes.py`
  - Dependencias: ninguna

- [x] **T2: Alta de visitantes y punto de redirección** (M)
  - Descripción: `candidatos_visitante(curso_id, consulta)` (regulares de otros grupos de la misma materia y ciclo, por cuenta o nombre), `inscribir_visitante(curso_id, alumno_id)` y `_curso_de_datos`.
  - Aceptación:
    - [x] Solo ofrece regulares de otro grupo con el mismo ciclo y materia normalizada (carrera ignorada); rechaza otra materia, otro ciclo, el mismo grupo, un oyente de origen y a quien ya está inscrito en el grupo visitado.
    - [x] Varias coincidencias → se devuelven todas, nunca se adivina; puede ser visitante en varios grupos.
    - [x] Crear la visita no cambia la inscripción regular del origen.
    - [x] `_curso_de_datos` devuelve el origen para un visitante y el mismo curso para los demás.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_visitantes.py -q`
  - Archivos: `core/repository.py`, `core/services.py`, `tests/test_visitantes.py`
  - Dependencias: T1

### Punto de verificación: modelo y alta
- [x] Suite completa en verde antes de seguir.

## Fase 2: Capturas y lectura

- [x] **T3: Capturas redirigidas al origen** (L)
  - Descripción: participaciones, calificaciones de examen (por nombre), tareas y proyecto de un visitante se guardan en el origen; la participación lleva la nota «Grupo <grupo visitado>». Reemplazo y deshacer (R12, R14, R17) siguen funcionando.
  - Aceptación:
    - [x] Participación capturada desde el grupo visitado aparece en el historial y el total del origen con el piso de 0 aplicado (+5, −10, +5 = 5) y nota «Grupo …»; la capturada en el origen no lleva nota automática.
    - [x] Examen: se guarda en el examen homónimo del origen; sin homónimo no se guarda nada y el mensaje nombra el examen y el grupo; nunca se crea un examen.
    - [x] Tareas y proyecto se guardan en el origen; el reemplazo pide confirmar y «Deshacer» restaura.
    - [x] No queda ninguna fila de datos del visitante en el grupo visitado.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_visitantes_capturas.py tests/test_registro.py tests/test_calificaciones.py tests/test_tareas.py tests/test_proyecto.py -q`
  - Archivos: `core/services.py`, `tests/test_visitantes_capturas.py`
  - Dependencias: T2

- [x] **T4: Lectura: resumen, historial y calificación final** (M)
  - Descripción: `resumen_curso` del grupo visitado incluye a los visitantes con los datos del origen (exámenes reindexados por nombre; los que no existen allá no aparecen) y su final con las ponderaciones del origen; `historial`, `historial_examenes`, `desglose_final` y el selector de cursos del historial usan el origen.
  - Aceptación:
    - [x] La final del visitante es idéntica vista desde el grupo visitado y desde el origen, aun con ponderaciones distintas entre los dos grupos.
    - [x] Las columnas de examen que el origen no tiene quedan vacías en la fila del visitante.
    - [x] `tipo` = Visitante y la fila lleva el grupo de origen; ordenar y filtrar siguen funcionando.
    - [x] El historial del visitante desde cualquiera de los dos grupos muestra los mismos eventos.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_visitantes_lectura.py tests/test_calificacion_final.py tests/test_historial.py -q`
  - Archivos: `core/repository.py`, `core/services.py`, `tests/test_visitantes_lectura.py`
  - Dependencias: T2 (puede ir antes o después de T3)

### Punto de verificación: lógica de captura y lectura
- [x] Suite completa en verde.

## Fase 3: Equipos, eliminación y datos

- [x] **T5: Equipos entre los dos grupos** (M)
  - Descripción: un alumno está en un solo equipo entre su origen y los grupos que visita (ambos sentidos); calificar «equipo N» en el grupo visitado guarda la nota del visitante en el origen.
  - Aceptación:
    - [x] Formar/agregar a un equipo en un grupo se rechaza si ya tiene uno en el otro, con el mensaje «quién, en qué equipo y qué grupo»; no se crea ni se mueve nada.
    - [x] Sacarlo de uno lo libera para el otro; deshacer funciona como hoy.
    - [x] «Equipo N» en el grupo visitado copia la nota a cada miembro; la de un visitante queda en el origen; reemplazo y deshacer restauran las previas de todos.
    - [x] Las pruebas existentes de equipos no cambian.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_visitantes_equipos.py tests/test_equipos.py tests/test_equipos_agregar.py tests/test_proyecto.py -q`
  - Archivos: `core/services.py`, `core/repository.py`, `tests/test_visitantes_equipos.py`
  - Dependencias: T3

- [x] **T6: Eliminar visita y eliminar curso de origen** (M)
  - Descripción: R20 acepta visitantes (solo se quita la visita y su equipo, nunca el origen; deshacer la restaura); eliminar el origen borra sus visitas y el diálogo de R1 informa cuántos visitantes se pierden.
  - Aceptación:
    - [x] Eliminar un visitante no cambia ningún dato del origen y el total/final del origen quedan igual; deshacer restaura visita y equipo.
    - [x] Eliminar el curso de origen borra las visitas y los `miembro_equipo` de los visitantes; el equipo del grupo visitado se conserva vacío y su número no se reutiliza.
    - [x] El resumen del diálogo del curso incluye el conteo de visitantes; archivar el origen no cambia nada.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_visitantes_eliminar.py tests/test_eliminar_alumno.py tests/test_cursos.py -q`
  - Archivos: `core/services.py`, `core/repository.py`, `tests/test_visitantes_eliminar.py`
  - Dependencias: T5

- [x] **T7: Exportación** (S)
  - Descripción: «Tipo» = Visitante; excluido por defecto del grupo visitado, incluido con la opción de oyentes; los números son los del origen.
  - Aceptación:
    - [x] Por defecto el visitante no sale; con la opción sale con «Tipo» = Visitante y la final del origen.
    - [x] El origen exporta al alumno como regular, sin cambios.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_exportacion.py tests/test_visitantes_lectura.py -q`
  - Archivos: `exporters/curso.py`, `tests/test_exportacion_visitantes.py`
  - Dependencias: T5

- [x] **T8: Exportar e importar la base (R19)** (M)
  - Descripción: exportar incluye las visitas; fusionar las identifica por clave natural (curso visitado + alumno + curso de origen) y las agrega; si el tipo o el origen difieren es un conflicto «antes → después»; migrar un archivo 1.6.x en memoria.
  - Aceptación:
    - [x] Exportar y reemplazar todo conserva las visitas.
    - [x] Fusionar agrega visitas nuevas, reimportar el mismo archivo no cambia nada y un origen distinto se lista como conflicto (se conserva lo local por omisión).
    - [x] Un archivo 1.6.x se acepta y se migra en memoria sin modificar el archivo.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_exportar_base.py tests/test_reemplazar_base.py tests/test_fusion_plan.py tests/test_fusion_aplicar.py tests/test_fusion_conflictos.py tests/test_visitantes_fusion.py -q`
  - Archivos: `core/importar_base.py`, `core/database.py`, `tests/test_visitantes_fusion.py`
  - Dependencias: T5

### Punto de verificación: lógica completa
- [x] Suite completa en verde antes de tocar la UI.

## Fase 4: Interfaz y cierre

- [x] **T9: Interfaz** (L)
  - Descripción: «Agregar alumno» ofrece «Visitante de otro grupo» con búsqueda de candidatos y elección si hay varios; etiqueta y color de «Visitante» (`tema.py`) en la tabla con el grupo de origen; aviso al capturar («Guardado en el grupo 1509», o «El grupo 1509 no tiene un examen “X”…»); «Eliminar alumno» también para visitantes; diálogo de eliminar curso con el conteo de visitantes; el rechazo de equipo indica grupo y número.
  - Aceptación:
    - [x] Se puede dar de alta un visitante desde la pantalla y se distingue de oyentes y regulares.
    - [x] Capturar desde el grupo visitado avisa dónde se guardó; el valor aparece al abrir el origen.
    - [x] Eliminar visitante (botón y clic derecho) y deshacer funcionan; «Convertir en regular» no aparece para visitantes.
    - [x] Sin hex ni colores nuevos fuera de `tema.py`; el resto de pantallas y modos no cambia.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_visitantes.py tests/test_ui_curso.py tests/test_ui_eliminar_alumno.py -q` y prueba manual con `main.py`.
  - Archivos: `ui_desktop/dialogos_curso.py`, `ui_desktop/vista_curso.py`, `ui_desktop/vista_cursos.py`, `ui_desktop/dialogos.py`, `ui_desktop/tema.py`, `ui_desktop/vista_historial.py`, `tests/test_ui_visitantes.py`
  - Dependencias: T6, T7, T8

- [x] **T10: Documentación y versión 1.7.0** (S)
  - Descripción: `CLAUDE.md` (R21 completa e Interfaz), `README.md` y `core/version.py` a `1.7.0`.
  - Aceptación:
    - [x] `CLAUDE.md` y `README.md` coherentes con lo implementado.
    - [x] Versión `1.7.0`; suite completa en verde (salvo las 2 pruebas de foco que ya fallan en esta máquina).
  - Verificación: `.venv\Scripts\python.exe -m pytest`
  - Archivos: `CLAUDE.md`, `README.md`, `core/version.py`
  - Dependencias: T9
