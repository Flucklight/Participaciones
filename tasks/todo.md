# Calificación final por suma ponderada (módulo `calificacion-final`)

Cada tarea termina con `.venv\Scripts\python.exe -m pytest` en verde. Arranque manual: `.venv\Scripts\python.exe main.py`.

## Fase 1: Núcleo (sin UI)

- [x] **T1: Función pura de la calificación final** (S)
  - Descripción: `core/calificacion_final.py` con `Ponderaciones`, `calificacion_final`, el redondeo a entero (mitad hacia arriba), la equivalencia a 0–10 (un decimal) y el desglose por componente.
  - Aceptación:
    - [x] Participaciones aportan `décimas × 10`; 8 décimas, promedio 70, tareas 90, proyecto 85 con 10/30/20/40 da exactamente 81.
    - [x] Sin tope: 12 décimas aportan 12; suma de ponderaciones mayor o menor de 100 % válida; ponderación 0 anula un componente.
    - [x] Redondeo mitad hacia arriba (87.5 → 88, 2.5 → 3, 0.5 → 1, 87.49 → 87) y robusto ante error binario; la equivalencia /10 da un decimal (81 → 8.1).
    - [x] Sin exámenes (promedio `None`) el componente aporta 0; el desglose suma la final exacta.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_calificacion_final.py -q`
  - Archivos: `core/calificacion_final.py`, `tests/test_calificacion_final.py`
  - Dependencias: ninguna

- [x] **T2: Ponderaciones por curso y final en el resumen** (M)
  - Descripción: tabla `ponderacion`, repositorio, servicio (`ponderaciones_de`, `establecer_ponderaciones` con validación, `restablecer_ponderaciones`, `desglose_final`, `ponderacion_examenes_pendiente`), `ResumenAlumno.final` y R18 más el modelo en `CLAUDE.md` antes de seguir.
  - Aceptación:
    - [x] Sin fila: 10 / 0 / 20 / 40; con fila: lo guardado; una fila con exámenes en 0 % se distingue de «sin fila».
    - [x] Validación: negativo, mayor de 100, `nan`, `inf` y texto lanzan `ErrorDominio`; la suma puede pasar de 100.
    - [x] `resumen_curso` trae `final` exacto y cambia al cambiar ponderaciones o cualquier componente; el piso de 0 de las décimas se respeta.
    - [x] `ponderacion_examenes_pendiente` es verdadero solo si el curso tiene exámenes y no hay fila guardada.
    - [x] Nada se guarda de la final; décimas, exámenes, tareas y proyecto no cambian; borrar el curso borra su fila; una base existente abre y conserva sus datos.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_calificacion_final.py tests/test_cursos.py -q`
  - Archivos: `core/database.py`, `core/models.py`, `core/repository.py`, `core/services.py`, `CLAUDE.md`, `tests/test_calificacion_final.py`
  - Dependencias: T1

### Checkpoint 1: Núcleo
- [ ] Suite completa en verde (599 pruebas previas intactas).
- [ ] Una base `.db` existente abre y conserva sus datos.
- [ ] Revisión con la persona antes de seguir a la UI.

## Fase 2: Pantalla Curso

- [ ] **T3: Columnas «Final» y «Final /10»** (S)
  - Descripción: dos columnas centradas después de las de examen y antes de «Última», visibles en todos los modos, ordenables por el valor exacto.
  - Aceptación:
    - [ ] Muestran el entero (81) y el decimal (8.1); sin captura la final con las ponderaciones por omisión es la que corresponda (p. ej. 0).
    - [ ] Ordenan de mayor a menor primero y no rompen el modo Proyecto (agrupado por equipo).
    - [ ] Los oyentes también las tienen.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_curso.py tests/test_ui_proyecto_vistas.py -q`
  - Archivos: `ui_desktop/vista_curso.py`, `tests/test_ui_curso.py`
  - Dependencias: T2

- [ ] **T4: Diálogo y botón «⚖ Ponderaciones»** (M)
  - Descripción: botón en el encabezado del curso y diálogo con los cuatro porcentajes, suma en vivo («Suma: 110 % · 10 % de puntos extra» / «faltan 10 %»), «Restablecer», validaciones dentro del diálogo; al guardar se recarga la tabla.
  - Aceptación:
    - [ ] Abre con los valores actuales; cambiar un valor actualiza la suma al instante con el mensaje correcto.
    - [ ] Valores inválidos se avisan dentro del diálogo; «Cancelar» no guarda; «Restablecer» vuelve a 10 / 0 / 20 / 40.
    - [ ] Guardar recalcula las columnas «Final» de inmediato y la franja lo confirma.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_ponderaciones.py -q`
  - Archivos: `ui_desktop/dialogos_ponderaciones.py`, `ui_desktop/vista_curso.py`, `tests/test_ui_ponderaciones.py`
  - Dependencias: T2

- [ ] **T5: Asignar la ponderación de exámenes** (M)
  - Descripción: al crear el primer examen con ponderación 0 se abre el diálogo con foco en «Exámenes» y 30 % sugerido; Cancelar no bloquea; recordatorio en la franja al abrir un curso con exámenes y ponderación sin asignar.
  - Aceptación:
    - [ ] Crear un examen en un curso sin ponderación de exámenes abre el diálogo con 30 % sugerido; guardar la asigna y cambia la final.
    - [ ] Cancelar deja el examen creado y la franja recuerda «Los exámenes aún no pesan…».
    - [ ] Tras guardar (aunque sea 0 %) no se vuelve a insistir; un curso con exámenes y sin asignar recibe el recordatorio al abrirse.
    - [ ] Las pruebas de exámenes existentes siguen pasando (cancelando o aceptando el diálogo de forma explícita).
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_ponderaciones.py tests/test_ui_curso.py -q`
  - Archivos: `ui_desktop/vista_curso.py`, `tests/test_ui_ponderaciones.py`, `tests/test_ui_curso.py` (ajustes)
  - Dependencias: T4

### Checkpoint 2: Pantalla Curso
- [ ] Suite completa en verde.
- [ ] Flujo manual: crear un curso, capturar de todo, ver la final y cambiar ponderaciones; crear el primer examen y asignar su ponderación.
- [ ] Revisión con la persona antes de seguir.

## Fase 3: Ver y exportar

- [ ] **T6: Tarjeta y desglose en el historial** (M)
  - Descripción: tarjeta «Calificación final» (entera, con «= 8.1 de 10») y desglose por componente (valor 0–100, ponderación, aporte) que entrega el servicio.
  - Aceptación:
    - [ ] La tarjeta coincide con la tabla del curso; el desglose lista participaciones (décimas × 10), exámenes, tareas y proyecto, y sus aportes suman la final exacta.
    - [ ] Cambia al cambiar de curso en el selector y al cambiar las ponderaciones; no altera las demás secciones.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_ui_historial.py -q`
  - Archivos: `ui_desktop/vista_historial.py`, `tests/test_ui_historial.py`
  - Dependencias: T2

- [ ] **T7: Exportación** (S)
  - Descripción: columna «Calificación final» (entero) después de las de examen y «Promedio exámenes» y antes de «Participaciones», en `.xlsx` y `.csv`; en el `.xlsx`, línea con las ponderaciones usadas.
  - Aceptación:
    - [ ] Numérica entera, en su lugar con y sin exámenes; refleja ponderaciones personalizadas; oyentes excluidos por defecto.
    - [ ] El `.xlsx` indica «Ponderaciones: participaciones 10 % · exámenes 30 % · tareas 20 % · proyecto 40 %»; el `.csv` no la lleva.
  - Verificación: `.venv\Scripts\python.exe -m pytest tests/test_exportacion.py -q`
  - Archivos: `exporters/curso.py`, `tests/test_exportacion.py`
  - Dependencias: T2

## Fase 4: Cierre

- [ ] **T8: Documentación y versión** (S)
  - Descripción: `CLAUDE.md` (R18 completa, interfaz, exportación), `README.md`, versión 1.6.0 y ejecutable.
  - Aceptación:
    - [ ] Documentación coherente con R18 y con lo construido.
    - [ ] Suite completa en verde; `scripts\construir_exe.ps1` genera el ejecutable.
  - Verificación: suite completa y `scripts\construir_exe.ps1`
  - Archivos: `CLAUDE.md`, `README.md`, `core/version.py`
  - Dependencias: T5, T6, T7

### Checkpoint 3: Listo
- [ ] Listo para revisión y commit.
