# Spec: Equipos para el proyecto final (módulo `equipos`)

Estado: **BORRADOR; las 4 decisiones de diseño ya las respondió la persona, falta la aprobación explícita** (sin código ni cambios a `CLAUDE.md` todavía). Índice: `MAPA-proyecto.md`. Se construye **antes** de `proyecto`.

## Objetivo

El proyecto final lo entregan equipos. El profesor necesita **formar equipos** dentro de un curso, ver a los alumnos agrupados por equipo y poder **separar** a alguien de su equipo. Esta spec cubre solo los equipos y la sección «Proyecto» donde se manejan; calificar viene en `SPEC-proyecto.md`.

Usuario: el profesor, al inicio del proyecto (formar) y cuando hay cambios (separar).

Decisiones ya tomadas con la persona:
- Formar equipos **solo en la sección «Proyecto»**: un botón «Formar equipos» activa un modo en el que se seleccionan **varios alumnos** y se crea un equipo con un **número incremental** por curso.
- Al crear equipos, **solo en esta sección** la tabla se ordena por número de equipo (agrupados) y, dentro del equipo, por nombre.
- En ese modo, **clic derecho → «Separar»** saca a un miembro de su equipo.
- El número de un equipo **nunca se reutiliza**, aunque se quede sin miembros.
- Si entre los seleccionados hay alguien que **ya tiene equipo**, se **rechaza y se avisa** quién es; hay que separarlo antes. Nunca se mueve a nadie sin que lo pidas.

## Supuestos (corrígeme ahora o procedo con ellos)

1. **Un alumno pertenece a un solo equipo** por curso. Los equipos son por curso (el equipo 1 de un curso no tiene relación con el de otro).
2. **Un equipo puede tener desde 1 alumno** (decisión de la persona: hay proyectos individuales). Si separas a los demás, el equipo sigue existiendo con los que queden; uno sin miembros desaparece de la vista pero **su número se conserva como usado**.
3. Los **oyentes** también pueden estar en equipos y se muestran en la tabla como siempre (con «Mostrar oyentes» activo).
4. **Cuarto modo «Proyecto»** en el selector `[Participación | Examen | Tareas | Proyecto]`; **F2 recorre los cuatro** en ciclo. Color propio: **ciruela/magenta** (distinto del azul, índigo, verde azulado y ámbar de avisos; se define en `tema.py`).
5. En modo «Proyecto» la tabla agrega una columna **«Equipo»** («Equipo 3» o vacío) y se ordena por equipo y nombre; **los alumnos sin equipo van al final**, ordenados por nombre. En los demás modos la tabla conserva su orden y no cambia nada. Se puede ordenar por otra columna con un clic en el encabezado, como siempre.
6. **Seleccionar:** con «Formar equipos» activo, la tabla permite selección múltiple (clic, Ctrl+clic y Mayús+clic); el clic ya **no** carga al alumno en el campo de registro. Al activar el modo la franja explica cómo usarlo; al desactivarlo (o cambiar de modo) la selección se limpia.
7. **Crear:** una barra muestra «N seleccionados» y el botón «Crear equipo con N alumnos» (o «con 1 alumno»; deshabilitado sin selección). Tras crear, la franja dice «Equipo 3 formado con N alumnos» y los miembros quedan resaltados. «Deshacer» elimina el equipo recién creado (y libera a sus miembros); su número no se reutiliza.
8. **Separar:** clic derecho sobre una fila con equipo abre el menú «Separar del equipo N». Si hay varias filas seleccionadas con equipo, separa a todas. Es inmediato (no destruye datos) y se puede deshacer. Solo está disponible con «Formar equipos» activo.
9. Las calificaciones **no se tocan** al formar o separar equipos (eso es de `proyecto`).
10. **Eliminar un curso** borra sus equipos; el diálogo no necesita contarlos (no son calificaciones).
11. Sin migración manual: las tablas nuevas se crean solas al abrir una base existente (`CREATE TABLE IF NOT EXISTS`).
12. **Color por equipo:** en modo «Proyecto» los equipos se distinguen con **dos colores de fondo que se alternan** de un equipo al siguiente **por orden de aparición** (no por paridad del número, para que dos equipos contiguos siempre difieran aunque haya huecos de numeración). Los alumnos sin equipo no llevan color. Los dos tonos son pares (claro, oscuro) en `tema.py`, con texto legible en ambos modos y sin chocar con la fila resaltada ni con la selección. **El diseño exacto se elige con pruebas visuales antes de implementarlo** (ver «Diseño del color de equipos»).

## Modelo de datos (cambio propuesto)

```
equipo(curso_id FK→curso ON DELETE CASCADE, numero INTEGER, PRIMARY KEY (curso_id, numero))
miembro_equipo(curso_id, alumno_id FK→alumno ON DELETE CASCADE, numero INTEGER,
               PRIMARY KEY (curso_id, alumno_id),
               FOREIGN KEY (curso_id, numero) REFERENCES equipo ON DELETE CASCADE)
```

- El siguiente número es `MAX(numero) + 1` sobre `equipo` del curso. Los equipos **no se borran al quedarse vacíos** (solo desaparecen de la vista): así el máximo histórico se conserva y el número no se reutiliza, **sin tocar la tabla `curso`**.
- Una sola fila por alumno y curso en `miembro_equipo`: garantiza «un solo equipo».

## Reglas de negocio nuevas (se agregarán a `CLAUDE.md` al implementar)

- **R16 Equipos de proyecto:** supuestos 1, 2, 7 y 8; número incremental por curso y nunca reutilizado; un alumno en un solo equipo; un equipo puede ser de 1 alumno; formar con alguien que ya tiene equipo se rechaza (se informa quién); separar y deshacer.
- Actualizar Modelo de datos, Interfaz (cuarto modo, columna «Equipo», formar, separar, F2 en cuatro modos) y paleta (ciruela = Proyecto).

## Interfaz

```
Modo Proyecto:
[ Participación ][ Examen ][ Tareas ][■ Proyecto ]      [ Formar equipos ○ ]

Con «Formar equipos» activo:
  3 seleccionados      [ Crear equipo con 3 alumnos ]

 No.  Cuenta      Nombre                  Décimas  Tareas  …  Equipo
  4   100000004   ACOSTA ORTEGA ELENA      …              …  Equipo 1
  9   100000009   PEREZ LUNA ANA           …              …  Equipo 1
  2   100000002   GARCIA LOPEZ ANA         …              …  Equipo 2
  …                                                          (sin equipo, al final)
 clic derecho sobre una fila con equipo ▸ «Separar del equipo 1»
```

- En `equipos` el modo «Proyecto» **no tiene campo de registro** (llega con `proyecto`): muestra el botón «Formar equipos», la barra de selección y la tabla agrupada, con una franja de ayuda («Activa «Formar equipos» para armar los equipos del proyecto»).
- Colores solo desde `ui_desktop/tema.py` (nuevo par `COLOR_PROYECTO` y su hover).

## Diseño del color de equipos (por decidir con pruebas)

Se prepararán capturas de la tabla (modo claro y oscuro, datos ficticios) con estas variantes para que la persona elija:

| Variante | Idea | Ventaja | Costo |
|---|---|---|---|
| A. Bandas suaves | El fondo de las filas del equipo alterna entre dos tonos tenues (azul-gris y ciruela pálido) | Discreta; la tabla se lee igual que ahora | Ninguno |
| B. Bandas marcadas + texto de color | Tonos más intensos y el texto de la fila toma el color del equipo | El cambio de equipo salta a la vista | Un poco más cargada; el texto de color puede cansar en tablas largas |
| C. Encabezado de grupo | Antes de cada equipo, una fila «Equipo 2 · 2 alumnos» coloreada, y las filas del equipo con tono suave | El equipo se ve como un bloque con su tamaño | Agrega filas que no son alumnos: hay que excluirlas de la selección, el conteo y el ordenamiento |

Las capturas de prueba (claro y oscuro) se hicieron con datos ficticios antes de implementar.

Criterios para decidir: legible en claro y oscuro, no confundirse con la selección (azul) ni con el resaltado verde de «recién registrado», y que se note el cambio de equipo sin recargar la vista.

## Comandos

```
Pruebas:    .venv\Scripts\python.exe -m pytest
Una prueba: .venv\Scripts\python.exe -m pytest tests/test_equipos.py -q
Ejecutar:   .venv\Scripts\python.exe main.py
Empaquetar: powershell -ExecutionPolicy Bypass -File scripts\construir_exe.ps1   (subir core/version.py antes)
```

## Estructura (archivos a tocar o crear)

```
core/database.py        → tablas equipo y miembro_equipo
core/models.py          → Equipo, ResultadoEquipo; ResumenAlumno gana `equipo: int | None`
core/repository.py      → todo el SQL de equipos (siguiente número, miembros, alta, baja, equipo por alumno)
core/services.py        → formar_equipo, separar_de_equipo, deshacer_equipo, equipos_del_curso, equipo_de;
                          `resumen_curso` trae el equipo de cada alumno
ui_desktop/tema.py      → color del modo Proyecto y los dos tonos alternados de equipo
ui_desktop/vista_curso.py → cuarto modo, F2 en ciclo de cuatro, botón «Formar equipos», selección múltiple,
                            barra «N seleccionados», menú contextual «Separar», orden y columna «Equipo»
tests/test_equipos.py, test_ui_curso.py (ampliar), test_ui_equipos.py (nuevo)
CLAUDE.md, README.md    → R16 y pantalla; subir core/version.py
```

## Estilo de código

Español sin acentos ni ñ; el servicio decide, la UI solo muestra; errores como `ErrorDominio`:

```python
@dataclass
class ResultadoEquipo:
    estado: EstadoEquipo  # FORMADO | YA_TIENEN_EQUIPO
    equipo: int | None = None
    miembros: list[Alumno] = field(default_factory=list)
    con_equipo: list[tuple[Alumno, int]] = field(default_factory=list)  # quién ya tenía equipo y cuál
```

## Estrategia de pruebas

pytest, **solo datos ficticios** (`100000001`, nombres inventados).
- Esquema: tablas creadas en base nueva y existente sin perder datos; PK impide dos equipos para el mismo alumno; cascada al borrar curso o alumno.
- Servicio: formar con 1 o más alumnos; rechazar una lista vacía o con alumnos no inscritos; numeración 1, 2, 3 por curso e independiente entre cursos; **el número no se reutiliza** tras separar a todos; rechazar si alguien ya tiene equipo (informa quién y cuál, no crea ni mueve nada); separar uno o varios; separar a quien no tiene equipo no falla ni cambia nada; deshacer formar libera a los miembros; `resumen_curso` trae `equipo`.
- Independencia: décimas, exámenes, tareas y sus promedios no cambian.
- UI (humo): el selector pasa a cuatro modos (clic y F2 en ciclo); «Formar equipos» activa la selección múltiple y desactiva el clic que carga al alumno; crear con selección válida/inválida; orden por equipo con los sin equipo al final y en otros modos el orden no cambia; menú «Separar» (una y varias filas); deshacer; cambiar de modo limpia la selección.
- Regresión: la suite completa (371 pruebas) sigue pasando; las pruebas de F2 y del selector se ajustan solo donde el ciclo pase de tres a cuatro modos.

## Límites

- **Siempre:** correr `.venv\Scripts\python.exe -m pytest` antes de cada commit; SQL solo en `core/repository.py`; `core/` sin importar `ui_*`; actualizar `CLAUDE.md` y `README.md` en el mismo cambio; datos ficticios; colores solo en `tema.py`.
- **Preguntar antes:** cambiar tablas existentes (incluida `curso`); añadir dependencias; mover automáticamente a alguien de un equipo a otro; cambiar el orden de la tabla fuera de la sección «Proyecto».
- **Nunca:** reutilizar el número de un equipo; poner a un alumno en dos equipos; mover o separar a alguien sin acción explícita; tocar calificaciones al formar o separar; copiar datos reales de alumnos.

## Criterios de éxito

1. En modo «Proyecto» con «Formar equipos» activo, seleccionar 3 alumnos (Ctrl/Mayús) y pulsar «Crear equipo con 3 alumnos» los asigna al equipo 1; el siguiente equipo es el 2.
2. La tabla muestra «Equipo» y se agrupa por número y nombre, con los alumnos sin equipo al final; en los otros tres modos la tabla se ve igual que antes.
3. Incluir a alguien que ya tiene equipo rechaza la operación, dice quién y en cuál equipo, y no cambia nada.
4. Clic derecho en un miembro → «Separar del equipo N» lo deja sin equipo; si se separa a todos, el equipo desaparece y el siguiente número creado sigue sin reutilizar el suyo.
5. «Deshacer» revierte la última creación o separación.
6. Sin alumnos seleccionados el botón de crear está deshabilitado; con 1 solo se puede formar un equipo de 1 alumno.
7. Décimas, exámenes, tareas y sus promedios se comportan exactamente como antes.
8. Una base `.db` existente abre sin errores y conserva todos sus datos.
9. La suite completa pasa.

## Preguntas abiertas

Ninguna bloqueante. Las 4 decisiones de diseño ya están respondidas. Los supuestos 1–11 se toman como aceptados salvo que los corrijas; los que más conviene que revises: el **diseño del color por equipo** (supuesto 12), que se decide con las capturas de la sección anterior. Respuestas de la persona: equipos de **1 integrante** permitidos; orden con los **sin equipo al final**, color **ciruela** para el modo y **dos colores alternados** para los equipos; sintaxis y sincronización de `proyecto` correctas; columna «Equipo» en la exportación necesaria.
