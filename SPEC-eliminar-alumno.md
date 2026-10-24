# Spec: Borrar alumno oyente de un curso (R20, propuesta)

## Objetivo
En la pantalla **Curso** se puede «Agregar alumno», pero no quitarlo. Se agrega la acción **«Eliminar alumno»**, permitida **solo a oyentes**. Un alumno `regular` (viene de la lista de inscripción) nunca se elimina desde la app.

Usuario: la persona que lleva las participaciones del grupo y se equivocó al dar de alta a un oyente (nombre mal escrito, duplicado, ya no asiste).

## Supuestos (corrige lo que no sea así)
1. **Eliminar = quitar al oyente de ESE curso**, no borrar a la persona de toda la base. Se borra su `inscripcion` en el curso y todo lo suyo **en ese curso**: participaciones, calificaciones de exámenes de ese curso, tareas, proyecto y membresía de equipo.
2. Si tras quitarlo el `alumno` **no tiene inscripción en ningún otro curso**, se borra también el registro `alumno` (no quedan alumnos huérfanos). Si sí la tiene, el registro `alumno` se conserva.
3. **Se puede deshacer** (decidido): antes de borrar, el servicio guarda una copia de todo lo eliminado (alumno si se borró, inscripción, participaciones con su fecha y nota, calificaciones de exámenes, tareas, proyecto y membresía de equipo). «Deshacer» lo restaura tal cual. Sigue la convención actual: revierte solo lo último guardado y deja de estar disponible en la siguiente captura o al cerrar. Si al deshacer la cuenta del oyente ya la usa otro alumno, o su equipo ya no existe, se avisa con `ErrorDominio` y no se restaura nada a medias. Aun así se pide confirmación previa con conteos.
4. El equipo no se borra aunque el oyente era el único miembro (R16: el número no se reutiliza).
5. Eliminar a un regular se **rechaza** con mensaje claro (`ErrorDominio`), también en el servicio, no solo ocultando el botón.
6. Cambia el modelo de **reglas**, no el de **datos** (no hay tablas ni columnas nuevas).

## Regla propuesta (se añadiría a CLAUDE.md como R20)
> **20. Eliminar alumno de un curso:** solo oyentes. Quita su inscripción y sus datos en ese curso (participaciones, calificaciones de exámenes, tareas, proyecto, membresía de equipo); si no queda inscrito en otro curso, se borra también el alumno. Exige confirmación con conteos y se puede deshacer (restaura todo lo eliminado). Un regular no puede eliminarse (para quitarlo, reimportar/otra vía fuera de alcance).

## Comandos
```
Pruebas:   python -m pytest -q
Una prueba: python -m pytest tests/test_eliminar_alumno.py -q
App:       python main.py          (verificar el nombre real del punto de entrada)
Empaquetar: scripts/construir_exe.ps1
```

## Estructura (archivos a tocar)
```
core/repository.py          → SQL: capturar_alumno_en_curso(), eliminar_alumno_de_curso(), restaurar_alumno_en_curso()
core/services.py            → eliminar_alumno_oyente(curso_id, alumno_id), resumen_eliminacion(...), deshacer de la eliminación
ui_desktop/vista_curso.py   → botón «Eliminar alumno» + menú/confirmación; sin reglas de negocio
ui_desktop/dialogos_curso.py→ diálogo de confirmación con conteos
tests/test_eliminar_alumno.py
CLAUDE.md, README.md, core/version.py (1.6.2)
```

## Estilo de código
Español sin acentos, type hints, SQL solo en `repository.py`, la UI solo llama a `services`. Ejemplo del patrón existente:
```python
def eliminar_curso(self, curso_id: int) -> None:
    ...
```
El nuevo servicio lanza `ErrorDominio("Solo se pueden eliminar alumnos oyentes.")` si `tipo != 'oyente'`.

## UI
- Acción **«Eliminar alumno»** en **ambos** lugares: botón junto a «Agregar alumno» (actúa sobre el alumno seleccionado) y opción en el menú de clic derecho sobre la fila. Desactivada o ausente si no hay selección o si la fila es un regular. El clic derecho hoy solo existe con «Formar equipos» activo: se amplía para ofrecer esta opción en el modo normal sin alterar el menú de equipos.
- Diálogo de confirmación con conteos (acción destructiva): «Se eliminará a <nombre> del curso. Se perderán N participaciones, N calificaciones de examen, tareas y proyecto». Botones «Eliminar» (rojo, `tema`) y «Cancelar»; Enter no confirma y Esc cancela.
- Tras eliminar: se refresca la tabla y la franja avisa «<nombre> eliminado del curso» con **«Deshacer»**.
- Los modos Formar equipos / Proyecto / Examen no cambian; en «Formar equipos» la acción no aplica.

## Estrategia de pruebas (datos ficticios, p. ej. `100000001`)
- Oyente con participaciones, examen, tareas, proyecto y equipo → todo desaparece de ese curso.
- Regular → `ErrorDominio`, nada cambia.
- Oyente en dos cursos → se conserva el `alumno` y sus datos del otro curso.
- Oyente en un solo curso → se borra también el `alumno`.
- Deshacer restaura alumno (si se había borrado), inscripción, participaciones (mismo total con `total_con_piso`), exámenes, tareas, proyecto y equipo; si la cuenta ya está en uso, falla sin restaurar nada.
- Equipo sobrevive vacío y su número no se reutiliza al formar otro.
- El total/final de los demás alumnos no cambia.
- Conteos del resumen coinciden con lo borrado.
- Exportar/fusionar (R19) siguen funcionando tras la eliminación.

## Límites
- **Siempre:** validar en el servicio, confirmar antes de borrar, correr toda la suite, actualizar CLAUDE.md/README y subir versión.
- **Preguntar antes:** borrar al regular, cambios de esquema.
- **Nunca:** SQL fuera de `repository.py`, reglas en la UI, borrar datos de otros cursos, usar datos reales en pruebas.

## Criterios de éxito
1. Se puede eliminar un oyente desde la pantalla Curso con confirmación.
2. Un regular no se puede eliminar (servicio y UI).
3. Quedan limpios participaciones, calificaciones, tareas, proyecto y membresía del curso; los otros cursos y alumnos no se tocan.
4. Suite completa en verde con las pruebas nuevas.

## Decisiones tomadas
1. El segundo cambio pequeño se hará más adelante (fuera de este spec).
2. Eliminar se puede deshacer.
3. Se quita del curso; la persona se borra solo si no está en otro curso.
4. Botón junto a «Agregar alumno» y clic derecho.

## Preguntas abiertas
Ninguna.
