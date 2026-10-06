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
```

## Reglas de negocio

1. **CRUD de cursos:** crear, importar, ver, editar, **archivar** y **eliminar**. Archivar es reversible; eliminar es definitivo y exige confirmación explícita indicando cuántas participaciones se perderán.
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
   - El número de cuenta se guarda como **texto**; las fechas como fechas reales de Excel.
   - Si el archivo está abierto en Excel o la carpeta no existe, se informa con un mensaje claro (`ErrorDominio`), sin cerrar la app.

11. **Rutas y empaquetado** (`core/rutas.py`): nunca construir rutas con `__file__` fuera de ese módulo.
   - Desarrollo: datos en `data/` del proyecto. Empaquetada (`sys.frozen`): `%LOCALAPPDATA%\Participaciones\data`, **fuera** de la carpeta del `.exe`, para que reconstruir la app nunca borre datos.
   - Los archivos incluidos (íconos, etc.) se leen con `rutas.recurso(...)`; deben listarse en `datas` de `participaciones.spec`.
   - Se genera con `scripts/construir_exe.ps1`. La versión vive en `core/version.py` (súbela antes de cada entrega).

## Interfaz
- Panel lateral izquierdo con **Cursos** y **Configuración** (solo esas dos por ahora).
- **Cursos:** botones Crear / Importar / Eliminar arriba; cards (nombre, grupo, semestre) al centro; menú por card con Editar, Archivar, Eliminar.
- **Curso:** botones «Exportar» y «Agregar alumno» arriba; registro rápido + tabla de alumnos (No., Cuenta, Nombre, Décimas, Última); clic en una fila = elegir alumno. Operable con teclado; tras guardar, el foco vuelve al campo de alumno. Confirmación como franja no bloqueante, no como diálogo modal.
- **Historial de alumno:** tarjetas de resumen (total, participaciones, última), selector de curso, tabla editable de participaciones y alta con fecha anterior.
  - Se abre con doble clic en una fila de la pantalla Curso; «← Curso» regresa al curso seleccionado.
  - Cada fila muestra fecha, décimas capturadas, **efecto real** y **total acumulado** (los calcula `ServicioParticipaciones.historial_detallado`; la UI no calcula). Las filas donde se aplicó el mínimo de 0 se marcan con ⚑.
  - Editar y eliminar una participación recalculan el total; eliminar pide confirmación.
  - Un oyente muestra «Convertir en regular» (conserva el historial); «Editar alumno» corrige nombre y cuenta (la cuenta no puede repetirse).
- Fuera de alcance por ahora: gráfica de evolución, sección global Alumnos, usuarios/login, sincronización en la nube.

## Convenciones de código
- Python 3.11+, tipado con type hints, formato con `black`/`ruff` si se instalan.
- Dependencias mínimas: `customtkinter`, `openpyxl`, `pytest`.
- Cada regla de negocio nueva lleva su prueba en `tests/`.
- **Los tests solo usan datos ficticios** (nombres y cuentas inventados, p. ej. `100000001`). Nunca copiar nombres ni números de cuenta reales al código, tests, README ni commits.
- Para probar el importador con una lista real, define la variable de entorno `LISTA_REAL` con su ruta (`$env:LISTA_REAL = "..."`); esa prueba se omite si no existe.
- Datos reales de alumnos (Excel, `.db`) **no se versionan**; van en `data/` y en `.gitignore`.
- Respaldo automático del `.db` al cerrar la aplicación.

## Cómo trabajar con Claude
- Antes de cambiar el modelo de datos o una regla, proponer el cambio y actualizar este archivo.
- Mantener `README.md` coherente con este archivo cuando cambie el alcance.
