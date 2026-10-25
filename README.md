# Participaciones

Aplicación local de escritorio para registrar y gestionar las participaciones (décimas) de los estudiantes, por semestre, materia y grupo. Reemplaza el libro de Excel con macros (`Participaciones.xlsm`) que hoy requiere una tabla nueva por cada curso.

## Objetivo

Centralizar en un solo sistema todos los cursos, alumnos y participaciones, con un CRUD simple y un registro rápido pensado para usarse durante la clase.

## Stack

- **Python 3.11+**
- **SQLite** (archivo local `data/participaciones.db`, sin servidor)
- **customtkinter** para la interfaz de escritorio
- **openpyxl** para importar y exportar Excel
- **pytest** para pruebas

El proyecto se diseña para poder escalar a web más adelante: la lógica vive en `core/` y no depende de la interfaz (ver `CLAUDE.md`).

## Modelo de datos

```
alumno(id PK, num_cuenta UNIQUE NULL, nombre_completo, nombre_norm)
curso(id, ciclo, carrera, materia, grupo, archivado)   -- único por ciclo+materia+grupo
inscripcion(curso_id, alumno_id, tipo: 'regular' | 'oyente' | 'visitante', curso_origen_id) -- curso_origen_id solo para visitantes: el grupo donde viven sus datos
participacion(id, curso_id, alumno_id, decimas, fecha, nota)
examen(id, curso_id, nombre, nombre_norm)               -- único por curso+nombre; sin puntaje máximo
calificacion(examen_id, alumno_id, puntos, fecha)       -- una por alumno y examen
calificacion_tareas(curso_id, alumno_id, puntos, fecha) -- una por alumno y curso; promedio ya calculado fuera
calificacion_proyecto(curso_id, alumno_id, puntos, fecha) -- una por alumno y curso; sin vínculo con el equipo
ponderacion(curso_id, participaciones, examenes, tareas, proyecto) -- porcentajes de la calificación final por curso (sin fila: 10/0/20/40)
equipo(curso_id, numero, nombre, proyecto)              -- equipos de proyecto (nombre y proyecto opcionales); no se borran al quedar vacíos
miembro_equipo(curso_id, alumno_id, numero)             -- un alumno en un solo equipo por curso
```

- El nombre se guarda **completo en un solo campo**, tal como viene en la lista de inscripción (`APELLIDO_PATERNO APELLIDO_MATERNO NOMBRES`). No se separan apellidos porque los compuestos (`DE LA PAZ`) no se pueden dividir de forma confiable.
- Las participaciones son **eventos con fecha**; el total de un alumno se calcula sumándolas.
- Los **oyentes** no tienen número de cuenta hasta que aparecen en una lista de inscripción.
- Un alumno regular de un grupo puede ser **visitante** de otro grupo de la misma materia y ciclo. Todo lo que se le captura en el grupo que visita (participaciones, exámenes, tareas, proyecto) se guarda en su **grupo de origen**; nada se duplica y su calificación final es una sola, la del origen.
- Los **exámenes** son independientes de las décimas: una calificación por alumno y examen, sin tope (se aceptan puntos extra). Un examen sin capturar vale 0. El **promedio de exámenes** es la media simple de todos los exámenes del curso y se calcula en `core/promedio.py`.
- La **calificación de tareas** es el promedio de tareas que ya calculó otra plataforma: se captura (o corrige) por alumno y curso, sin tope, y la app no calcula nada. Sin captura vale 0. Es independiente de décimas y exámenes.
- Los **equipos de proyecto** se forman por curso con 1 o más alumnos. El número es incremental y **nunca se reutiliza**, aunque el equipo se quede sin miembros. Un alumno está en un solo equipo. No afectan ninguna calificación.

## Pantallas

### Principal
Panel lateral izquierdo para navegar. Las vistas se muestran en el área central.
Secciones: **Cursos** y **Configuración** (respaldos, carpeta de datos y exportar/importar la base).

### Pasar los datos de una computadora a otra
En **Configuración**: en la computadora de origen pulsa **Exportar base…** y guarda el `.db`; llévalo a la otra (USB, OneDrive, correo) y ahí pulsa **Importar base…**.
- **Fusionar** suma lo que falta sin borrar nada de lo que ya hay. Antes de guardar ves qué se agrega y cada diferencia (calificaciones o equipos distintos, participaciones repetidas, personas que podrían ser la misma) para elegir; por omisión se conserva lo de la computadora donde importas.
- **Reemplazar todo** deja la base igual a la del archivo.
- En ambos casos se crea un respaldo antes y **Deshacer importación** lo restaura.

### Cursos
- Arriba: **Crear**, **Importar lista** y **Eliminar**.
- Centro: cards con nombre del curso, grupo y semestre.
- Menú de cada card: Editar, Archivar, Eliminar.

### Curso
Vista parecida a la tabla de Excel, con registro rápido arriba.

```
[ Alumno: cuenta o nombre ▾ ]  [ Décimas ]  [ Guardar ]
✓ NOMBRE DEL ALUMNO  +10 → total 60                [Deshacer]

 No. | Cuenta | Nombre | Décimas | Última participación
```

- El alumno se busca por **número de cuenta o nombre** (autocompletado tolerante a mayúsculas, acentos y espacios).
- Si existe: se suman las décimas y se muestra nombre, décimas sumadas y total. Un clic en una fila de la tabla también elige al alumno.
- El total **nunca baja de 0**: si restas más de lo que tiene, queda en 0 y la app lo avisa.
- Si no existe: se ofrece crearlo en el curso como **regular** u **oyente**.
- Todo el flujo es operable con teclado.
- Doble clic en un alumno abre su historial.
- **Eliminar alumno:** solo para **oyentes y visitantes**, con el botón «－ Eliminar alumno» (con uno elegido en la tabla) o con clic derecho sobre su fila. A un oyente se le quita del curso con sus participaciones, calificaciones, tareas, proyecto y equipo (y se borra del sistema si no está en otro curso); a un visitante solo se le quita la visita y su equipo en este grupo, sin tocar nada de su grupo de origen. Pide confirmación con lo que se perderá y se puede **deshacer** desde la franja hasta tu siguiente captura. A un alumno regular (de la lista de inscripción) no se le puede eliminar.
- **Visitantes:** en «Agregar alumno» elige «¿Es de otro grupo de esta materia? Agregar como visitante…», busca por cuenta o nombre entre los regulares de los otros grupos de la materia y, si hay varios, elige. En la tabla aparece como «(visitante · grupo de origen)» y la franja avisa en qué grupo se guardó lo que captures. Un examen solo se le puede capturar si el grupo de origen tiene uno con el mismo nombre. Un alumno está en un solo equipo entre su grupo de origen y los que visita. Si eliminas el curso de origen, sus visitas desaparecen de los otros grupos (el diálogo te dice cuántas).

**Exámenes y tareas.** El selector `[Participación | Examen | Tareas | Proyecto]` (tecla **F2**, recorre los cuatro modos) cambia el registro rápido a calificaciones: eliges el examen (o creas uno con «＋ Nuevo»; «⋯» renombra o elimina), escribes cuenta o nombre y la calificación. Si el alumno ya tenía nota, la app avisa «Ya tiene X; se cambiará a Y» y pide confirmar; «Deshacer» la restaura. La tabla gana una columna «Examen - <nombre>» por examen. En modo **Tareas** capturas la calificación de tareas de cada alumno (con la misma advertencia de reemplazo y «Deshacer»); la tabla muestra la columna «Tareas».

**Equipos para el proyecto final.** El modo **Proyecto** agrupa la tabla por equipo, con una fila de encabezado coloreada («Equipo 2 · 3 alumnos · Los Cuervos · Sistema de riego») y dos tonos que se alternan; los alumnos sin equipo quedan al final. Con **«Formar equipos»** haces clic en los alumnos (otro clic los quita) y pulsas «Crear equipo con N alumnos»: un diálogo te pide, si quieres, el nombre del equipo y el título de su proyecto (doble clic en el equipo para editarlos después); «Sacar de equipo» los saca de su equipo. Con clic derecho también puedes **sacar** a un alumno o **agregarlo a un equipo ya formado** (submenú con la lista). Todo se puede deshacer, y un alumno que ya tiene equipo nunca se mueve sin que lo saques antes.

**Calificar el proyecto final.** En el modo Proyecto, con «Formar equipos» apagado, escribes la cuenta o el nombre de un alumno, o **«equipo N»** para todo un equipo (también puedes hacer clic en la fila del equipo o usar «Usar equipo N»), y la calificación del proyecto. Calificar a un equipo **copia la misma nota a cada miembro**; después puedes corregir a cada alumno por separado y nada se sincroniza solo. Si algún miembro ya tenía otra nota, la app avisa («2 de 4 miembros ya tienen calificación») y pide confirmar; «Deshacer» devuelve las notas previas de todos. Sin captura vale 0, no tiene tope y es independiente de décimas, exámenes y tareas.

**Calificación final.** La columna **Final** (0–100, entera) y **Final /10** de la tabla suman, ponderados, cuatro componentes: las **participaciones** (cada décima vale 10 puntos), el **promedio de exámenes**, las **tareas** y el **proyecto final**. Las ponderaciones son por curso y se cambian con **«⚖ Ponderaciones»**: cada una va de 0 a 100 % y la suma puede pasar de 100 % (el excedente son puntos extra); el diálogo muestra la suma en vivo. Por omisión pesan 10 % las participaciones, 20 % las tareas y 40 % el proyecto, y los exámenes **0 % hasta que les asignas su ponderación**: al crear un examen la app te la pide (sugiere 30 %; si cancelas, te lo recuerda). Lo no capturado vale 0. La final nunca se guarda: se recalcula siempre y solo se redondea (la mitad hacia arriba) al mostrar o exportar.

**Importar tareas desde un archivo.** Con «⬆ Importar tareas» eliges el `.xlsx` o `.csv` que descargas de la otra plataforma. La app reconoce a cada alumno por su nombre (o por número de cuenta si el archivo trae una columna «Cuenta») y te muestra una vista previa: qué columna importar (por omisión la del promedio), quién cambia («antes → después»), qué coincidencias son dudosas (solo se aplican si las marcas) y qué filas se omiten. Nunca crea alumnos ni toca a quienes el archivo no menciona. Al aplicar, puedes **deshacer la importación** completa.

### Exportar
Desde la pantalla Curso: **Excel** (hoja «Resumen» con No., Cuenta, Nombre, Décimas, Tareas, Equipo, Proyecto, una columna por examen y «Promedio exámenes» si el curso tiene exámenes, Calificación final, Participaciones, Última, y hoja opcional «Participaciones» con el detalle; el Excel indica las ponderaciones usadas) o **CSV** (resumen). Los oyentes y visitantes se excluyen salvo que marques «Incluir oyentes y visitantes» (la columna «Tipo» los distingue; los números y la final del visitante son los de su grupo de origen).

### Historial de un alumno
- Tarjetas de resumen (total, número de registros, última participación y **calificación final** con su equivalencia de 0 a 10) y una línea con el **desglose** de la final por componente.
- Cada fila muestra el efecto real y el total acumulado; ⚑ marca los registros donde se aplicó el mínimo de 0.
- Selector de curso (un alumno puede estar en varios).
- Tabla de participaciones con fecha, décimas y nota; cada fila se puede editar o borrar.
- Agregar participaciones con fecha anterior.
- Sección **Exámenes, tareas y proyecto**: la fila «Tareas», la fila «Proyecto final» (con su equipo) y la calificación de cada examen del curso (0 si no se ha capturado); se puede calificar, corregir o quitar.
- Convertir oyente en regular.

## Importación de listas

La lista de inscripción (Excel de la facultad) trae el ciclo, carrera, materia y grupo en el encabezado, y una tabla `No. | No. Cuenta | Nombre`. Al importarla se crea el curso, los alumnos (por número de cuenta) y sus inscripciones. Reimportar no duplica alumnos ni borra participaciones.

## Cómo ejecutar

```bash
.venv/Scripts/python.exe main.py            # abre la aplicación
.venv/Scripts/python.exe -m pytest          # corre las pruebas
```

Si recreas el entorno en otra máquina: `python -m venv .venv` y luego `.venv/Scripts/python.exe -m pip install -r requirements.txt`.
La base de datos se guarda en `data/participaciones.db`; al cerrar la aplicación se crea un respaldo en `data/backups/` (se conservan los 10 más recientes).

## Generar el ejecutable (Windows)

```bash
powershell -ExecutionPolicy Bypass -File scripts/construir_exe.ps1
```

Crea `dist/Participaciones/Participaciones.exe` (≈46 MB, tarda ~30 s). Para usarla en otra computadora copia **la carpeta completa** `dist/Participaciones/`; el `.exe` solo no funciona. No requiere instalar Python.

- **Datos del ejecutable:** se guardan en `%LOCALAPPDATA%\Participaciones\data` (base de datos y respaldos), fuera de la carpeta de la app: reconstruir, mover o borrar `dist/` nunca toca tus datos. La versión de desarrollo (`python main.py`) usa `data/` del proyecto, así que **son dos bases independientes**. Para pasar datos de una a otra usa **Configuración → Exportar base… / Importar base…**. La ruta exacta aparece en **Configuración**.
- **Ícono:** `assets/icon/FES ARAGON.png` es la fuente; `tools/crear_icono.py` genera `assets/icon/app.ico` (el script de construcción lo ejecuta solo).
- **Actualizar de versión:** la primera vez que se abre una base de la 1.6.x o anterior, la app la actualiza sola (agrega los visitantes) y deja una copia `antes_migracion_AAAAMMDD_HHMMSS.db` en la misma carpeta de datos; después esa base ya no la abre una versión anterior.
- **Receta:** `participaciones.spec`. Dependencias solo para compilar: `requirements-build.txt`.
- Si el proyecto está en OneDrive, el script borra `dist/` y manda los temporales fuera de OneDrive para evitar errores de "Acceso denegado" por la sincronización.

## Estructura del proyecto

```
Participaciones/
├── README.md
├── CLAUDE.md              # reglas y convenciones del proyecto
├── core/                  # lógica, sin dependencia de la interfaz (incluye rutas.py y version.py)
│   ├── models.py
│   ├── repository.py      # único lugar con SQL
│   └── services.py
├── importers/
│   ├── lista_aragon.py
│   └── calificaciones_plataforma.py
├── ui_desktop/
├── assets/icon/           # logo (PNG) e ícono de la app (.ico)
├── scripts/               # construir_exe.ps1
├── tools/                 # crear_icono.py
├── participaciones.spec   # receta de PyInstaller
├── tests/
├── data/                  # participaciones.db (no versionar)
└── main.py
```

## Plan de trabajo

1. ✅ `core`: modelos, base de datos y servicios.
2. ✅ Importador de la lista de inscripción (probado con un archivo real).
3. ✅ Pruebas (`.venv\Scripts\python.exe -m pytest`).
4. Interfaz de escritorio, por pantallas:
   - ✅ Principal (panel lateral), Cursos y Configuración
   - ✅ Curso (tabla + registro rápido)
   - ✅ Historial de un alumno (doble clic en una fila del curso)
5b. ✅ Exportar/importar la base entre máquinas (Configuración).
5c. ✅ Eliminar alumnos oyentes de un curso (con deshacer).
5d. ✅ Visitantes de otro grupo de la misma materia (datos en el grupo de origen).
5. ✅ Exportar a Excel/CSV (botón «Exportar» en la pantalla Curso) y respaldos (automático al cerrar y manual desde Configuración).

## Mejoras futuras

- Gráfica de evolución acumulada de décimas en el historial del alumno.
- Sección global **Alumnos** (directorio).
- Importar el Excel anterior (`Participaciones.xlsm`), cruzando por nombre.
- Interfaz web (`ui_web/`) reutilizando `core/`.
- Identificador por evento en las participaciones para fusionar bases sin ambigüedad en los duplicados.
