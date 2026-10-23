# CLAUDE.md — Reglas del proyecto Participaciones

Este archivo define la estructura y las reglas del proyecto. Debe leerse antes de modificar código. Si una decisión cambia, se actualiza aquí en el mismo cambio. Descripción general en `README.md`.

## Idioma
- Documentación, interfaz y mensajes al usuario: **español**.
- Código (nombres de clases, funciones, variables): **español sin acentos ni ñ**, consistente con el dominio (`curso`, `alumno`, `participacion`, `decimas`).

## Arquitectura

```
core/            lógica; NUNCA importa nada de ui_*
importers/       lectura de archivos externos (Excel)
ui_desktop/      interfaz customtkinter; solo llama a core.services
tests/           pytest
data/            base de datos local (no versionar)
```

1. **`core/` es independiente de la interfaz.** Debe poder reutilizarse desde una futura `ui_web/` (FastAPI/Flask) sin cambios.
2. **Todo el SQL vive en `core/repository.py`.** Ninguna otra capa escribe consultas.
3. **La UI no contiene reglas de negocio.** Solo recoge datos, llama a `services` y muestra el resultado.
4. Programación orientada a objetos: modelos como clases (`Alumno`, `Curso`, `Inscripcion`, `Participacion`).
5. Sin servidor: SQLite en archivo local. No introducir dependencias de red.

## Modelo de datos

```
alumno(id PK, num_cuenta UNIQUE NULL, nombre_completo, nombre_norm)  -- nombre_norm se deriva de nombre_completo (solo para buscar)
curso(id, ciclo, carrera, materia, grupo, archivado)  -- único por ciclo+materia+grupo
inscripcion(curso_id, alumno_id, tipo 'regular'|'oyente')
participacion(id, curso_id, alumno_id, decimas, fecha, nota)
examen(id, curso_id, nombre, nombre_norm)  -- único por curso+nombre_norm; sin puntaje máximo
calificacion(examen_id, alumno_id, puntos, fecha)  -- una por alumno y examen (PK compuesta)
calificacion_tareas(curso_id, alumno_id, puntos, fecha)  -- una por alumno y curso (PK compuesta); promedio ya calculado fuera
calificacion_proyecto(curso_id, alumno_id, puntos, fecha)  -- una por alumno y curso (PK compuesta); sin vínculo con el equipo
ponderacion(curso_id PK, participaciones, examenes, tareas, proyecto)  -- porcentajes de la calificación final por curso; sin fila = 10/0/20/40; nunca se guarda la calificación final
equipo(curso_id, numero, nombre, proyecto)  -- equipos de proyecto; nombre y título del proyecto opcionales ('' si no hay); no se borran al quedar vacíos (así el número no se reutiliza)
miembro_equipo(curso_id, alumno_id, numero)  -- un alumno en un solo equipo por curso (PK compuesta)
```

## Reglas de negocio

1. **CRUD de cursos:** crear, importar, ver, editar, **archivar** y **eliminar**. Archivar es reversible; eliminar es definitivo y exige confirmación explícita indicando cuántas participaciones (y, si las hay, exámenes, calificaciones y calificaciones de tareas) se perderán.
2. **Nombre completo en un solo campo** (`nombre_completo`), tal como viene en la lista. Nunca separar apellidos.
3. **Normalización para comparar y buscar:** ignorar mayúsculas, acentos y espacios repetidos o sobrantes. Se guarda en mayúsculas y con espacios limpiados.
4. **Participaciones como eventos con fecha.** El total de un alumno se calcula a partir de sus participaciones; nunca guardar un total acumulado.
5. **Décimas negativas permitidas** (sirven para corregir), con un **mínimo de 0 en el total**.
   - Las participaciones se guardan tal como se capturaron (p. ej. `-10`).
   - El total se calcula en orden cronológico (fecha, id) sin bajar nunca de 0 (`core/puntaje.py::total_con_piso`): `+5, -10, +5` da `5`, no `0`.
   - Es la **única** función que calcula totales; el repositorio y los servicios la usan, la UI no recalcula.
   - Al registrar, el resultado incluye `decimas_aplicadas` (cambio real del total). Si difiere de lo solicitado, la UI avisa: «-10 solicitadas, se aplicaron -5 (mínimo 0)».
   - Editar, borrar o deshacer una participación recalcula el total con la misma regla.
6. **Registro rápido en la pantalla Curso:** el alumno se identifica por número de cuenta **o** nombre completo (también coincidencia parcial).
   - Si existe: sumar y avisar con nombre, décimas sumadas y total.
   - Si hay varias coincidencias: pedir que elija; nunca adivinar.
   - Si no existe: avisar y dejar elegir si se crea en ese curso como **regular** u **oyente**.
   - Debe poder deshacerse el último registro.
   - Un clic en una fila de la tabla carga a ese alumno en el campo de registro (sin escribir su nombre) y pasa el foco a las décimas. Solo reacciona a clics del usuario, no a selecciones programáticas (p. ej. el resaltado tras guardar).
7. **Oyentes:** pueden existir sin número de cuenta (`num_cuenta` NULL). Se conservan sus participaciones. No aparecen en exportaciones de calificaciones salvo que se pida.
8. **Importación de lista de inscripción:** el encabezado trae ciclo, carrera, materia y grupo; la tabla trae `No. | No. Cuenta | Nombre`.
   - Alumnos se identifican por número de cuenta.
   - Reimportar no duplica alumnos ni borra participaciones.
   - Si un alumno de la lista coincide por nombre normalizado con un oyente sin cuenta, **preguntar** si son la misma persona; en caso afirmativo asignar la cuenta y pasar a `regular`. Nunca fusionar sin confirmación.
9. **Unicidad de curso** por ciclo + materia + grupo.

10. **Exportación** (`exporters/curso.py`, sin dependencia de la UI): `.xlsx` (hoja «Resumen» + hoja opcional «Participaciones» con efecto real y total acumulado) o `.csv` (solo resumen, UTF-8 con BOM).
   - Los **oyentes se excluyen por defecto**; se pueden incluir (agrega la columna «Tipo»).
   - Los totales se exportan como **números**, ya con el mínimo de 0 aplicado (los calcula el servicio); nunca como fórmulas de suma.
   - El «Resumen» siempre trae, después de «Décimas», «Tareas» (R14), «Equipo» (R16: número de equipo, vacío si no tiene) y «Proyecto» (R17); tareas y proyecto son números y valen 0 sin capturar. Si el curso tiene exámenes, agrega después una columna «Examen - <nombre>» por examen (sin capturar = 0) y «Promedio exámenes» (R13), también como números. Luego va «Calificación final» (R18, entero redondeado, antes de «Participaciones»); en el `.xlsx` una línea bajo el título indica las ponderaciones usadas. La hoja «Participaciones» no incluye exámenes, tareas, proyecto ni la final.
   - El número de cuenta se guarda como **texto**; las fechas como fechas reales de Excel.
   - Si el archivo está abierto en Excel o la carpeta no existe, se informa con un mensaje claro (`ErrorDominio`), sin cerrar la app.

11. **Rutas y empaquetado** (`core/rutas.py`): nunca construir rutas con `__file__` fuera de ese módulo.
   - Desarrollo: datos en `data/` del proyecto. Empaquetada (`sys.frozen`): `%LOCALAPPDATA%\Participaciones\data`, **fuera** de la carpeta del `.exe`, para que reconstruir la app nunca borre datos.
   - Los archivos incluidos (íconos, etc.) se leen con `rutas.recurso(...)`; deben listarse en `datas` de `participaciones.spec`.
   - Se genera con `scripts/construir_exe.ps1`. La versión vive en `core/version.py` (súbela antes de cada entrega).

12. **Exámenes y calificaciones** (independientes de las décimas; no afectan `total_con_piso`):
   - Un curso tiene varios exámenes, solo con nombre (único por curso comparado normalizado). **Sin tope máximo**: se aceptan puntos extra.
   - Una calificación por alumno y examen, `>= 0` (decimales permitidos; negativos rechazados). Capturar otra vez **reemplaza** la anterior, pero antes se advierte («Ya tiene X; se cambiará a Y») y se pide confirmar; el cambio se puede deshacer.
   - Eliminar un examen exige confirmación indicando cuántas calificaciones se perderán; eliminar un curso borra sus exámenes y calificaciones.
   - Los oyentes pueden tener calificaciones y se excluyen de exportaciones por defecto, igual que las participaciones.
13. **Promedio de exámenes** (`core/promedio.py::promedio_examenes`, única fuente): media simple de los puntos sobre **todos** los exámenes del curso; un examen sin calificación vale 0. Sin exámenes no hay promedio. No se guarda; la UI y el exportador no lo recalculan.

14. **Calificación de tareas** (independiente de décimas y exámenes; no afecta `total_con_piso` ni el promedio de exámenes):
   - Es el promedio de tareas **ya calculado en otra plataforma**: la app solo lo guarda y lo muestra; nunca lo calcula ni guarda tareas individuales.
   - Una sola por alumno y curso, `>= 0` (decimales permitidos; negativos rechazados), **sin tope**. Sin captura vale 0.
   - Capturar otra vez **reemplaza** la anterior, pero antes se advierte («Ya tiene X en tareas; se cambiará a Y») y se pide confirmar; el cambio se puede deshacer.
   - Los oyentes pueden tenerla y se excluyen de exportaciones por defecto. Eliminar un curso la borra (el diálogo informa cuántas se pierden).

15. **Importar tareas desde archivo** (`importers/calificaciones_plataforma.py` lee; `core/services.py` decide; independiente de décimas y exámenes):
   - Se importa **una columna** de un `.xlsx` o `.csv` de otra plataforma (la persona elige; por omisión la numérica de más a la derecha, que es el promedio). El valor se guarda tal cual por el servicio de tareas (R14): `>= 0`, sin tope, reemplaza el anterior.
   - **Nada se guarda sin vista previa y confirmación.** El lector no depende de posiciones fijas: reconoce a un alumno por apellidos, nombres y correo (`@`) en las tres primeras columnas.
   - Identificación **por nombre** (normalizado, R3), o por número de cuenta si el archivo trae una columna «Cuenta» (tiene prioridad; el nombre queda de respaldo): coincidencia exacta única → se aplica; mismas palabras en otro orden o un nombre contenido en el otro → **dudosa**, solo se aplica si la persona la confirma; varias o ninguna coincidencia, o nombre repetido en el archivo → se omite. **Nunca se crean alumnos** ni se tocan los que el archivo no menciona.
   - Valor vacío, no numérico, negativo o no finito → fila omitida con su motivo; una celda vacía no cambia la calificación existente. Si el archivo trae grupo y ciclo y no coinciden con el curso, la vista previa avisa.
   - La importación completa se puede **deshacer**.

16. **Equipos de proyecto** (independientes de décimas, exámenes y tareas; no tocan ninguna calificación):
   - Un equipo se forma con **1 o más alumnos** del curso (también oyentes), con un **nombre** (máx. 60 caracteres) y el **título de su proyecto** (máx. 120), ambos opcionales y editables después; no se exige que sean únicos. El número es **incremental por curso** (máximo histórico + 1) y **nunca se reutiliza**, aunque el equipo se quede sin miembros; un equipo vacío no aparece en pantalla.
   - Un alumno está en **un solo equipo** por curso. Si entre los elegidos hay quien ya tiene equipo, **no se crea ni se mueve nada** y se informa quién y en cuál; hay que separarlo antes. Nunca se mueve a nadie sin que lo pida.
   - **Separar** saca a uno o varios alumnos de su equipo (quien no tiene equipo se ignora). **Agregar** suma alumnos sin equipo a un equipo que ya tiene miembros (a quien ya tiene equipo no se le ofrece; un equipo vacío no se revive). Formar, separar y agregar se pueden deshacer. Eliminar un curso borra sus equipos.

17. **Calificación del proyecto final** (independiente de décimas, exámenes y tareas; no afecta `total_con_piso`, el promedio de exámenes ni las tareas):
   - Una por **alumno** y curso, `>= 0` (decimales permitidos; negativos rechazados), **sin tope**. Sin captura vale 0.
   - Se captura a **un alumno** (cuenta o nombre, como siempre) o a **un equipo** escribiendo «equipo N» (también «e N»; un número solo sigue siendo número de cuenta): calificar a un equipo **copia la misma nota a cada miembro**. No se guarda ningún vínculo nota–equipo: sacar, agregar o corregir a alguien después no cambia las notas de los demás.
   - Si algún alumno afectado ya tiene una nota **distinta** de la nueva (las iguales no cuentan) no se guarda nada hasta confirmar el reemplazo; con un equipo se avisa «N de M miembros ya tienen calificación». «Deshacer» restaura las notas previas de **todos** los afectados (o las elimina si no había). Los oyentes pueden tenerla y se excluyen de la exportación por defecto. Eliminar un curso la borra (el diálogo informa cuántas se pierden).

18. **Calificación final** (`core/calificacion_final.py`, única fuente del cálculo; el servicio la usa, la UI y el exportador no la recalculan; **nunca se guarda**):
   - Es una **suma ponderada** de cuatro componentes en escala de 0 a 100: **participaciones** (el total con piso de 0 de R5 × 10: 1 décima = 10 puntos; 10 décimas = 100 puntos = calificación 10), **promedio de exámenes** (R13), **tareas** (R14) y **proyecto** (R17) tal cual se capturaron. `final = Σ componente × ponderación / 100`, sin tope: los componentes y la suma pueden pasar de 100 (puntos extra).
   - Las **ponderaciones son por curso**, cada una de 0 a 100 %, con decimales; **la suma puede ser cualquiera** (más de 100 % son puntos extra). Un curso sin ponderaciones guardadas usa **participaciones 10 %, exámenes 0 %, tareas 20 % y proyecto 40 %**: los exámenes pesan 0 hasta que se asigna su ponderación (al crear un examen la app lo pide; sugiere 30 %). Guardar 0 % en exámenes explícitamente cuenta como asignado.
   - Sin exámenes no hay promedio y ese componente aporta 0 (su peso no se redistribuye); lo no capturado vale 0.
   - **Redondeo solo al mostrar y exportar**: entero con la mitad hacia arriba (87.5 → 88; no el redondeo por banca de Python) y equivalencia de 0 a 10 con un decimal (81 → 8.1) calculada del valor exacto. Ordenar usa el valor exacto.
   - Cambiar las ponderaciones o cualquier componente recalcula la final de inmediato; no modifica décimas, exámenes, tareas ni proyecto.

## Interfaz
- **Paleta** (`ui_desktop/tema.py`, único lugar con colores; las vistas usan sus nombres, nunca hex ni `gray`): azul de la FES Aragón = marca y participaciones; **índigo = modo Examen** (vecino del azul, se distingue sin chocar); **verde azulado = modo Tareas**; **ciruela = modo Proyecto** (y dos tonos alternados, azul-gris y ciruela pálido, para agrupar los equipos en la tabla); verde = éxito, rojo = peligro, ámbar = avisos. Cada color es un par (claro, oscuro); los rellenos llevan texto blanco, el texto de enlaces usa `COLOR_ACENTO_TEXTO`.
- Panel lateral izquierdo con **Cursos** y **Configuración** (solo esas dos por ahora).
- **Cursos:** botones Crear / Importar / Eliminar arriba; cards (nombre, grupo, semestre) al centro; menú por card con Editar, Archivar, Eliminar.
- **Curso:** botones «Exportar», «Agregar alumno», «Importar tareas» y «⚖ Ponderaciones» arriba; registro rápido + tabla de alumnos (No., Cuenta, Nombre, Décimas, Tareas, Proyecto, una columna «Examen - <nombre>» por examen, **Final** (0–100, entera), **Final /10** (un decimal), Última; los valores desde «Décimas» van centrados; «Final» y «Final /10» se ordenan por el valor exacto); clic en una fila = elegir alumno. Operable con teclado; tras guardar, el foco vuelve al campo de alumno. Confirmación como franja no bloqueante, no como diálogo modal.
  - **Selector segmentado `[Participación | Examen | Tareas | Proyecto]`** en el registro rápido (**F2 recorre los cuatro modos en ciclo**). En modo Examen aparece la lista de exámenes con «＋ Nuevo» y «⋯» (Renombrar…, Eliminar… con confirmación y conteo de calificaciones); el campo pasa a «Calificación» y se conservan el modo y el examen tras guardar. Usa la misma identificación de alumno que las participaciones (cuenta, nombre parcial, varias coincidencias, no existe).
  - Si el alumno ya tiene calificación en ese examen, la franja avisa «Ya tiene X; se cambiará a Y» con «Reemplazar» / «Cancelar» (no guarda hasta confirmar); «Deshacer» restaura la anterior o elimina la calificación. En modo Examen o Tareas, elegir a un alumno (clic en fila o sugerencia) trae su calificación actual para corregirla.
  - **Modo Tareas:** campo «Calificación de tareas» (el promedio ya calculado en otra plataforma; sin lista de exámenes), mismo flujo de identificación, reemplazo («Ya tiene X en tareas; se cambiará a Y») y «Deshacer». «Deshacer» revierte solo lo último guardado (participación, examen o tareas). La tabla trae la columna «Tareas» (0 sin captura) entre Décimas y los exámenes.
  - **Importar tareas (R15):** «⬆ Importar tareas» abre el selector de `.xlsx`/`.csv` y el diálogo con la vista previa: columna a importar (por omisión la numérica de más a la derecha), resumen (coinciden, cambian, quedan igual, dudosas, omitidas, alumnos que no aparecen), tabla «antes → después», casillas para las dudosas y confirmación «Importar de todos modos» si el grupo del archivo no coincide. «Aplicar N cambios» guarda; la franja ofrece «Deshacer importación» (restaura todo lo importado) hasta la siguiente captura.
  - **Calificación final (R18):** «⚖ Ponderaciones» abre el diálogo con los cuatro porcentajes (participaciones, exámenes, tareas, proyecto final), la **suma en vivo** («Suma: 110 % · 10 % de puntos extra» o «faltan N %») y los botones «Restablecer» (rellena 10 / 0 / 20 / 40 sin guardar), «Guardar» y «Cancelar»; los valores inválidos (vacío, no numérico, fuera de 0–100) se avisan dentro del diálogo y al guardar la tabla se recalcula. **Al crear un examen** en un curso sin ponderación asignada se abre ese diálogo con el foco en «Exámenes» y 30 % sugerido; cancelar no bloquea (el examen queda creado y la franja recuerda «Los exámenes aún no pesan en la calificación final…»); el mismo recordatorio sale al abrir un curso que ya tiene exámenes y nunca guardó ponderaciones. Guardar 0 % explícito cuenta como asignado.
  - **Modo Proyecto (R16, R17):** con «Formar equipos» apagado es el modo **evaluar**: bajo el botón «Formar equipos» está el registro (campo «Número de cuenta, nombre o «equipo N»», «Calificación del proyecto» y «Registrar proyecto»), con el mismo flujo que tareas: identificación, reemplazo con «Reemplazar» / «Cancelar», «Deshacer» y clic en una fila que carga al alumno y su nota. Escribir **«equipo N»** (o «e N») califica a todo el equipo; el botón **«Usar equipo N»** (activo si el alumno cargado tiene equipo) y el clic en la **fila del equipo** (el encabezado) mandan «equipo N» al registro. Con notas distintas ya capturadas la franja avisa «N de M miembros ya tienen calificación; se cambiarán a X» y «Deshacer» devuelve las notas previas de todos. La tabla agrega la columna «Equipo» y se **agrupa por equipo**: una fila de encabezado coloreada «Equipo N · M alumnos · <nombre> · <proyecto>» (el nombre y el proyecto solo si existen; no es un alumno: no se selecciona, no abre historial ni cuenta), sus miembros debajo con el mismo color suave, dos tonos que se alternan por orden de aparición, y al final los alumnos sin equipo (sin encabezado ni color). **Doble clic en el encabezado** edita el nombre y el título del proyecto del equipo. Ordenar por otra columna ordena dentro de cada equipo. En los demás modos la tabla no cambia.
  - **Formar equipos** (el registro se oculta mientras está activo): el botón «Formar equipos» activa la selección: **un clic agrega al alumno y otro lo quita** (Mayús y Ctrl siguen valiendo); el clic ya no carga al alumno y el doble clic no abre el historial. Debajo del botón, a la izquierda, «Crear equipo con N alumnos» (desde 1; abre un diálogo con el nombre del equipo y el título de su proyecto, opcionales, y Cancelar no forma el equipo) y «Sacar de equipo (N)». Con clic derecho: «Sacar del equipo N» (o «de sus equipos») y «Agregar a ▸» con la lista de equipos formados (solo para quien no tiene equipo). La franja avisa, resalta a los alumnos afectados y «Deshacer» revierte lo último; cambiar de modo limpia la selección.
  - No hay columna de promedio en pantalla: el promedio vive en la exportación.
- **Historial de alumno:** tarjetas de resumen (total, participaciones, última y **calificación final** con su equivalencia «= 7.8 de 10»), una línea de **desglose** de la final (componente, valor de 0 a 100 × ponderación = aporte; lo arma `ServicioParticipaciones.desglose_final`, la UI no calcula), selector de curso, tabla editable de participaciones y alta con fecha anterior.
  - Se abre con doble clic en una fila de la pantalla Curso; «← Curso» regresa al curso seleccionado.
  - Cada fila muestra fecha, décimas capturadas, **efecto real** y **total acumulado** (los calcula `ServicioParticipaciones.historial_detallado`; la UI no calcula). Las filas donde se aplicó el mínimo de 0 se marcan con ⚑.
  - Editar y eliminar una participación recalculan el total; eliminar pide confirmación.
  - Sección **«Exámenes, tareas y proyecto»** bajo las participaciones: primero la fila «Tareas», luego «Proyecto final» (con «· Equipo N» si tiene) y después una por examen del curso (Concepto, Calificación, Fecha; sin capturar = 0 y «—»), con «Calificar / editar» (calificación ≥ 0 y fecha) y «Quitar calificación» (con confirmación; vuelve a valer 0).
  - Un oyente muestra «Convertir en regular» (conserva el historial); «Editar alumno» corrige nombre y cuenta (la cuenta no puede repetirse).
- Fuera de alcance por ahora: gráfica de evolución, sección global Alumnos, usuarios/login, sincronización en la nube.

## Convenciones de código
- Python 3.11+, tipado con type hints, formato con `black`/`ruff` si se instalan.
- Dependencias mínimas: `customtkinter`, `openpyxl`, `pytest`.
- Cada regla de negocio nueva lleva su prueba en `tests/`.
- **Los tests solo usan datos ficticios** (nombres y cuentas inventados, p. ej. `100000001`). Nunca copiar nombres ni números de cuenta reales al código, tests, README ni commits.
- Para probar el importador con una lista real, define la variable de entorno `LISTA_REAL` con su ruta (`$env:LISTA_REAL = "..."`); esa prueba se omite si no existe. Igual para el importador de tareas: `PLATAFORMA_REAL` (.xlsx) y `PLATAFORMA_REAL_CSV` (.csv).
- Datos reales de alumnos (Excel, `.db`) **no se versionan**; van en `data/` y en `.gitignore`.
- Respaldo automático del `.db` al cerrar la aplicación.

## Cómo trabajar con Claude
- Antes de cambiar el modelo de datos o una regla, proponer el cambio y actualizar este archivo.
- Mantener `README.md` coherente con este archivo cuando cambie el alcance.
