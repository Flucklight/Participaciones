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
inscripcion(curso_id, alumno_id, tipo: 'regular' | 'oyente')
participacion(id, curso_id, alumno_id, decimas, fecha, nota)
```

- El nombre se guarda **completo en un solo campo**, tal como viene en la lista de inscripción (`APELLIDO_PATERNO APELLIDO_MATERNO NOMBRES`). No se separan apellidos porque los compuestos (`DE LA PAZ`) no se pueden dividir de forma confiable.
- Las participaciones son **eventos con fecha**; el total de un alumno se calcula sumándolas.
- Los **oyentes** no tienen número de cuenta hasta que aparecen en una lista de inscripción.

## Pantallas

### Principal
Panel lateral izquierdo para navegar. Las vistas se muestran en el área central.
Secciones: **Cursos** y **Configuración** (respaldos y carpeta de datos).

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

### Exportar
Desde la pantalla Curso: **Excel** (hoja «Resumen» con No., Cuenta, Nombre, Décimas, Participaciones, Última, y hoja opcional «Participaciones» con el detalle) o **CSV** (resumen). Los oyentes se excluyen salvo que marques «Incluir oyentes».

### Historial de un alumno
- Tarjetas de resumen (total, número de registros, última participación).
- Cada fila muestra el efecto real y el total acumulado; ⚑ marca los registros donde se aplicó el mínimo de 0.
- Selector de curso (un alumno puede estar en varios).
- Tabla de participaciones con fecha, décimas y nota; cada fila se puede editar o borrar.
- Agregar participaciones con fecha anterior.
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

- **Datos del ejecutable:** se guardan en `%LOCALAPPDATA%\Participaciones\data` (base de datos y respaldos), fuera de la carpeta de la app: reconstruir, mover o borrar `dist/` nunca toca tus datos. La versión de desarrollo (`python main.py`) usa `data/` del proyecto, así que **son dos bases independientes**. Para pasar datos de una a otra, copia `participaciones.db` entre ambas carpetas con la app cerrada. La ruta exacta aparece en **Configuración**.
- **Ícono:** `assets/icon/FES ARAGON.png` es la fuente; `tools/crear_icono.py` genera `assets/icon/app.ico` (el script de construcción lo ejecuta solo).
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
│   └── lista_aragon.py
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
5. ✅ Exportar a Excel/CSV (botón «Exportar» en la pantalla Curso) y respaldos (automático al cerrar y manual desde Configuración).

## Mejoras futuras

- Gráfica de evolución acumulada de décimas en el historial del alumno.
- Sección global **Alumnos** (directorio).
- Importar el Excel anterior (`Participaciones.xlsm`), cruzando por nombre.
- Interfaz web (`ui_web/`) reutilizando `core/`.
