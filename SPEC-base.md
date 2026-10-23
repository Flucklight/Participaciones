# Spec: Exportar e importar la base entre máquinas (laptop → equipo principal)

## Objetivo
Llevar la información de la versión de la laptop a esta versión (y, si hace falta, de regreso) con un solo archivo que se mueve a mano (USB, OneDrive, correo). Sin red ni sincronización (regla 5 de `CLAUDE.md`).

- **Usuario:** el profesor, que usa la app en dos máquinas.
- **Hallazgo:** hoy **no existe** una función de «importar base». Solo hay `respaldar()` (`core/database.py`) y la importación de lista de inscripción en Excel (R8). Este feature crea **exportar e importar**.
- **Decisiones ya tomadas:**
  - Alcance: **toda la base** (cursos, alumnos, participaciones, exámenes, calificaciones, tareas, proyecto, equipos y ponderaciones).
  - Formato: **copia consistente del `.db`** (SQLite).
  - Importar tiene **dos modos**: *Reemplazar todo* y *Fusionar*.
  - Fusionar siempre muestra **vista previa y pide confirmar**; nada se guarda antes.

### Historias de usuario
1. En la laptop: Configuración → «Exportar base…», se elige dónde guardar y se obtiene un `.db` con nombre `participaciones_export_AAAAMMDD_HHMMSS.db`.
2. Aquí: Configuración → «Importar base…», se elige el archivo, luego el modo:
   - **Reemplazar todo:** la base local queda igual al archivo. Antes se hace un respaldo automático y se pide confirmar indicando cuántos cursos, alumnos y participaciones se perderán de la base local.
   - **Fusionar:** se muestra una vista previa de lo que se agregará, lo que cambiará y los conflictos. Aplica solo tras confirmar.
3. Si algo sale mal, se restaura el respaldo previo a la importación («Deshacer importación»).

## Reglas de negocio propuestas (nueva R19, se añade a `CLAUDE.md` al aprobar)
1. **Exportar** = copia consistente de la base (reutiliza el mecanismo de `respaldar`), a una ruta elegida. No modifica la base de origen. Mensaje claro (`ErrorDominio`) si el destino está abierto o no existe.
2. **Validar antes de importar:** el archivo debe ser SQLite con las tablas de la app. Si no, se rechaza con mensaje claro y no se toca nada. Si es de una versión anterior, se migra una **copia temporal** (con `_migrar`); si es de una versión más nueva que la local (esquema desconocido), se rechaza.
3. **Respaldo obligatorio:** antes de aplicar cualquier importación se crea un respaldo de la base local; «Deshacer importación» lo restaura.
4. **Reemplazar todo:** sustituye el contenido local por el del archivo y exige confirmación explícita con conteos.
5. **Fusionar: identidad por clave natural**, nunca por `id` (los `id` difieren entre máquinas):

| Entidad | Clave natural | Si ya existe |
|---|---|---|
| curso | ciclo + materia + grupo (R9) | se reutiliza; se fusionan sus datos |
| alumno | `num_cuenta` | se reutiliza |
| alumno sin cuenta (oyente) | `nombre_norm` | **dudoso**: solo se une si la persona confirma (como R8); nunca se fusiona sin confirmación |
| inscripcion | curso + alumno | se conserva; si el tipo difiere, es conflicto |
| participacion | alumno + curso + fecha + décimas + nota | si es idéntica no se duplica; si no, se agrega |
| examen | curso + `nombre_norm` | se reutiliza |
| calificacion, tareas, proyecto | alumno (+ examen/curso) | si el valor difiere, es **conflicto**; los valores iguales no cuentan |
| ponderacion | curso | si difiere, es conflicto |
| equipo / miembro_equipo | curso + número | si los miembros difieren, es conflicto a elegir (ver Decisiones) |

6. **Conflictos:** la vista previa los lista como «antes → después» con casilla por conflicto (por omisión **no se sobrescribe** lo local). Solo se aplica lo confirmado.
7. **Fusionar nunca borra** nada local. Las participaciones se fusionan como eventos y el total se recalcula con `total_con_piso` (R5); nunca se importan totales guardados.
8. **Atomicidad:** la fusión corre en una sola transacción. Si falla, no queda nada a medias.
9. **Sin PII en tests, README ni commits:** los tests solo usan datos ficticios (cuentas como `100000001`).

## Stack
Python 3.11+, `sqlite3` (stdlib), `customtkinter`, `openpyxl`, `pytest`. **Sin dependencias nuevas.**

## Comandos
```
Pruebas:   python -m pytest -q
Una prueba: python -m pytest tests/test_exportar_importar.py -q
App:       python main.py          # confirmar el punto de entrada real al planear
Empaquetar: powershell scripts/construir_exe.ps1
```

## Estructura (respeta la arquitectura de `CLAUDE.md`)
```
core/database.py          → exportar_base(conexion, destino), validar_base(ruta) [SQL de bajo nivel ya vive aquí junto a respaldar]
core/repository.py        → consultas de lectura/escritura que necesite la fusión (todo el SQL va aquí)
core/importar_base.py     → plan de fusión: calcular_vista_previa(), aplicar() (sin importar nada de ui_*)
core/services.py          → ServicioBase: exportar, previsualizar, importar (reemplazar/fusionar), deshacer
ui_desktop/vista_configuracion.py → botones «Exportar base…» / «Importar base…»
ui_desktop/dialogo_importar_base.py → modo + vista previa + confirmar (nuevo)
tests/test_exportar_importar.py     → pruebas (nuevo)
core/version.py           → subir a 1.6.1 al entregar
```

## Estilo de código
Español sin acentos ni ñ, type hints, `ErrorDominio` para errores al usuario, la UI no contiene reglas.
```python
def exportar_base(conexion: sqlite3.Connection, destino: str | Path) -> Path:
    """Copia consistente de la base en `destino`; no modifica la base de origen."""
```

## Estrategia de pruebas
`pytest` con bases temporales (`tmp_path`) y datos ficticios. Cada regla R19 lleva su prueba:
- Exportar produce un `.db` abrible con los mismos conteos; destino inválido o abierto da `ErrorDominio`.
- Validar: rechaza un archivo que no es SQLite, uno sin tablas de la app y uno de esquema más nuevo; acepta uno de versión anterior (p. ej. 1.4.0 sin `nombre`/`proyecto` en `equipo`).
- Reemplazar: deja la base igual al archivo y existe el respaldo previo; deshacer restaura.
- Fusionar:
  - base vacía + archivo = copia fiel;
  - reimportar el mismo archivo dos veces no duplica nada;
  - alumnos con distintos `id` pero misma cuenta se unen;
  - oyentes con el mismo nombre quedan como dudosos y no se unen sin confirmar;
  - un conflicto no se sobrescribe sin marcarlo;
  - las participaciones se unen y el total respeta el piso de 0;
  - una falla a mitad de la fusión no deja cambios.
- UI: prueba ligera del diálogo (como `tests/test_ui_final.py`) y verificación manual del flujo laptop → equipo principal.

## Límites
- **Siempre:** respaldar antes de importar; validar el archivo; pedir confirmación con conteos; correr toda la suite antes de cada commit; actualizar `CLAUDE.md` y `README.md` en el mismo cambio.
- **Preguntar antes:** cambiar el esquema de la base; añadir dependencias; cambiar reglas existentes (R1–R18).
- **Nunca:** guardar totales o calificaciones finales; fusionar personas sin confirmación; borrar datos locales al fusionar; versionar un `.db` real o datos reales; usar `id` como identidad entre máquinas; escribir SQL fuera de `core/repository.py` / `core/database.py`.

## Criterios de éxito
1. Exportar en la laptop y «Reemplazar todo» aquí deja una base idéntica (mismos conteos y mismos totales y calificaciones finales por alumno).
2. Fusionar el mismo archivo dos veces no cambia nada la segunda vez.
3. Con datos distintos en ambos lados, la vista previa lista cada conflicto y, sin confirmar, la base no cambia.
4. «Deshacer importación» devuelve exactamente la base de antes.
5. Un archivo inválido o de versión más nueva se rechaza con un mensaje en español y sin efectos.
6. Todos los tests pasan; nuevos tests cubren cada punto de R19.

## Decisiones (resueltas)
1. **Participaciones posiblemente duplicadas** (mismo alumno+curso+fecha+décimas+nota en ambos lados): la vista previa las marca y la persona elige por caso **«Mantener ambas»** o **«Descartar la importada»**. Por omisión: descartar la importada (no duplicar). *Trabajo a futuro:* añadir un identificador por evento al esquema para fusionar sin ambigüedad.
2. **Equipos con miembros distintos** en cada máquina: se muestran como **conflicto a elegir** (conservar el local o tomar el importado); por omisión, el local.
3. **Dirección:** funciona en ambos sentidos (laptop ⇄ equipo principal); el diseño es simétrico.
4. **Cursos archivados:** se exportan y fusionan igual que los activos, conservando su estado.
5. **Versión:** cambio menor, se sube a **1.6.1** (no 1.7.0). Actualizar también la mención en «Estructura».

## Preguntas abiertas
Ninguna. Pendiente solo confirmar el punto de entrada real de la app al planear.
