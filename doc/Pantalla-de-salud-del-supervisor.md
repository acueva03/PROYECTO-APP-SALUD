# Pantalla de salud del supervisor

Pantalla de **solo consulta** donde el supervisor ve la evolución de salud de uno de sus pacientes: datos actuales, gráfico del peso, gráfico de adherencia a la medicación (últimos 14 días) y registro de tomas.

## Qué cambió respecto a la versión anterior

- La pantalla del **paciente** ya no muestra gráficos ni historial de tomas. Se queda con **Mis datos** (edad, peso, altura, IMC, ficha médica) y el formulario para registrar el peso.
- Los gráficos pasaron a la pantalla del **supervisor**, en una página propia.
- El código de los gráficos vive en `frontend/static/graficos.js` y solo lo carga la pantalla del supervisor (la del paciente es ahora más ligera).

## Cómo se usa

1. El supervisor entra en su panel (`/supervisor`).
2. En la tarjeta **Paciente supervisado** pulsa **Ver gráficos de salud**.
3. Se abre `/supervisor/salud/<id del paciente>` **en una pestaña nueva**.

> Se abre en otra pestaña a propósito: `supervisor.js` (la pestaña del panel) es la que consulta las alertas SOS y hace sonar la alarma. Si el supervisor navegara fuera de esa pestaña, dejaría de recibir avisos. La pantalla de gráficos lo recuerda con un banner.

## API (solo lectura)

Todas son `GET`, solo para supervisores y solo para pacientes vinculados a ese supervisor.

| Endpoint | Devuelve |
|---|---|
| `/api/supervisor/pacientes/<id>/salud` | Edad, peso, altura, IMC y ficha médica |
| `/api/supervisor/pacientes/<id>/peso` | Lista de pesajes `{fecha, kg}`, de más antiguo a más reciente |
| `/api/supervisor/pacientes/<id>/tomas?dias=30` | Tomas de medicación de los últimos `dias` días (entre 1 y 365) |

| Situación | Respuesta |
|---|---|
| Sin sesión | 401 |
| Usuario que no es supervisor | 403 |
| Paciente no vinculado **o inexistente** | 403 (el mismo, para no revelar qué ids existen) |
| `POST`, `PUT`, `PATCH`, `DELETE` | 405: el supervisor no puede modificar nada |

La ruta de la pantalla, `/supervisor/salud/<id>`, redirige al login (sin sesión o sin ser supervisor) o al panel (paciente no vinculado).

## Código implicado

| Archivo | Papel |
|---|---|
| `backend/app.py` | Endpoints, ruta de la pantalla y las funciones compartidas `datos_salud`, `pesos_de` y `tomas_de` (las usan también los endpoints del paciente) |
| `frontend/templates/supervisor_salud.html` | Plantilla de la pantalla |
| `frontend/static/graficos.js` | Funciones de gráficos (Chart.js): `dibujarPeso`, `dibujarAdherencia`, `dibujarHistorial` |
| `frontend/static/supervisor_salud.js` | Carga los datos de la API y dibuja la pantalla |
| `frontend/static/salud_supervisor.css` | Estilos propios de la pantalla |
| `backend/test_supervisor_salud.py` | Tests |

## Pendiente de integrar con el trabajo de P3 (varios pacientes)

- `paciente_supervisado_o_403(paciente_id)` en `app.py` es **provisional**. Cuando exista el helper definitivo con ese nombre, se borra el provisional.
- `supervisor_salud.js` expone `SaludSupervisor.cargar(idPaciente)`: cuando el panel tenga pestañas por paciente, bastará llamarla al cambiar de pestaña.

## Tests

`python3 -m unittest test_supervisor_salud -v` comprueba:

- Un supervisor vinculado ve los datos de su paciente (y solo los suyos).
- Un supervisor no ve pacientes ajenos ni ids inexistentes (403).
- Sin sesión (401) y con rol paciente (403).
- El supervisor no puede modificar datos (405).
- Valores raros en `dias` no rompen el endpoint.
- La pantalla se abre para el supervisor vinculado y redirige a quien no corresponde.
- La pantalla del paciente ya no contiene los gráficos y `/api/mi-salud` sigue igual.
