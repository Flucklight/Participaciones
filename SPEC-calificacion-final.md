# Spec: Calificación final por suma ponderada (módulo `calificacion-final`)

Estado: **APROBADA por la persona** (con sus respuestas a las 3 preguntas incorporadas); sin código ni cambios a `CLAUDE.md` todavía. Es un solo módulo (una capacidad: calcular, configurar y mostrar la calificación final), así que no hace falta mapa de capacidades. El nombre del archivo es `SPEC-calificacion-final.md` porque `SPEC.md` ya es la spec de exámenes, ya comiteada.

## Objetivo

Hasta ahora la app guarda por separado las décimas de participación, los exámenes (con su promedio), la calificación de tareas y la del proyecto final, y **no hay un número que los junte**. Se agrega la **calificación final**: una **suma ponderada** de esos cuatro componentes.

```
final = participaciones × 10 % + promedio de exámenes × 30 % + tareas × 20 % + proyecto × 40 %
```

Las ponderaciones **pueden sumar más de 100 %** (el excedente funciona como puntos extra) y son **editables por curso**. La calificación final se ve como columna en la tabla del curso, en el historial del alumno y en la exportación.

Usuario: el profesor, que hoy calcula esa suma a mano en otra hoja.

Decisiones ya tomadas con la persona:
- **Participaciones:** `1 décima = 10 puntos` (100 puntos = 10 décimas = calificación de 10). Los demás componentes entran **tal cual los capturó** (se asumen en escala de 0 a 100).
- **Resultado en escala de 0 a 100, redondeado** (se calcula con todos los decimales y solo se redondea al mostrar y exportar).
- **Ponderaciones editables por curso**; el componente de exámenes **arranca en 0 %** y, al crear el primer examen, se pide asignarle su ponderación. Las demás arrancan en 10 / 20 / 40.
- Aparece en: **columnas «Final» (0–100) y «Final /10» en la tabla del curso**, **historial del alumno** (con la equivalencia de 0 a 10) y **exportación** (solo la de 0 a 100).

## Supuestos (corrígeme ahora o procedo con ellos)

1. **Participaciones:** se usa el total ya calculado con piso de 0 (`total_con_piso`, R5) y **sin tope**: `puntos_participaciones = total × 10`. 12 décimas = 120 puntos (puntos extra, que ponderados suman al final).
2. **Exámenes:** se usa el promedio de exámenes (R13, `promedio_examenes`). Un examen sin calificación ya cuenta 0 dentro del promedio. **La ponderación de los exámenes arranca en 0 %** en cada curso (decisión de la persona): mientras no se asigne, los exámenes no pesan en la final; si el curso no tiene exámenes tampoco hay promedio y el componente aporta 0 (no se redistribuye su peso). Ver el supuesto 7b: al **crear el primer examen** la app pide asignar su ponderación.
3. **Tareas y proyecto:** se usan las calificaciones guardadas (R14 y R17), 0 si no hay captura.
4. **Fórmula exacta:** `final = Σ (componente × ponderación / 100)` con los cuatro componentes en escala de 0 a 100. No se limita a 100: con puntos extra o ponderaciones que suman más de 100 % el resultado puede pasar de 100.
5. **Redondeo:** al entero más cercano, **la mitad hacia arriba** (87.5 → 88, 87.49 → 87), solo al **mostrar y exportar**; internamente se conserva el valor exacto. La tabla ordena por el valor exacto.
6. **Ponderaciones por curso:** cuatro porcentajes, cada uno `>= 0` y `<= 100`, con decimales permitidos; **la suma puede ser cualquiera** (más de 100 % = puntos extra, menos de 100 % también se permite). Un curso sin ponderaciones guardadas usa **participaciones 10 %, exámenes 0 %, tareas 20 % y proyecto 40 %** (suma 70 % hasta que se asigne la de exámenes). Cambiar las ponderaciones recalcula de inmediato; **no se guardan finales** (R4: nunca guardar un total calculado).
7. **Pantalla de ponderaciones:** botón **«⚖ Ponderaciones»** en el encabezado de la pantalla Curso (junto a «Exportar», «Agregar alumno», «Importar tareas») abre un diálogo con los cuatro porcentajes, la **suma en vivo** («Suma: 110 % · 10 % de puntos extra» o «Suma: 90 % · faltan 10 %») y los botones «Restablecer» (10 / 0 / 20 / 40), «Guardar» y «Cancelar». Valores no numéricos, negativos, mayores de 100 o no finitos se rechazan dentro del diálogo.
7b. **Asignar la ponderación de exámenes:** al **crear un examen** en un curso cuya ponderación de exámenes es 0 %, justo después de crearlo se abre el diálogo de ponderaciones con el foco en «Exámenes» y **30 % sugerido** (se puede cambiar). «Guardar» la asigna; «Cancelar» no bloquea (el examen queda creado) y la franja recuerda «Los exámenes aún no pesan en la calificación final: asígnales su ponderación en «⚖ Ponderaciones»». Lo mismo se recuerda al abrir un curso que **ya tiene exámenes y ponderación 0 %** de exámenes sin haberla guardado nunca (p. ej. cursos anteriores a esta versión). No se vuelve a insistir si la persona guardó explícitamente 0 %.
8. **Tabla del curso:** dos columnas después de las de examen y antes de «Última», centradas y visibles en todos los modos: **«Final»** (0–100, entera) y **«Final /10»** (la misma calificación en escala de 0 a 10 con **un decimal**, calculada del valor exacto; 81 → 8.1). Se **ordenan** (mayor primero) por el valor exacto; los oyentes también las tienen.
9. **Historial del alumno:** una **tarjeta «Calificación final»** (entera, con «= 8.1 de 10» debajo) junto a las de resumen y un **desglose** (componente, valor en escala 0–100, ponderación y aporte): Participaciones (décimas × 10), Exámenes (promedio), Tareas, Proyecto y la suma; el desglose lo entrega el servicio, la UI no calcula.
10. **Exportación:** columna **«Calificación final»** (número entero, redondeado) en el «Resumen» del `.xlsx` y del `.csv`, **después de las columnas de examen y de «Promedio exámenes»** y antes de «Participaciones». Además, en el `.xlsx` una línea bajo el título del curso con las ponderaciones usadas («Ponderaciones: participaciones 10 % · exámenes 30 % · tareas 20 % · proyecto 40 %») para que el archivo se entienda solo. Los oyentes siguen excluidos por defecto.
11. **Eliminar un curso** borra sus ponderaciones (sin conteo en el diálogo: no son calificaciones).
12. Sin migración manual: la tabla nueva se crea sola (`CREATE TABLE IF NOT EXISTS`); los cursos existentes quedan con las ponderaciones por omisión sin tocar sus datos.

## Modelo de datos (cambio propuesto)

```
ponderacion(curso_id PK FK→curso ON DELETE CASCADE,
            participaciones REAL, examenes REAL, tareas REAL, proyecto REAL)   -- porcentajes
```

Sin fila = ponderaciones por omisión (10 / 0 / 20 / 40). Una fila guardada explícitamente con exámenes en 0 % significa «ya decidí que no pesan». **No se agrega ninguna columna a `curso`** (cambiar tablas existentes se pregunta antes) y **no se guarda ninguna calificación final**.

## Reglas de negocio nuevas (se agregarán a `CLAUDE.md` al implementar)

- **R18 Calificación final** (`core/calificacion_final.py::calificacion_final`, única fuente; el servicio la usa, la UI y el exportador no la recalculan): supuestos 1–6; suma ponderada con participaciones × 10, promedio de exámenes (0 sin exámenes), tareas y proyecto; ponderaciones por curso (por omisión 10/30/20/40, sin exigir que sumen 100 %); redondeo solo al mostrar y exportar; nunca se guarda.
- Actualizar Modelo de datos, Interfaz (botón «Ponderaciones», columna «Final», tarjeta y desglose del historial) y Exportación (columna y línea de ponderaciones).

## Interfaz

**Pantalla Curso:**

```
[⚖ Ponderaciones] [⬆ Importar tareas] [＋ Agregar alumno] [⬇ Exportar]

 No.  Cuenta     Nombre               Décimas  Tareas  Proyecto  Examen - P1  Final  Final /10  Última
  1   100000001  ABREU SOLANO …           8       90       85        70        81      8.1     05/03/2027
```

**Diálogo «Ponderaciones»:**

```
Participaciones [ 10 ] %      Exámenes [ 0 ] %  (al crear el primer examen: 30 % sugerido)
Tareas          [ 20 ] %      Proyecto final [ 40 ] %
Suma: 100 %
                         [Restablecer]  [Cancelar] [Guardar]
```

**Historial:** tarjeta «Calificación final» (entera) y, debajo de las tarjetas o en una sección propia, el desglose por componente con su aporte.

Colores solo desde `ui_desktop/tema.py` (se reutilizan los existentes; no hacen falta nuevos).

## Comandos

```
Pruebas:    .venv\Scripts\python.exe -m pytest
Una prueba: .venv\Scripts\python.exe -m pytest tests/test_calificacion_final.py -q
Ejecutar:   .venv\Scripts\python.exe main.py
Empaquetar: powershell -ExecutionPolicy Bypass -File scripts\construir_exe.ps1   (subir core/version.py antes)
```

## Estructura (archivos a tocar o crear)

```
core/calificacion_final.py → calificacion_final(...) y el desglose; constantes de ponderaciones por omisión;
                             redondeo (la mitad hacia arriba). Sin base ni UI.
core/database.py          → tabla ponderacion
core/models.py            → Ponderaciones, DesgloseFinal; ResumenAlumno gana `final: float`
core/repository.py        → SQL de ponderacion (obtener, guardar, borrar)
core/services.py          → ponderaciones_de, establecer_ponderaciones (valida), restablecer_ponderaciones,
                            desglose_final(curso_id, alumno_id); `resumen_curso` trae `final`
exporters/curso.py        → columna «Calificación final» y línea de ponderaciones (xlsx)
ui_desktop/dialogos_curso.py o dialogos_ponderaciones.py → DialogoPonderaciones
ui_desktop/vista_curso.py → botón, columna «Final», orden
ui_desktop/vista_historial.py → tarjeta y desglose
tests/test_calificacion_final.py, test_ui_curso.py, test_ui_historial.py, test_exportacion.py (ampliar), test_ui_ponderaciones.py
CLAUDE.md, README.md      → R18 y pantallas; subir core/version.py (1.6.0)
```

## Estilo de código

Español sin acentos ni ñ, type hints, funciones puras para el cálculo (como `core/promedio.py` y `core/puntaje.py`), errores como `ErrorDominio`:

```python
@dataclass(frozen=True)
class Ponderaciones:
    """Porcentajes de cada componente de la calificación final (pueden sumar más de 100)."""

    participaciones: float = 10.0
    examenes: float = 30.0
    tareas: float = 20.0
    proyecto: float = 40.0

    @property
    def suma(self) -> float:
        return self.participaciones + self.examenes + self.tareas + self.proyecto
```

## Estrategia de pruebas

pytest, datos ficticios (`100000001`, nombres inventados).
- **Función pura** (`calificacion_final`): ejemplo base (8 décimas, promedio 70, tareas 90, proyecto 85, pesos 10/30/20/40 → 81); décimas × 10 y sin tope (12 décimas → aporta 12); sin exámenes aporta 0; todo en 0 → 0; ponderaciones que suman más de 100 % pasan de 100; menos de 100 % también; ponderación 0 anula un componente; **redondeo de la mitad hacia arriba** (87.5 → 88, 87.49 → 87, 0.5 → 1) y no por banca (2.5 → 3); valores exactos conservados.
- **Servicio:** ponderaciones por omisión (10 / 0 / 20 / 40) sin fila; una fila guardada con exámenes en 0 % se distingue de «sin fila»; guardar y leer; validación (negativo, > 100, `nan`, texto); restablecer; suma mayor y menor de 100 % permitidas; `resumen_curso` trae `final` y cambia al cambiar las ponderaciones o cualquier componente (décimas, examen, tareas, proyecto); el piso de 0 de las décimas se respeta; el desglose coincide con el final; nunca se guarda un final; independencia (no cambia décimas, exámenes, tareas ni proyecto); cascada al borrar el curso; una base `.db` existente abre y conserva sus datos.
- **Exportación:** columna «Calificación final» numérica entera, en su lugar (con y sin exámenes), oyentes excluidos por defecto, línea de ponderaciones en el `.xlsx`, reflejo de ponderaciones personalizadas; el `.csv` igual sin la línea.
- **UI (humo, patrones de `test_ui_curso.py`):** al crear el primer examen con ponderación 0 se abre el diálogo con 30 % sugerido (guardar asigna; cancelar deja el examen y recuerda en la franja; no se insiste tras guardar 0 % explícito; un curso con exámenes y sin asignar recibe el recordatorio al abrirse); las columnas «Final» y «Final /10» (valores, centradas, orden); botón y diálogo (abrir, editar, suma en vivo con mensaje de extra y de faltante, restablecer, validaciones dentro del diálogo, cancelar no guarda); el historial (tarjeta con la equivalencia /10 y desglose); cambiar ponderaciones actualiza la tabla.
- **Regresión:** la suite completa (599 pruebas) sigue pasando; las pruebas de posición de columnas del curso y de la exportación se ajustan solo donde se inserta la columna nueva.

## Límites

- **Siempre:** correr `.venv\Scripts\python.exe -m pytest` antes de cada commit; el cálculo vive solo en `core/calificacion_final.py` (la UI y el exportador no lo repiten); SQL solo en `core/repository.py`; `core/` sin importar `ui_*`; actualizar `CLAUDE.md` y `README.md` en el mismo cambio; datos ficticios; colores solo en `tema.py`.
- **Preguntar antes:** cambiar tablas existentes (incluida `curso`); añadir dependencias; guardar la calificación final; cambiar la regla del piso de 0 o la del promedio de exámenes.
- **Nunca:** guardar una calificación final (se calcula siempre); redondear antes de sumar; modificar décimas, exámenes, tareas o proyecto por calcular el final; copiar datos reales de alumnos.

## Criterios de éxito

1. Con 8 décimas, promedio de exámenes 70, tareas 90 y proyecto 85 y las ponderaciones 10 / 30 / 20 / 40, la columna «Final» muestra **81** y «Final /10» muestra **8.1** (8 + 21 + 18 + 34).
2. Cambiar la ponderación del proyecto a 50 % en «⚖ Ponderaciones» actualiza todas las finales de la tabla al instante; el diálogo indica «Suma: 110 % · 10 % de puntos extra».
3. 12 décimas aportan 12 puntos con el 10 % (se pasan de 100 sin problema); una décima negativa total nunca baja de 0 (piso de R5).
4. Un curso sin exámenes calcula la final con el componente de exámenes en 0.
5. 87.5 se muestra y exporta como 88; 87.49 como 87.
6. El historial muestra la tarjeta de calificación final y un desglose cuyos aportes suman la final (antes de redondear).
7. El `.xlsx` y el `.csv` traen «Calificación final» como número, en su lugar, y el `.xlsx` indica las ponderaciones usadas; los oyentes siguen excluidos por defecto.
8. Décimas, exámenes, tareas y proyecto se comportan exactamente como antes.
9. Una base `.db` existente abre sin errores y conserva todos sus datos; los cursos existentes usan 10 / 0 / 20 / 40 y se les recuerda asignar la de exámenes si ya tienen exámenes.
10. Un curso nuevo calcula la final con exámenes en 0 %; al crear su primer examen se abre el diálogo de ponderaciones con 30 % sugerido en «Exámenes», y al guardar la final cambia en la tabla; cancelar deja el examen creado y la franja lo recuerda.
11. La suite completa pasa.

## Preguntas abiertas

Ninguna. Respuestas de la persona: (1) la equivalencia de 0 a 10 va en el historial **y también en la tabla**; (2) los exámenes ponderan **0 % al principio** y, **al crear un examen, se debe asignar su ponderación**; (3) cada ponderación va de 0 a 100 % y la suma puede pasar de 100 %. Los supuestos 1–12 se toman como aceptados.