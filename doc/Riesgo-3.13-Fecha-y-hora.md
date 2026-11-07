# Riesgo 3.13: fecha y hora incorrectas

## El problema

Las alarmas suenan según el reloj del móvil, pero el servidor guarda fechas y valida datos. Si el móvil tiene la hora mal, o el servidor está en otra zona horaria, pueden registrarse tomas en el día equivocado o alarmas fuera de plazo.

## Qué se hizo

| Medida | Dónde |
|---|---|
| El servidor usa siempre la fecha de **Madrid** (`hoy_madrid()`), no la del sistema | `backend/models.py` (usa `ZoneInfo('Europe/Madrid')`) |
| Las validaciones de fechas (alarmas en el pasado, peso con fecha futura, ventana del historial) usan `hoy_madrid()` | `backend/app.py` |
| Una "sonada" de alarma se rechaza (400) si la `fecha_local` del móvil difiere **más de 1 día** de la de Madrid | `fecha_local_plausible()` en `backend/app.py` |
| Endpoint `GET /api/hora`: hora del servidor en UTC, fecha y hora de Madrid. No necesita sesión ni devuelve datos personales | `backend/app.py` |
| Aviso en la pantalla del paciente si el reloj del móvil difiere **más de 5 minutos** del servidor (compensa el tiempo de la petición; se repite cada 5 min y al volver a la pestaña) | `frontend/static/reloj.js`, `paciente.html` |

## Cosas a tener en cuenta

- `zoneinfo` necesita la base de datos de zonas horarias: en Windows hay que tener instalado `tzdata` (está en `requirements.txt`).
- El aviso **no corrige** el reloj ni las alarmas: solo avisa. Las alarmas siguen sonando según el reloj del móvil.
- Si no hay conexión, el aviso no cambia (no se alerta en falso).
- La fecha por defecto del formulario de peso la pone el navegador; el servidor valida igualmente contra la fecha de Madrid.

## Tests

`python3 -m unittest test_reloj -v`:

- `hoy_madrid()` usa la zona de Madrid.
- `/api/hora` devuelve una hora con zona horaria, la fecha de Madrid y la zona.
- Una sonada con fecha del móvil a más de 1 día de diferencia da 400 (y hasta 1 día se tolera).
- El peso rechaza fechas futuras según Madrid.
- Una alarma en el pasado se valida según Madrid.
