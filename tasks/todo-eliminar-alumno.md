# Eliminar alumno oyente (módulo `eliminar-alumno`)

Cada tarea termina con `.venv\Scripts\python.exe -m pytest` en verde. Arranque manual: `.venv\Scripts\python.exe main.py`.

## Fase 1: Núcleo (sin UI)

- [x] **T1: Repositorio: contar, borrar por curso y restaurar** (M)
  - Descripción: en `core/repository.py`, `contar_datos_alumno_en_curso`, `eliminar_alumno_de_curso` (borra inscripción, participaciones, calificaciones de exámenes de ese curso, tareas, proyecto y membresía; borra el `alumno` si no queda inscrito en otro curso) y `restaurar_alumno_en_curso`. Modelo `InstantaneaAlumno` en `core/models.py`.
  - Aceptación:
    - [x] Los conteos coinciden con lo que existe.
    - [x] Borrar no toca otros cursos ni otros alumnos.
    - [x] Oyente en un solo curso: desaparece también el `alumno`; en dos cursos: se conserva.
    - [x] Restaurar reinserta todo en una transacción y falla sin escribir si la cuenta está ocupada.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_eliminar_alumno.py -q`
  - Archivos: `core/repository.py`, `core/models.py`, `tests/test_eliminar_alumno.py`
  - Dependencias: ninguna

- [x] **T2: Servicio y regla R20** (M)
  - Descripción: `resumen_eliminacion`, `eliminar_alumno_oyente` (devuelve la instantánea), `deshacer_eliminacion`; documentar R20 y el efecto en el modelo en `CLAUDE.md` antes de seguir.
  - Aceptación:
    - [x] Regular o no inscrito → `ErrorDominio`, nada cambia.
    - [x] Oyente con participaciones, examen, tareas, proyecto y equipo: todo desaparece de ese curso.
    - [x] El equipo sobrevive vacío y su número no se reutiliza al formar otro.
    - [x] Total y final de los demás alumnos no cambian.
    - [x] Deshacer devuelve todo y el total con `total_con_piso` es igual al de antes; con cuenta ocupada o equipo inexistente falla sin restaurar nada.
    - [x] Exportar y fusionar (R19) siguen funcionando tras eliminar y tras deshacer.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_eliminar_alumno.py tests/test_cursos.py tests/test_equipos.py -q`
  - Archivos: `core/services.py`, `CLAUDE.md`, `tests/test_eliminar_alumno.py`
  - Dependencias: T1

### Punto de verificación: núcleo completo
- [x] Suite completa en verde antes de tocar la UI.

## Fase 2: Interfaz

- [x] **T3: Diálogo de confirmación** (S)
  - Descripción: en `ui_desktop/dialogos_curso.py`, diálogo «Eliminar a <nombre>» con los conteos del servicio, botón «Eliminar» (rojo de `tema`) y «Cancelar»; devuelve verdadero/falso.
  - Aceptación:
    - [x] Muestra participaciones, calificaciones de examen, tareas, proyecto y si quedaba en un equipo.
    - [x] Cancelar no cambia nada; el foco inicial está en «Cancelar».
    - [x] Sin hex ni colores nuevos fuera de `tema.py`.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_curso.py -q`
  - Archivos: `ui_desktop/dialogos_curso.py`, `tests/test_ui_curso.py`
  - Dependencias: T2

- [x] **T4: Botón, clic derecho y «Deshacer»** (M)
  - Descripción: en `ui_desktop/vista_curso.py`, botón «Eliminar alumno» junto a «Agregar alumno» y opción en el clic derecho de la fila (nuevo `_menu_alumno`; `_menu_equipos` queda igual y la acción no aparece con «Formar equipos» activo); `_ultima_eliminacion` con «Deshacer» en la franja y limpieza al capturar otra cosa.
  - Aceptación:
    - [x] Sin selección, con un regular, con un encabezado de equipo o con más de una fila: botón/opción desactivados (sin eliminación en lote).
    - [x] Eliminar refresca la tabla y la franja avisa «<nombre> eliminado del curso» con «Deshacer».
    - [x] «Deshacer» restaura al alumno y resalta su fila; tras otra captura ya no deshace.
    - [x] El menú de equipos y el resto de modos no cambian.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_curso.py -q` y prueba manual con `main.py`.
  - Archivos: `ui_desktop/vista_curso.py`, `tests/test_ui_curso.py`
  - Dependencias: T3

### Punto de verificación: funcionalidad completa
- [x] Prueba manual: crear oyente, darle participación, examen, tareas, proyecto y equipo; eliminar desde el botón y desde el clic derecho; deshacer; confirmar totales.

## Fase 3: Cierre

- [x] **T5: Documentación y versión** (S)
  - Descripción: `CLAUDE.md` (R20 e Interfaz), `README.md` y `core/version.py` a `1.6.2`.
  - Aceptación:
    - [x] `CLAUDE.md` y `README.md` coherentes con lo implementado.
    - [x] Versión `1.6.2`.
    - [x] Suite completa en verde.
  - Verificación: `.venv\Scripts\python.exe -m pytest`
  - Archivos: `CLAUDE.md`, `README.md`, `core/version.py`
  - Dependencias: T4
