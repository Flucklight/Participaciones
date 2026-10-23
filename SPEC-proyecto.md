# Spec: Calificación del proyecto final (módulo `proyecto`)

Estado: **BORRADOR; la persona ya aprobó los supuestos 6 y 7 (sintaxis «equipo N» y «Usar equipo N»), el 4 (la nota no se sincroniza) y la columna «Equipo» en la exportación; falta la aprobación final** (sin código ni cambios a `CLAUDE.md` todavía). Índice: `MAPA-proyecto.md`. Depende de `SPEC-equipos.md` (módulo `equipos`): solo **lee** quiénes son los miembros de un equipo.

## Objetivo

Además de décimas, exámenes y tareas, el profesor lleva la **calificación del proyecto final**. Se califica **a un equipo** (la nota se copia a todos sus miembros) y después se puede **corregir a cada alumno por separado**. La calificación se guarda **por alumno**.

Usuario: el profesor, al evaluar entregas y al corregir casos individuales, con teclado.

Decisiones ya tomadas con la persona:
- En la sección «Proyecto» hay un modo **evaluar**: calificar a un **equipo** integra la nota a todos sus miembros; también se puede **modificar la calificación individual** de cualquier alumno.
- Si algún miembro ya tiene una calificación individual, se **avisa y se pide confirmar** el reemplazo (como en tareas y exámenes), con **deshacer**.
- Aparece en: modo evaluar, **columna «Proyecto»** en la tabla del curso, **historial** del alumno y **exportación**.

## Supuestos (corrígeme ahora o procedo con ellos)

1. **Una calificación de proyecto por alumno y curso** (el proyecto final es uno solo), `>= 0`, decimales permitidos, **sin tope** (puntos extra), igual que tareas. Sin captura **vale 0**.
2. Es **independiente** de décimas, exámenes y tareas: no modifica `total_con_piso`, el promedio de exámenes (R13) ni la calificación de tareas, y no entra en ningún promedio.
3. Se guarda con su **fecha de captura** (hoy por defecto; editable desde el historial). Solo hay un valor vigente.
4. **Calificar a un equipo** escribe la misma nota en cada miembro **en ese momento**. No se guarda un vínculo «nota del equipo»: si después se agrega o se separa a alguien, **su nota no cambia sola**; separar a un alumno conserva su calificación.
5. **Reemplazo en dos pasos** (como tareas): si ningún miembro tenía una calificación **distinta** de la nueva se guarda de inmediato; si **alguno ya tenía otra** (las iguales no cuentan), la franja avisa «N de M miembros del equipo 3 ya tienen calificación; se cambiarán a X» con «Reemplazar» / «Cancelar». Nada se guarda hasta confirmar. «Deshacer» restaura las calificaciones previas de **todos** los miembros (o las elimina si no existían).
6. **Cómo se elige el destino** en el campo de registro de modo «Proyecto → evaluar»:
   - Un **alumno** (cuenta o nombre, parcial, varias coincidencias, no existe → crear regular u oyente, igual que siempre) → califica **solo a ese alumno**.
   - El texto **«equipo N»** (también «e N») → califica **a todo el equipo N**. Un número solo sigue siendo un número de cuenta; no se confunde.
   - Equipo que no existe o sin miembros → mensaje claro, no guarda.
7. **Clic en una fila** (modo evaluar) carga a ese alumno y su calificación actual para corregirla, como en tareas. Si el alumno tiene equipo, un botón **«Usar equipo N»** junto al campo cambia el destino a «equipo N» para calificar a todos.
8. **Modo evaluar y modo formar** conviven en la sección «Proyecto» (`[Evaluar | Formar equipos]`); por omisión se abre en **evaluar**. En modo formar no hay campo de registro (spec de `equipos`).
9. Los **oyentes** pueden tener calificación de proyecto y pertenecer a equipos; se excluyen de la exportación por defecto, igual que el resto.
10. **Eliminar un curso** borra sus calificaciones de proyecto; el diálogo informa cuántas se pierden.
11. Sin migración manual: la tabla nueva se crea sola (`CREATE TABLE IF NOT EXISTS`).

## Modelo de datos (cambio propuesto)

```
calificacion_proyecto(curso_id FK→curso ON DELETE CASCADE, alumno_id FK→alumno ON DELETE CASCADE,
                      puntos REAL, fecha TEXT, PRIMARY KEY (curso_id, alumno_id))
```

No se guarda a qué equipo pertenecía la nota: es la nota del alumno.

## Reglas de negocio nuevas (se agregarán a `CLAUDE.md` al implementar)

- **R17 Calificación de proyecto:** supuestos 1–7 y 9–10; una por alumno y curso, `>= 0`, sin tope; calificar a un equipo copia a cada miembro; reemplazo con advertencia y confirmación; deshacer restaura a todos los miembros; independiente de las demás calificaciones.
- Actualizar Modelo de datos, Interfaz (modo evaluar, columna «Proyecto», historial) y Exportación.

## Interfaz

**Registro rápido en modo «Proyecto → Evaluar»:**

```
[ Participación ][ Examen ][ Tareas ][■ Proyecto ]         [ ■ Evaluar | Formar equipos ]
Alumno o «equipo N»: [equipo 3_________]  [Usar equipo 3]  Calificación del proyecto: [____]  [Registrar proyecto]
```

- Misma mecánica que tareas: tras guardar, foco al campo de alumno y se conserva el modo; franjas «Equipo 3 · Proyecto: 9.5 (4 alumnos)» y «Ana Pérez · Proyecto: 8».
- Reemplazo y «Deshacer» como en el supuesto 5; «Deshacer» revierte solo lo último guardado (participación, examen, tareas o proyecto).

**Tabla del curso:** columna **«Proyecto»** entre «Tareas» y las columnas de examen; 0 sin captura; ordenable. En modo «Proyecto» se agrega «Equipo» (spec de `equipos`).

**Historial del alumno:** la sección pasa a llamarse **«Exámenes, tareas y proyecto»**; su fila **«Proyecto final»** (con «· Equipo N» si tiene) muestra calificación y fecha (0 y «—» sin captura), y se puede calificar, corregir y quitar (con confirmación; vuelve a valer 0) como las demás filas.

**Exportación:** columnas **«Proyecto»** (número, después de «Tareas») y **«Equipo»** (número de equipo o vacío, justo antes de «Proyecto»), en `.xlsx` y `.csv`; siempre presentes (sin captura, Proyecto = 0).

## Comandos

```
Pruebas:    .venv\Scripts\python.exe -m pytest
Una prueba: .venv\Scripts\python.exe -m pytest tests/test_proyecto.py -q
Ejecutar:   .venv\Scripts\python.exe main.py
Empaquetar: powershell -ExecutionPolicy Bypass -File scripts\construir_exe.ps1   (subir core/version.py antes)
```

## Estructura (archivos a tocar o crear)

```
core/database.py        → tabla calificacion_proyecto
core/models.py          → CalificacionProyecto, ResultadoProyecto; ResumenAlumno gana `proyecto: float`
core/repository.py      → todo el SQL de calificacion_proyecto (obtener, guardar, eliminar, por alumno, contar, de varios)
core/services.py        → registrar_proyecto (alumno o «equipo N», reemplazo en dos pasos), deshacer_proyecto,
                          proyecto_de, establecer_proyecto, eliminar_proyecto; conteo al eliminar un curso
exporters/curso.py      → columnas «Equipo» y «Proyecto»
ui_desktop/vista_curso.py → modo evaluar, «Usar equipo N», columna «Proyecto», reemplazo y deshacer
ui_desktop/vista_historial.py, dialogos_historial.py → fila «Proyecto final»
ui_desktop/dialogos.py, vista_cursos.py → el diálogo de eliminar curso cuenta los proyectos
tests/test_proyecto.py, test_ui_curso.py, test_ui_historial.py, test_exportacion.py, test_cursos.py (ampliar)
CLAUDE.md, README.md    → R17 y pantalla; subir core/version.py
```

## Estilo de código

Mismo patrón que tareas (`registrar_tareas`, `ResultadoTareas`), con un resultado que además informa a quiénes afecta:

```python
@dataclass
class ResultadoProyecto:
    estado: EstadoRegistro  # GUARDADO | CONFIRMAR_REEMPLAZO | AMBIGUO | NO_EXISTE
    puntos: float
    alumnos: list[Alumno] = field(default_factory=list)  # a quién(es) se aplicó
    equipo: int | None = None  # si se calificó a un equipo
    anteriores: dict[int, CalificacionProyecto | None] = field(default_factory=dict)  # para deshacer
    candidatos: list[Alumno] = field(default_factory=list)
```

## Estrategia de pruebas

pytest, datos ficticios. Cada regla lleva su prueba:
- Esquema: tabla creada en base nueva y existente; PK única; cascada.
- Servicio: negativo, `nan` y texto rechazados; 0 y puntos extra aceptados; alumno individual (cuenta, nombre parcial, ambiguo, no existe); **«equipo N» copia la nota a todos los miembros**; «e N» equivalente; equipo inexistente o vacío rechazado; reemplazo solo tras confirmar y con el conteo correcto («N de M»); deshacer restaura anteriores y elimina las nuevas de **todos**; corregir a un alumno **no** cambia al resto del equipo; separar a un alumno conserva su nota; agregar a alguien al equipo no le pone nota; independencia de `total_alumno`, `prom_examenes` y `tareas`.
- Resumen: `proyecto` = 0 sin captura; refleja lo capturado.
- Exportación: «Equipo» y «Proyecto» en xlsx y csv, numéricos, en el orden acordado; oyentes excluidos por defecto; curso sin datos exporta 0 y equipo vacío.
- UI (humo): modo evaluar en la sección «Proyecto», calificar alumno y calificar «equipo N», «Usar equipo N», reemplazo con confirmación y deshacer, clic en fila carga la nota actual, columna y orden, historial (calificar, corregir, quitar con confirmación), diálogo de eliminar curso con conteo.
- Regresión: la suite completa sigue pasando.

## Límites

- **Siempre:** correr `.venv\Scripts\python.exe -m pytest` antes de cada commit; reutilizar la identificación de alumnos del servicio; SQL solo en el repositorio; `core/` sin importar `ui_*`; actualizar `CLAUDE.md` y `README.md`; datos ficticios; colores solo en `tema.py`.
- **Preguntar antes:** guardar un vínculo permanente entre la nota y el equipo (cambia el modelo); cambiar tablas existentes; añadir dependencias.
- **Nunca:** guardar una nota «de equipo» calculada o sincronizada automáticamente; reemplazar calificaciones sin confirmar; mezclar el proyecto con décimas, `total_con_piso`, el promedio de exámenes o tareas; copiar datos reales de alumnos.

## Criterios de éxito

1. Con un equipo de 4, escribir «equipo 3» y «9.5» y presionar Enter pone 9.5 a los 4 y la franja dice «Equipo 3 · Proyecto: 9.5 (4 alumnos)»; posible sin mouse tras elegir el modo (F2).
2. Si 2 de los 4 ya tenían nota distinta, avisa «2 de 4 miembros del equipo 3 ya tienen calificación; se cambiarán a 9.5», no guarda hasta confirmar y «Deshacer» devuelve las notas de los 4.
3. Corregir a un solo alumno (cuenta o nombre) cambia solo su nota; el resto del equipo no se mueve.
4. Una calificación negativa o no numérica se rechaza; 0 y valores sobre 10 (o 100) se aceptan.
5. La tabla muestra «Proyecto» (0 sin captura) y se ordena por ella; el historial permite calificar, corregir y quitar la fila «Proyecto final».
6. El `.xlsx` y el `.csv` traen «Equipo» y «Proyecto» como número; los oyentes siguen excluidos por defecto.
7. Décimas, exámenes, tareas y sus promedios se comportan exactamente como antes.
8. Una base `.db` existente abre sin errores; eliminar un curso informa cuántas calificaciones de proyecto se pierden.
9. La suite completa pasa.

## Preguntas abiertas

Ninguna bloqueante. Los supuestos 1–11 se toman como aceptados salvo que los corrijas; los que más conviene que revises: **sintaxis «equipo N» y botón «Usar equipo N»** (6 y 7), que **la nota no se sincroniza** con el equipo después de calificar (4), y **columna «Equipo» en la exportación** (antes de «Proyecto»).
