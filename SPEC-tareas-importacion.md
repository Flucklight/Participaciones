# Spec: Importar calificaciones de tareas (módulo `tareas-importacion`)

Estado: **BORRADOR; respuestas de la persona incorporadas, falta aprobación explícita** (sin código ni cambios a `CLAUDE.md` todavía). Índice: `MAPA-tareas.md`. Depende de `SPEC-tareas.md` (módulo `tareas`, ya aprobado): este módulo solo guarda a través de su servicio.

## Objetivo

El profesor descarga de otra plataforma un archivo con las calificaciones de tareas de todo el grupo y quiere **actualizar de una vez** la calificación de tareas de cada alumno del curso, en lugar de capturarla alumno por alumno. Se importa el valor ya promediado; la app no calcula nada.

Usuario: el profesor, varias veces por semestre, cada vez que la plataforma actualiza los promedios.

Se construye **después** de `tareas`.

Decisiones ya tomadas con el usuario:
- Acepta **.xlsx y .csv**.
- **Vista previa y confirmar**: nada se guarda hasta que el profesor aprueba el resumen.
- Reemplazar el valor anterior (una sola calificación vigente por alumno, sin tope, ≥ 0).

## Lo que muestra el archivo de muestra

Revisé `Calificaciones LENGUAJES FORMALES-AUTOMATAS Grupo_ 1509 (2027-I) 22-10-2026.xlsx` (datos reales, **no se versiona** ni se copia a código, pruebas o commits; `.gitignore` ya excluye `*.xlsx`):

| Parte | Contenido |
|---|---|
| Hoja | Una sola, «Sheet0» (60 alumnos, sin nombres repetidos) |
| A1, A2 | Materia y `Grupo: 1509 (2027-I)` |
| Filas 1–3 | Por cada tarea: fecha de entrega, «Tarea N: nombre» y puntaje máximo (100) |
| Fila 5 | «Media de la clase» (no es un alumno) |
| Filas 6 en adelante | Un alumno por fila |
| Col. A / B | **Apellidos** / **nombres** (separados) |
| Col. C | Correo institucional `@aragon.unam.mx` |
| Col. D (sin encabezado) | Fracción 0–1 que calcula la plataforma: suma entregada ÷ suma de máximos |
| Col. E, F, G… | Una columna por tarea, de 0 a 100 |
| Col. H (sin encabezado) | Fórmula `=AVERAGE(E:G)` en escala 0–100: **el promedio de las tareas** (coincide en las 60 filas; D = H/100) |

### Muestra en CSV

`INTELIGENCIA_ARTIFICIAL.csv` (también datos reales, **no se versiona**; `.gitignore` ya excluye `*.csv`). **No tiene la misma disposición que el `.xlsx`:**

| Parte | CSV | (xlsx, para comparar) |
|---|---|---|
| Codificación / separador | UTF-8 sin BOM, coma, saltos CRLF | — |
| Fila 1 | Encabezados: `Apellidos`, `Nombre`, `Dirección de correo`, `Tarea N: …` | Materia en A1 y grupo en A2 |
| Fila 2 / 3 | `Fecha` / `Puntos` (fecha de entrega y máximo de cada tarea) | Fecha, nombre y máximo en las filas 1–3 |
| Alumnos | Desde la fila 4, sin fila «Media de la clase» | Desde la fila 6, con «Media de la clase» en la 5 |
| Col. A / B / C | Apellidos / nombres / correo | Igual |
| Última columna | **Sin encabezado**: promedio 0–100 de las tareas (una columna menos que el xlsx: no hay la fracción 0–1) | Col. H |
| Datos del curso | **No trae materia ni grupo** | Sí (A1, A2) |

Conclusión: el importador **no puede depender de posiciones fijas de fila**. Debe localizar a los alumnos por su forma (apellidos y nombres no vacíos, correo con «@» en la tercera columna y al menos un valor numérico) y tomar los rótulos de columna de las filas de encabezado que haya, sea cual sea su orden.

**Hallazgos que cambian el diseño:**
1. **El archivo no trae número de cuenta**, así que no se puede identificar al alumno por cuenta como habíamos supuesto. Trae apellidos, nombres y correo.
2. Hay **dos columnas candidatas** al «promedio» (D en 0–1 y H en 0–100) y ninguna tiene encabezado.
3. La columna H es una fórmula: al leer el archivo se toma el **valor calculado guardado**; si el archivo se guardó sin calcular, la celda llega vacía y debe avisarse.

## Supuestos (corrígeme ahora o procedo con ellos)

1. **Identificación por nombre** (decisión de la persona por ahora; ver supuesto 1b). Se compara «apellidos + nombres» del archivo contra `nombre_completo` del alumno del curso (que guarda apellidos primero, como la lista de inscripción), con la normalización del proyecto (sin acentos, mayúsculas ni espacios repetidos).
   - Coincidencia única exacta → se aplica.
   - Sin coincidencia exacta pero con una única coincidencia por palabras (mismo conjunto de palabras en otro orden, o uno contenido en el otro) → **dudosa**: se lista con casilla para confirmarla; nunca se aplica sin confirmar.
   - Varias coincidencias, o sin ninguna → **se omite** y se lista en la vista previa. **Nunca se crean alumnos** desde este archivo.
   - Nombre repetido dentro del archivo → se omite y se avisa (ambiguo).
1b. **Preparado para ser más preciso:** si el archivo trae una columna de **número de cuenta** (encabezado «Cuenta», «No. Cuenta» o similar, con valores de dígitos), la identificación usa la cuenta con prioridad y el nombre queda de respaldo. Así, si más adelante la persona agrega esa columna al archivo, el modelo gana precisión sin cambiar la app. Sin esa columna rige el supuesto 1.
2. **Columna a importar elegida por el profesor** (confirmado: la del promedio, H en el xlsx y la última en el csv). El diálogo lista las columnas numéricas del archivo con su rótulo (el de la tarea, o «Columna H (sin encabezado)») y los primeros valores como muestra; el profesor elige. La opción por defecto es la **numérica de más a la derecha**. Se importa el valor tal cual, sin convertir de escala.
3. Los alumnos del curso que **no aparecen en el archivo no se tocan** (conservan su calificación o su 0).
4. Al confirmar, **cada valor reemplaza** al anterior sin pedir una confirmación por alumno (la vista previa ya mostró «antes → después»). La fecha de captura es hoy.
5. **Deshacer la importación:** tras aplicar, la franja ofrece «Deshacer importación», que restaura los valores anteriores (o elimina los que no existían). Solo mientras no se haga otra captura ni se salga de la pantalla.
6. **Verificación de grupo (solo si el archivo la trae):** el xlsx trae `Grupo: <grupo> (<ciclo>)`; si no coincide con el curso abierto, la vista previa avisa y pide confirmar. El csv no trae datos del curso: no hay verificación y el resumen muestra siempre el nombre del curso al que se aplicará, para que se vea a cuál se importa.
7. Los **oyentes** del curso también pueden recibir calificación por esta vía (se identifican igual por nombre).
8. Una fila de alumno es la que tiene apellidos y nombres no vacíos, un correo con «@» en la tercera columna (sin exigir que traiga números: un alumno sin calificaciones es «sin dato»); «Media de la clase», `Fecha`, `Puntos` y filas vacías se ignoran. Una celda vacía en la columna elegida se informa («sin dato») y **no cambia** la calificación existente.
9. Valor negativo, no numérico o no finito en la columna elegida → fila omitida con el motivo (no detiene la importación).

## Vista previa (diálogo «Importar tareas»)

```
Archivo: Calificaciones … 22-10-2026.xlsx     Grupo en archivo: 1509 (2027-I)  ✓ coincide
Columna a importar: [ Columna H (sin encabezado) ▼ ]   muestra: 33.3, 65, 65, 63.3…

  60 alumnos en el archivo
  54 coinciden y se actualizan   (31 cambian · 23 quedan igual)
   3 coincidencias dudosas  → [ ] confirmar cada una
   3 no coinciden con nadie del curso → se omiten (lista)
   2 alumnos del curso no aparecen en el archivo → no se tocan

  Cambios (antes → después): … tabla desplazable …
                                           [Cancelar]  [Aplicar 54 cambios]
```

## Interfaz

- Botón **«⬆  Importar tareas»** en el encabezado de la pantalla Curso, junto a «Exportar» y «Agregar alumno».
- Selector de archivo para `.xlsx` y `.csv`.
- Tras aplicar: franja «✓ Tareas importadas: N actualizadas, M omitidas» con **Deshacer importación**; la tabla del curso se recarga.
- Operable con teclado; el foco vuelve al campo de alumno.

## Comandos

```
Pruebas:    .venv\Scripts\python.exe -m pytest
Una prueba: .venv\Scripts\python.exe -m pytest tests/test_importar_tareas.py -q
Ejecutar:   .venv\Scripts\python.exe main.py
Muestra real (opcional): $env:PLATAFORMA_REAL = "<ruta al .xlsx>"; $env:PLATAFORMA_REAL_CSV = "<ruta al .csv>"   # esas pruebas se omiten si no existen
```

## Estructura (archivos a tocar o crear)

```
importers/calificaciones_plataforma.py → leer .xlsx/.csv: columnas numéricas con su rótulo, filas de alumnos, grupo/ciclo
                                          del encabezado. Sin base de datos ni UI. Errores como ErrorImportacion.
core/models.py            → ArchivoCalificaciones (columnas + filas), FilaCalificacion, VistaPreviaTareas, ResultadoImportacionTareas
core/services.py          → previsualizar_importacion_tareas(curso_id, archivo, columna), importar_tareas(...,
                            confirmadas), deshacer_importacion_tareas(...)
core/repository.py        → solo el SQL que haga falta (p. ej. leer calificaciones del curso de una vez)
ui_desktop/dialogos_tareas.py → DialogoImportarTareas (columna, vista previa, dudosas)
ui_desktop/vista_curso.py → botón y franja con «Deshacer importación»
tests/conftest.py         → crear_excel_plataforma(...) con datos ficticios
tests/test_importar_tareas.py, test_ui_curso.py (ampliar)
CLAUDE.md, README.md      → regla R15 y pantalla; subir core/version.py
```

## Estilo de código

Español sin acentos ni ñ; el importador no depende de la base ni de la UI (como `importers/lista_aragon.py`); toda regla de negocio en `core/services.py`:

```python
@dataclass
class FilaCalificacion:
    """Una fila de alumno del archivo de la plataforma."""

    apellidos: str
    nombres: str
    valores: dict[str, float | None]  # por rótulo de columna numérica

    @property
    def nombre_completo(self) -> str:
        return f"{self.apellidos} {self.nombres}"
```

## Estrategia de pruebas

pytest, **solo datos ficticios** (cuentas `100000001`, nombres inventados). Un helper en `conftest.py` genera un `.xlsx` con la misma estructura que la plataforma; **nunca** se copia el archivo real ni sus nombres.
- Importador: las **dos disposiciones** (la del xlsx y la del csv) generadas con datos ficticios; encuentra el bloque de encabezado y las filas de alumnos sin depender de posiciones fijas; ignora «Media de la clase» y filas vacías; lista las columnas numéricas con su rótulo (incluida la que no tiene encabezado); lee grupo y ciclo; `.csv` con coma y con punto y coma, con y sin BOM; archivo que no es de la plataforma o sin alumnos → error claro; celda de fórmula sin valor guardado → «sin dato».
- Servicio: coincidencia exacta; dudosa solo se aplica si se confirma; ambigua y sin coincidencia se omiten sin crear alumnos; nombre repetido en el archivo; valores negativos/no numéricos omitidos con motivo; celda vacía no cambia lo existente; alumnos del curso fuera del archivo intactos; contadores de la vista previa (cambian / quedan igual); deshacer restaura anteriores y elimina las nuevas; no altera décimas ni exámenes.
- UI (humo): el botón abre el diálogo; elegir columna actualiza la vista previa; confirmar dudosas; aplicar y deshacer; cancelar no guarda nada.
- Muestras reales: pruebas opcionales con `PLATAFORMA_REAL` (xlsx) y `PLATAFORMA_REAL_CSV` (csv); se omiten sin la variable.
- Regresión: la suite completa sigue pasando.

## Límites

- **Siempre:** vista previa antes de guardar; `.venv\Scripts\python.exe -m pytest` antes de cada commit; datos reales fuera de código, pruebas, README y commits; reutilizar el servicio de `tareas` para validar y guardar; SQL solo en `core/repository.py`; el importador sin acceso a la base.
- **Preguntar antes:** guardar el correo u otro dato nuevo del alumno (cambia el modelo); crear alumnos desde el archivo; añadir dependencias; cambiar la regla de identificación.
- **Nunca:** aplicar una coincidencia dudosa o ambigua sin confirmación; crear alumnos automáticamente; modificar alumnos que no están en el archivo; versionar el archivo de la plataforma.

## Criterios de éxito

1. Con el archivo de muestra y un curso con esos alumnos, el diálogo muestra el resumen correcto (coinciden, cambian, quedan igual, no coinciden) y **no se guarda nada** hasta pulsar «Aplicar».
2. Elegir la columna H importa valores como `33.33`, `65`, `66.67` tal cual; elegir otra columna cambia la vista previa al instante.
3. Una coincidencia dudosa solo se aplica si se marca; una ambigua o inexistente se omite y queda en la lista.
4. Un alumno del curso que no está en el archivo conserva su calificación.
5. «Deshacer importación» deja la tabla exactamente como estaba antes.
6. Un archivo sin formato válido, o que se pueda abrir pero sin alumnos, da un mensaje claro y no cambia nada.
7. Décimas, exámenes y su promedio se comportan exactamente como antes.
8. La suite completa pasa; con `PLATAFORMA_REAL` y `PLATAFORMA_REAL_CSV` definidas, las pruebas con las muestras reales también.

## Preguntas abiertas

Ninguna. Respuestas de la persona: (1) la identificación **por nombre** es la estrategia por ahora; (2) importar la columna del promedio (H en el xlsx, la última en el csv), con elección en el diálogo; (3) el csv de muestra ya está en la carpeta del proyecto y tiene otra disposición que el xlsx (reflejado arriba). Los supuestos 3–9 se toman como aceptados. La persona puede modificar el archivo más adelante (p. ej. agregar una columna de cuenta): el supuesto 1b ya lo contempla.
