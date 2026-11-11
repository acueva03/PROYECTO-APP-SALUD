# Accesibilidad y riesgos de la pantalla del paciente (3.12, 3.14, 3.16, 3.18 y 3.25)

## El problema

La pantalla del paciente es la que usan personas mayores o con poca visión, y es donde están el botón SOS y los avisos de medicación. Antes de este cambio:

- Las alarmas solo sonaban con la pestaña abierta y nada lo advertía; si no sonaban, el supervisor no se enteraba (3.12).
- «Eliminar» borraba la alarma para siempre tras un `confirm()` pequeño del navegador (3.14).
- Si sonaban dos medicamentos a la vez, un único «Ya lo hice» los confirmaba **los dos** (3.16).
- Varios `catch` estaban vacíos y el SOS compartía archivo con las alarmas: un error de programación podía pasar por «sin conexión» o dejar sin SOS (3.18).
- No había ajustes de letra, contraste ni voz (3.25, historia de usuario 23).

## Qué se hizo

| Riesgo | Medida | Dónde |
|---|---|---|
| 3.12 | Aviso **fijo** «Mantén esta pantalla abierta y con el volumen subido» (el botón de sonido sí desaparece al activarse) | `paciente.html` |
| 3.12 | La pantalla no se apaga sola mientras la página está visible (*Screen Wake Lock API*); se vuelve a pedir al volver a la pestaña y se muestra si el navegador no lo permite | `conexion.js` (`mantenerPantallaEncendida`) |
| 3.12 | Al volver a la pestaña se comprueban las alarmas **en el momento** (en segundo plano los temporizadores van frenados) | `conexion.js` (`visibilitychange`) |
| 3.12.3 | Una alarma activa cuya hora pasó hace más de 15 min sin registro de toma aparece al supervisor como «(no ha sonado en su móvil)» en *Recordatorios sin confirmar* | `alarmas_sin_sonar_de()` en `app.py` |
| 3.14 | Diálogo propio (`<dialog>`) con nombre y dosis: «Vas a eliminar la alarma de Sintrom 4 mg». Con dosis, **Desactivar** es el botón grande y el foco empieza en él; **Eliminar** queda en segundo plano | `paciente.html`, `conexion.js` |
| 3.14 | **Borrado lógico**: columnas `eliminada` y `eliminada_en` (en `models.py` **y** en `actualizar_columnas()`, regla 3.19). Una alarma eliminada no se lista ni suena | `models.py`, `app.py` |
| 3.14 | «Deshacer» durante 30 s tras eliminar y **papelera** «Alarmas eliminadas» (últimos 30 días) con «Recuperar» | `conexion.js`, `paciente.html` |
| 3.14.3 | El supervisor recibe las alarmas eliminadas en `eliminadas` de `/api/supervisor/pacientes/<id>/medicacion` y puede restaurarlas | `supervisor_bp.py`, `app.py` |
| 3.16 | Cada aviso es un elemento con **sus propios** «Ya lo hice» y «Posponer 10 minutos», y muestra la dosis | `conexion.js`, `paciente.html` |
| 3.16.3 | Tras confirmar, «✔ Hecho: … · Deshacer» durante 1 minuto; devuelve la toma a `PENDIENTE` | `conexion.js`, `/api/tomas/<id>/deshacer` |
| 3.18 | El SOS pasa a `sos.js`, que no depende de ningún otro archivo y se carga el primero | `sos.js` |
| 3.18 | El SOS dice **qué** ha fallado (sin conexión / sesión caducada / error del servidor) y enseña un botón «📞 Llamar al 112» (`tel:112`) | `sos.js` |
| 3.18 | Ningún `catch` vacío: todos hacen `console.error` y distinguen fallo de **red**, error del **servidor** y error de **código**. El cuerpo de las peticiones se construye fuera del `try` de red | `errores.js`, `conexion.js` y resto de scripts del paciente |
| 3.18 | Un error de JavaScript no capturado muestra un aviso visible («El botón SOS sigue funcionando…») | `errores.js` |
| 3.18.2 | ESLint: `no-empty` pasa de aviso a **error** | `eslint.config.js` |
| 3.25 | Panel «Ajustes de letra, contraste y voz»: letra normal / grande (125 %) / muy grande (150 %), alto contraste, lectura en voz alta y quitar animaciones. Se guarda en el móvil | `accesibilidad.js`, `accesibilidad.css` |
| 3.25 | Los avisos se leen en voz alta (`speechSynthesis`, voz en español, un poco más lenta). Mientras habla, la alarma baja de volumen | `accesibilidad.js`, `conexion.js` |
| 3.25 | Dos regiones `aria-live` (educada y urgente) que existen siempre en el HTML; el aviso de alarma usa el patrón `alertdialog` y lleva el foco al primer botón | `paciente.html`, `accesibilidad.js` |

## Arreglos de accesibilidad encontrados por el camino

| Fallo | Arreglo |
|---|---|
| Bordes de los campos `#94A3B8`: **2,56:1** sobre blanco (WCAG 1.4.11 pide 3:1) | `#64748B`, 4,76:1 |
| El aviso de alarma parpadeaba entero: texto y botones perdían contraste la mitad del tiempo | Ahora solo parpadean el icono y el borde |
| La lista de alarmas se repintaba cada 30 s y el foco del teclado o del lector saltaba al principio | Solo se repinta si algo ha cambiado |
| El indicador «Sistema activo» se volvía a anunciar en cada comprobación | Solo cambia si cambia el estado |
| Botones «Desactivar / Eliminar / Reactivar» de menos de 44 px de alto | Mínimo 44×44 px |
| Mensajes de éxito o error distinguidos solo por el color | Llevan ✔ o ⚠ |

**Contrastes comprobados** (calculados con la fórmula WCAG): texto blanco sobre el SOS 4,98:1 (en el centro del degradado 4,23:1, válido porque «SOS» es texto grande); en alto contraste el SOS pasa a `#8E0000` (9,6:1) y el texto es negro sobre blanco (21:1).

**Auditoría con axe-core** (WCAG 2.2 AA + buenas prácticas) en la pantalla del paciente: 0 fallos con los ajustes normales y 0 fallos con alto contraste y letra muy grande.

## API nueva

| Endpoint | Quién | Qué hace |
|---|---|---|
| `DELETE /api/alarmas/<id>` | paciente | Ahora es borrado lógico. Una segunda vez da 404, como antes |
| `GET /api/mis-alarmas-eliminadas` | paciente | Papelera: alarmas eliminadas en los últimos 30 días |
| `POST /api/alarmas/<id>/restaurar` | paciente dueño o **su** supervisor | Recupera la alarma. Si su hora ya pasó, la mueve a la próxima vez que toque. 409 si no estaba eliminada |
| `POST /api/tomas/<id>/deshacer` | paciente dueño | Devuelve a `PENDIENTE` una toma confirmada hace menos de 90 s (1 minuto + margen de red). Si no, 409 |
| `GET /api/mis-tomas-supervisadas` | supervisor | Añade las alarmas que no sonaron (`sin_sonar: true`, `toma_id: null`) |

## Cosas a tener en cuenta

- **La pantalla encendida necesita HTTPS o `localhost`.** Abriendo la app desde otro móvil por la IP de la red local (`http://192.168…`) el navegador no lo permite, y el aviso lo dice.
- **La voz depende del navegador y del móvil.** Si no hay voz en español, se usa la que haya; si el navegador no tiene síntesis de voz, el panel lo indica y desactiva la opción.
- El navegador no deja hablar ni sonar hasta que el usuario toca la página: por eso sigue el botón «Activar sonido de alarmas».
- **Pendiente para quien lleve el panel del supervisor (3.14.3):** el backend ya devuelve las eliminadas y deja restaurarlas; falta pintarlas en `supervisor_pacientes.js` (pestaña Medicación). El aviso 3.12.3 sí se ve ya en *Recordatorios sin confirmar* sin tocar el panel.
- El contador de la tarjeta de cada paciente en el Resumen (`/api/supervisor/pacientes`) no incluye todavía las alarmas que no sonaron.

## Tests

`python3 -m unittest test_paciente_riesgos -v` (16 tests):

- **3.14:** eliminar no borra la fila; una eliminada no se lista, no suena (404) ni se puede reactivar; papelera y recuperar; permisos de recuperar (401 sin sesión, 403 otro paciente, 403 supervisor no vinculado, 200 su supervisor); recuperar una alarma pasada la reprograma; el supervisor la ve aparte; la papelera es solo para pacientes.
- **3.16:** confirmar una de dos tomas a la misma hora deja la otra `PENDIENTE` (también para el supervisor); las tomas pendientes traen la dosis; deshacer devuelve a `PENDIENTE`; deshacer caduca; permisos de deshacer.
- **3.12.3:** una alarma pasada hace 20 min sin sonar avisa al supervisor; margen de 15 min; no avisa si sonó, si está eliminada o desactivada; solo la ve su supervisor.

Además se probó la pantalla en Chromium (móvil de 412 px) con 35 comprobaciones: avisos y foco, confirmar uno sin confirmar el otro en la BD, deshacer, diálogo de eliminar y papelera, SOS con y sin conexión, aviso de error de JavaScript, ajustes que se guardan al recargar, sin scroll horizontal con letra muy grande y botones de 44 px como mínimo. La migración de la columna nueva se probó sobre una copia de una `app_salud.db` antigua: no se pierde ningún dato.

## Para actualizar en la Wiki (Plan RSGR)

| ID | Estado nuevo |
|---|---|
| 3.12 | Implementado (3.12.2: falta la prueba en móvil real) |
| 3.14 | Implementado, salvo la interfaz de 3.14.3 en el panel del supervisor |
| 3.16 | Implementado |
| 3.18 | Implementado |
| 3.25 | Implementado en la pantalla del paciente (3.25.2: Lighthouse/axe hecho con axe-core; faltan las sesiones con usuarios, ligadas a 3.10) |
