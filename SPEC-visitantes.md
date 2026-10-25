# Spec: Visitantes de otro grupo (módulo `visitantes`, R21 propuesta)

Estado: **spec aprobada** (no hay código ni cambios a `CLAUDE.md` todavía). Plan en `tasks/plan-visitantes.md`, tareas en `tasks/todo-visitantes.md`.
(`SPEC.md` en la raíz es un borrador antiguo de exámenes; este spec sigue la convención `SPEC-<módulo>.md`.)

## Objetivo
Un alumno inscrito como **regular** en un grupo de una materia a veces asiste a **otro grupo de la misma materia y ciclo**. Hoy habría que meterlo como oyente y sus calificaciones quedarían partidas en dos cursos. Se agrega el tipo de inscripción **«Visitante»**:

- En su **grupo de origen** (donde es regular) sigue igual: ahí viven **todas** sus participaciones, exámenes, tareas, proyecto y calificación final.
- En el **grupo que visita** aparece como **Visitante**, con una marca distinta a «oyente». Se le puede capturar todo desde ahí y **lo capturado se guarda en el grupo de origen**; no existe un segundo juego de calificaciones.

Usuario: la persona que lleva las participaciones de varios grupos de la misma materia.
Éxito: calificar al alumno desde cualquiera de los dos grupos da el mismo resultado final, sin duplicar ni perder datos.

## Decisiones ya tomadas
1. Nombre: **«Visitante»**.
2. En el grupo visitado se **ve y se captura**; todo se guarda en el origen.
3. **Puede estar en un equipo del grupo que visita**; la nota del proyecto se guarda en el origen.
4. En la exportación del grupo visitado se **excluye por defecto**, como los oyentes (se puede incluir; la columna «Tipo» dice «Visitante»).
5. **Examen sin homónimo en el origen:** se rechaza con aviso; la app no crea exámenes sola.
6. **Misma materia:** por nombre normalizado, mismo ciclo, sin contar la carrera.
7. **Un solo equipo entre los dos grupos:** si el visitante ya está en un equipo del grupo que visita, **no puede formar parte de un equipo en el origen** (y a la inversa); hay que sacarlo primero (R16: nunca se mueve a nadie solo).
8. **Eliminar el curso de origen borra también sus visitas**, avisando con conteo en el diálogo (el equipo del grupo visitado se conserva aunque quede vacío).
9. **La exclusión de equipos aplica en ambos sentidos** (confirmado).
10. **Nota automática de procedencia:** toda participación capturada a un visitante desde el grupo que visita lleva en la nota «Grupo 1510» (el grupo desde donde se capturó), para saber de dónde vino.

## Supuestos (corrige lo que no sea así)
1. **Origen:** un curso con el **mismo ciclo y la misma materia** (comparados normalizados, R3; la carrera no cuenta) y **distinto grupo**, donde el alumno es `regular`. Un alumno solo puede ser visitante en un grupo donde **no** esté ya inscrito, y solo de un origen donde sea regular. Puede ser visitante en varios grupos.
2. **Alta:** desde «Agregar alumno» del grupo que visita, una opción nueva «Visitante de otro grupo»: se busca (cuenta o nombre) entre los regulares de los demás grupos de la misma materia y ciclo. Si hay varias coincidencias se pide elegir; nunca se adivina (R6).
3. **El vínculo se guarda explícito** (`curso_origen_id` de la visita), no se deduce: así no depende de que el origen siga siendo el único grupo donde el alumno es regular.
4. **Participaciones:** se registran como eventos en el curso de origen (R4); el total sale de `total_con_piso` (R5) sobre todos sus eventos, vengan de donde vengan. Sin cambios en esa función.
5. **Exámenes:** los exámenes son por curso y los dos grupos pueden tener distintos. Regla propuesta: al capturar un examen de **B** a un visitante, se busca en el origen un examen con el **mismo nombre normalizado**; si existe, se guarda ahí; si no, **no se guarda nada** y se avisa («El grupo 1509 no tiene un examen “Parcial 1”: créalo allá o captura desde ese grupo»). **Nunca se crean exámenes ni se mezclan solos.** En el grupo visitado, las columnas de examen que el origen no tiene se muestran «—».
6. **Calificación final del visitante en el grupo que visita:** es la **del origen** (se calcula con las ponderaciones y los exámenes del origen, R18), mostrada tal cual; el grupo visitado no la recalcula con sus propias ponderaciones.
7. **Equipos (R16/R17):** la **membresía** del visitante vive en el grupo que visita (el equipo es de ese grupo); la **nota** del proyecto de «equipo N» se guarda, para el visitante, en el **origen** (`calificacion_proyecto` del origen). Se conserva «no se guarda vínculo nota–equipo». **Regla de exclusión (decidida):** un alumno está en un solo equipo entre su grupo de origen y los grupos que visita; formar o agregar a un equipo en un grupo se rechaza, informando en cuál ya está, si ya tiene uno en el otro (se aplica en ambos sentidos).
8. **Eliminar (R20):** un visitante se puede quitar del grupo visitado con «Eliminar alumno»; solo se borra la **visita** y su membresía de equipo allí. **Nunca** se tocan los datos del origen. Se puede deshacer.
9. **Si se elimina o archiva el curso de origen:** al eliminarlo se borran también sus visitas (el diálogo de R1 informa cuántos visitantes dejarán de aparecer en otros grupos). Archivarlo no cambia nada.
10. **El origen no cambia:** convertir en visitante nunca modifica la inscripción regular. «Convertir en regular» no aplica a un visitante.
11. **Fusión/importación de base (R19):** la visita se identifica por clave natural (curso visitado + alumno + curso de origen) y se trata como la inscripción: se agrega, y si cambia el origen o el tipo es un conflicto «antes → después».
12. **Mecanismo de datos** (se decide en el plan): lo más probable es un tipo `visitante` en `inscripcion` + columna `curso_origen_id`, con migración de bases existentes; no se pierde ningún dato. Es **cambio de modelo**, por eso se documenta en `CLAUDE.md` antes de implementar.

## Reglas propuestas (se añadirían a `CLAUDE.md`)
> **21. Visitantes de otro grupo:** un alumno regular de un grupo puede inscribirse como **Visitante** en otro grupo de la misma materia y ciclo. Todo lo que se le capture en el grupo visitado (participaciones, exámenes por nombre, tareas, proyecto) se guarda en su grupo de origen; el grupo visitado solo lo muestra y lo captura. Sin examen homónimo en el origen no se guarda. Se excluye de las exportaciones del grupo visitado por defecto. Quitar la visita no toca los datos del origen.

## Comandos
```
Pruebas:   .venv\Scripts\python.exe -m pytest
Una prueba: .venv\Scripts\python.exe -m pytest tests/test_visitantes.py -q
App:       .venv\Scripts\python.exe main.py
Empaquetar: scripts/construir_exe.ps1
```

## Estructura (archivos a tocar)
```
core/database.py     → columna/tipo nuevo + migración de bases existentes
core/models.py       → TipoInscripcion.VISITANTE, origen en ResumenAlumno
core/repository.py   → SQL: guardar/obtener visita, curso efectivo, resumen_curso con filas del origen
core/services.py     → inscribir_visitante, candidatos_visitante, redirección de las capturas, eliminar visita
core/importar_base.py→ fusión de visitas (R19)
exporters/curso.py   → «Tipo» = Visitante; excluido por defecto
ui_desktop/dialogos_curso.py → opción «Visitante de otro grupo» en «Agregar alumno»
ui_desktop/vista_curso.py    → marca de visitante en la tabla, avisos de redirección
ui_desktop/tema.py   → color/etiqueta del visitante (único lugar con colores)
tests/test_visitantes.py, tests/test_ui_visitantes.py
CLAUDE.md, README.md, core/version.py (1.7.0: es una función nueva con cambio de modelo)
```

## Estilo de código
Español sin acentos, type hints, SQL solo en `repository.py`, la UI no tiene reglas. Un único punto resuelve «¿en qué curso viven los datos de este alumno?», y todos los servicios de captura lo usan:
```python
def _curso_de_datos(self, curso_id: int, alumno_id: int) -> int:
    """El curso donde se guardan los datos del alumno: el de origen si es visitante, si no el mismo."""
```
El total, el promedio y la final siguen saliendo de sus únicas funciones (`total_con_piso`, `promedio_examenes`, `calificacion_final`).

## Estrategia de pruebas (datos ficticios, p. ej. `100000001`)
- Equipos: con equipo en la visita no se puede formar/agregar en el origen, ni a la inversa; el mensaje dice quién y dónde; sacarlo de uno lo libera para el otro.
- Nota: la participación capturada desde la visita lleva «Grupo 1510»; la capturada en el origen no lleva nota automática.
- Alta: solo regulares de otro grupo de la misma materia y ciclo; rechaza otra materia, otro ciclo, el mismo grupo y quien ya está inscrito allí.
- Participación capturada en B → aparece en el historial y el total de A; el total con piso (+5, −10, +5 = 5) es el mismo visto desde A y B.
- Examen homónimo existe → se guarda en A; no existe → no se guarda nada y el aviso es claro. Reemplazo y deshacer siguen funcionando (R12).
- Tareas y proyecto: igual (R14, R17); equipo en B califica al visitante y la nota queda en A.
- La final del visitante en B es igual a la de A (ponderaciones de A).
- Eliminar visita no toca datos del origen; deshacer la restaura; eliminar el origen borra sus visitas.
- Exportación: excluido por defecto, incluido con «Tipo» = Visitante.
- Migración: una base de la versión 1.6.x se abre sin perder nada; exportar/fusionar (R19) funciona con visitas.
- UI: la fila de visitante se distingue, la captura desde B avisa dónde se guardó.

## Límites
- **Siempre:** una sola fuente de verdad (el origen); confirmar en el servicio, no en la UI; correr toda la suite; actualizar `CLAUDE.md`/`README.md` y subir versión.
- **Preguntar antes:** crear exámenes automáticamente en el origen, mover o fusionar datos entre grupos, cambiar el origen de un visitante ya con datos.
- **Nunca:** duplicar calificaciones en dos cursos, modificar la inscripción regular al crear una visita, SQL fuera de `repository.py`, datos reales en pruebas.

## Criterios de éxito
1. Se puede inscribir como visitante a un regular de otro grupo de la misma materia y ciclo.
2. Todo lo capturado al visitante queda en el origen y se ve igual desde ambos grupos.
3. La calificación final del visitante es única (la del origen).
4. Quitar la visita o borrar un grupo no destruye datos del otro.
5. Bases anteriores se migran sin pérdida y la exportación/fusión de base sigue funcionando.
6. Suite completa en verde con las pruebas nuevas.

## Preguntas abiertas
Ninguna.
